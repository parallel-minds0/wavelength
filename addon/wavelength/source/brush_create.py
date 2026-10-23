"""Profile-aware interactive cube/brush creation.

All profiles expose the same click-click prototyping interaction. Blender mode snaps
to Blender's viewport grid and creates an ordinary mesh; engine profiles snap to
their profile grid and create brush-tagged meshes.
"""
import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector
from math import cos, sin, tau, pi
from bpy_extras import view3d_utils
from . import profiles, scene, workspace


def _snap(value, step):
    return round(value / step) * step if step and step > 0.0 else value


def _neutral_size(settings):
    """Neutral starting size in world meters, independent of the active grid step."""
    if getattr(settings, 'engine', 'blender') == 'blender':
        return 1.0
    return profiles.engine_to_world(settings, 16.0)


def _unit_step(settings, step=None):
    return _neutral_size(settings)


def _step(context):
    settings = context.scene.wavelength
    if settings.engine == 'blender':
        if not profiles.snap_enabled(settings, context):
            return 0.0
        space = getattr(context, 'space_data', None)
        overlay = getattr(space, 'overlay', None)
        step = float(getattr(overlay, 'grid_scale', 0.0) or getattr(settings, 'metric_grid_step', 1.0) or 1.0)
        scn = context.scene
        unit = scn.unit_settings
        if unit.system != 'NONE':
            step *= float(unit.scale_length or 1.0)
        return max(step, 1e-4)
    from . import tool_snap
    return tool_snap.step(context) if tool_snap.grid_enabled(context) else 0.0


def _ray(context, event):
    xy = (event.mouse_region_x, event.mouse_region_y)
    origin = view3d_utils.region_2d_to_origin_3d(context.region, context.region_data, xy)
    direction = view3d_utils.region_2d_to_vector_3d(context.region, context.region_data, xy).normalized()
    return origin, direction


def _axis_basis(normal):
    n = normal.normalized()
    ax = max(range(3), key=lambda i: abs(n[i]))
    if abs(n[ax]) > 0.999:
        if ax == 2:
            u, v = Vector((1, 0, 0)), Vector((0, 1, 0))
        elif ax == 0:
            u, v = Vector((0, 1, 0)), Vector((0, 0, 1))
        else:
            u, v = Vector((1, 0, 0)), Vector((0, 0, 1))
        if u.cross(v).dot(n) < 0:
            v.negate()
        return u, v, n
    helper = Vector((0, 0, 1)) if abs(n.z) < 0.9 else Vector((1, 0, 0))
    u = helper.cross(n).normalized()
    v = n.cross(u).normalized()
    return u, v, n


def _plane_from_mouse(context, event):
    origin, direction = _ray(context, event)
    depsgraph = context.evaluated_depsgraph_get()
    hit, location, normal, _face, obj, _matrix = context.scene.ray_cast(depsgraph, origin, direction)
    if hit and obj is not None and obj.type == 'MESH' and not obj.get('wl_exclude'):
        u, v, n = _axis_basis(normal)
        return location.copy(), u, v, n

    from . import tool_snap
    # Grid fallback is a world-origin plane chosen from the view, not from each
    # perspective mouse ray (which can change dominant axis across the viewport).
    facing=context.region_data.view_rotation@Vector((0,0,-1)) if tool_snap.profile_grid_active(context) else direction
    axis = max(range(3), key=lambda i: abs(facing[i]))
    n = Vector((0, 0, 0))
    n[axis] = 1.0 if facing[axis] < 0 else -1.0
    u, v, n = _axis_basis(n)
    return Vector((0, 0, 0)), u, v, n


def _intersect_plane(origin, direction, plane_point, normal):
    denom = direction.dot(normal)
    if abs(denom) < 1e-8:
        return None
    return origin + direction * ((plane_point - origin).dot(normal) / denom)


def _snapped_point(context, event, plane_point, u, v, n, step):
    origin, direction = _ray(context, event)
    point = _intersect_plane(origin, direction, plane_point, n)
    if point is None:
        return None
    plane_d = plane_point.dot(n)
    su = _snap(point.dot(u), step)
    sv = _snap(point.dot(v), step)
    return u * su + v * sv + n * plane_d


def _height(settings, step=None, height_m=None):
    if height_m is not None and height_m > 0.0:
        return float(height_m)
    return _neutral_size(settings) * max(1, int(getattr(settings, 'brush_height_steps', 1)))


def _initial_drag_point(settings, start, u, v):
    """Return the neutral initial drag point so creation begins at a neutral size."""
    neutral = _neutral_size(settings)
    kind = getattr(settings, 'brush_type', 'CUBE')
    if kind in {'CYLINDER', 'CONE', 'SPHERE'}:
        return start + u * (neutral * 0.5)
    if kind == 'ARCH':
        return start + u * (neutral * 2.0)
    if kind == 'STAIRS':
        steps = max(1, min(64, int(getattr(settings, 'stair_steps', 8))))
        return start + u * (neutral * 2.0) + v * (neutral * float(steps))
    return start + u * neutral + v * neutral


def _box_geometry(settings, a, b, n, step, height_m=None):
    top = n * _height(settings, step, height_m)
    u, v, _ = _axis_basis(n)
    plane_d = a.dot(n)
    au, av = a.dot(u), a.dot(v)
    bu, bv = b.dot(u), b.dot(v)
    min_len = min(_neutral_size(settings), step) if (step and step > 0.0) else 1e-3
    if abs(bu - au) < min_len:
        bu = au + (min_len if bu >= au else -min_len)
    if abs(bv - av) < min_len:
        bv = av + (min_len if bv >= av else -min_len)
    base = [u*au+v*av+n*plane_d, u*bu+v*av+n*plane_d,
            u*bu+v*bv+n*plane_d, u*au+v*bv+n*plane_d]
    verts = base + [p + top for p in base]
    faces = [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    return verts, faces


def _radial_geometry(settings, center, edge, u, v, n, step, cone=False, height_m=None):
    sides = max(3, min(int(getattr(settings, 'brush_sides', 8)), 64))
    delta = edge - center
    raw_r = (delta - n * delta.dot(n)).length
    min_r = min(_neutral_size(settings) * 0.5, step) if (step and step > 0.0) else 1e-3
    snapped_r = _snap(raw_r, step) if (step and step > 0.0 and raw_r >= step) else raw_r
    radius = max(min_r, snapped_r)
    height = _height(settings, step, height_m)
    base = [center + u * (cos(tau * i / sides) * radius) + v * (sin(tau * i / sides) * radius) for i in range(sides)]
    if cone:
        verts = base + [center + n * height]
        apex = sides
        faces = [tuple(reversed(range(sides)))] + [(i, (i + 1) % sides, apex) for i in range(sides)]
    else:
        top = [p + n * height for p in base]
        verts = base + top
        faces = [tuple(reversed(range(sides))), tuple(range(sides, sides * 2))]
        faces += [(i, (i + 1) % sides, (i + 1) % sides + sides, i + sides) for i in range(sides)]
    return verts, faces


def _sphere_geometry(settings, center, edge, u, v, n, step):
    from .primitives import generate
    unit = profiles.unit_meters(settings)
    raw_r = (edge - center).length
    min_r = min(_neutral_size(settings) * 0.5, step) if (step and step > 0.0) else 1e-3
    snapped_r = _snap(raw_r, step) if (step and step > 0.0 and raw_r >= step) else raw_r
    radius = max(min_r, snapped_r)
    st = str(getattr(settings, 'sphere_type', 'UV')).upper()
    is_engine = bool(profiles.get(settings.engine).get('brush_semantics', False))
    params = {
        'radius': max(2.0 if is_engine else 1e-3, radius / unit),
        'sphere_type': st,
        'segments': int(getattr(settings, 'brush_sides', 8)),
        'rings': int(getattr(settings, 'brush_rings', 6)),
        'subdivisions': int(getattr(settings, 'sphere_subdivisions', 1)),
    }
    verts, faces = generate('SPHERE', params, validate_bsp=profiles.requires_convex_brushes(settings.engine))[0]
    return [center + (u * x + v * y + n * z) * unit for x, y, z in verts], faces


def _arch_parts(settings, center, edge, u, v, n, step, height_m=None):
    segments = max(3, min(int(getattr(settings, 'arch_segments', 8)), 32))
    angle = max(15.0, min(float(getattr(settings, 'arch_angle', 180.0)), 360.0)) * pi / 180.0
    delta = edge - center
    neutral = _neutral_size(settings)
    raw_outer = (delta - n * delta.dot(n)).length
    min_outer = min(neutral, step * 2) if (step and step > 0.0) else 2e-3
    snapped_outer = _snap(raw_outer, step) if (step and step > 0.0 and raw_outer >= step * 2) else raw_outer
    outer = max(min_outer, snapped_outer)
    thick_base = neutral * 0.5
    max_thick = outer * 0.85
    thickness = max(1e-3, min(max_thick, float(getattr(settings, 'arch_thickness_steps', 1)) * thick_base))
    inner = max(1e-3, outer - thickness)
    height = _height(settings, step, height_m)
    parts = []
    start = pi / 2 - angle * 0.5
    for j in range(segments):
        a0 = start + angle * j / segments
        a1 = start + angle * (j + 1) / segments
        ring = []
        for r, a in ((inner, a0), (outer, a0), (outer, a1), (inner, a1)):
            ring.append(center + u * (cos(a) * r) + v * (sin(a) * r))
        verts = ring + [p + n * height for p in ring]
        faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        parts.append((verts, faces))
    if not profiles.requires_convex_brushes(settings.engine):
        from .primitives import _single_mesh
        parts=_single_mesh(parts)
    return parts


def _stairs_values_and_basis(settings, a, b, u, v, n, step, height_m=None):
    from . import primitive_ui
    d = b - a
    du = _snap(d.dot(u), step) if (step and step > 0.0 and abs(d.dot(u)) >= step) else d.dot(u)
    dv = _snap(d.dot(v), step) if (step and step > 0.0 and abs(d.dot(v)) >= step) else d.dot(v)
    unit = profiles.unit_meters(settings)
    steps = max(1, min(64, int(getattr(settings, 'stair_steps', 8))))
    curved = bool(getattr(settings, 'stair_curved', False))
    curve_angle = float(getattr(settings, 'stair_angle', 90.0))
    if curved and abs(curve_angle) / steps >= 180.0:
        steps = max(steps, int(abs(curve_angle) // 179) + 1)
    u_dir = u if dv >= 0 else -u
    v_dir = v if dv >= 0 else -v
    total_height_m = _height(settings, step, height_m)
    if step and step > 0.0:
        g_units = step / unit
        step_snap = min(g_units, 16.0)
        width_m = max(min(_neutral_size(settings), step), abs(du))
        length_m = max(min(_neutral_size(settings), step), abs(dv))
        width = max(step_snap, round((width_m / unit) / step_snap) * step_snap)
        run = max(step_snap, round(((length_m / unit) / steps) / step_snap) * step_snap)
        rise = max(step_snap, round(((total_height_m / unit) / steps) / step_snap) * step_snap)
        landing_raw = max(0.0, float(getattr(settings, 'stair_landing', 0.0)))
        landing = max(step_snap, round(landing_raw / step_snap) * step_snap) if landing_raw > 0 else 0.0
        inner_raw = max(step_snap, float(getattr(settings, 'stair_inner_radius', 64.0)))
        inner = max(step_snap, round(inner_raw / step_snap) * step_snap)
        if curved:
            origin = a + u * _snap(du * 0.5, step)
        else:
            x0 = -round((width / 2.0) / g_units) * g_units
            x1 = x0 + width
            u_span = du * (1.0 if dv >= 0 else -1.0)
            origin = a - u_dir * ((x0 if u_span >= 0 else x1) * unit)
    else:
        g_units = 0.0
        width_m = max(1e-3, abs(du))
        length_m = max(1e-3, abs(dv))
        width = max(1e-3, width_m / unit)
        run = max(1e-3, (length_m / unit) / steps)
        rise = max(1e-3, (total_height_m / unit) / steps)
        landing = max(0.0, float(getattr(settings, 'stair_landing', 0.0)))
        inner = max(1e-3, float(getattr(settings, 'stair_inner_radius', 64.0)))
        origin = a + u * (du * 0.5)
    values = dict(
        primitive_ui.DEFAULTS,
        steps=steps,
        width=width,
        run=run,
        rise=rise,
        landing=landing,
        curved=curved,
        curve_angle=curve_angle if abs(curve_angle) >= 1.0 else 90.0,
        inner_radius=inner,
    )
    return values, origin, u_dir, v_dir, unit


def _stairs_parts(settings, a, b, u, v, n, step, height_m=None):
    from .primitives import generate
    values, origin, u_dir, v_dir, unit = _stairs_values_and_basis(settings, a, b, u, v, n, step, height_m)
    is_engine = bool(profiles.get(settings.engine).get('brush_semantics', False))
    g_units = min(step / unit, 16.0) if (step and step > 0.0) else None
    return [([origin + (u_dir * x + v_dir * y + n * z) * unit for x, y, z in verts], faces) for verts, faces in generate('STAIRS', values, validate_bsp=profiles.requires_convex_brushes(settings.engine), grid_step=g_units)]


def _primitive_parts(settings, a, b, u, v, n, step, height_m=None):
    kind = getattr(settings, 'brush_type', 'CUBE')
    if kind == 'CYLINDER': return [_radial_geometry(settings, a, b, u, v, n, step, False, height_m)]
    if kind == 'TERRAIN':
        verts,_=_box_geometry(settings,a,b,n,step,height_m)
        return [(verts[:4],[(0,1,2,3)])]
    if kind == 'CONE': return [_radial_geometry(settings, a, b, u, v, n, step, True, height_m)]
    if kind == 'SPHERE': return [_sphere_geometry(settings, a, b, u, v, n, step)]
    if kind == 'ARCH': return _arch_parts(settings, a, b, u, v, n, step, height_m)
    if kind == 'STAIRS': return _stairs_parts(settings, a, b, u, v, n, step, height_m)
    return [_box_geometry(settings, a, b, n, step, height_m)]


def _preview_geometry(settings, a, b, u, v, n, step, height_m=None):
    verts = []; faces = []
    for pv, pf in _primitive_parts(settings, a, b, u, v, n, step, height_m):
        off = len(verts); verts.extend(pv); faces.extend(tuple(off + i for i in f) for f in pf)
    return verts, faces


def _primitive_name(settings, engine_brush):
    kind = getattr(settings, 'brush_type', 'CUBE')
    base = {'CUBE': 'Cube', 'CYLINDER': 'Cylinder', 'CONE': 'Cone', 'SPHERE': 'Sphere', 'ARCH': 'Arch', 'STAIRS': 'Stairs'}.get(kind, 'Brush')
    return f'{base} Brush' if engine_brush else base


def _event_in_window_region(context, event):
    """True only over the drawable 3D viewport, not toolbar/header/sidebar."""
    area = getattr(context, 'area', None)
    if area is None:
        return False
    x, y = event.mouse_x, event.mouse_y
    for region in area.regions:
        if region.type == 'WINDOW':
            return (region.x <= x < region.x + region.width and
                    region.y <= y < region.height + region.y)
    return False


def _tool_label(settings):
    return profiles.create_cube_label(settings)


_HOVER_POINT = None
_HOVER_STEP = 1.0
_HOVER_AREA_PTR = None
_HOVER_HANDLE = None


def _draw_idle_hover():
    """Draw the passive snap marker without keeping a modal operator alive."""
    global _HOVER_POINT
    if not workspace.active(bpy.context) or _HOVER_POINT is None:
        return
    try:
        area = bpy.context.area
        if area is None or area.type != 'VIEW_3D' or area.as_pointer() != _HOVER_AREA_PTR:
            return
    except Exception:
        return
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    gpu.state.depth_test_set('NONE')
    gpu.state.line_width_set(2.0)
    s = max((_HOVER_STEP or 0.5) * 0.18, 0.02)
    p = _HOVER_POINT
    marker = [(p.x-s,p.y,p.z),(p.x+s,p.y,p.z),(p.x,p.y-s,p.z),(p.x,p.y+s,p.z),(p.x,p.y,p.z-s),(p.x,p.y,p.z+s)]
    batch = batch_for_shader(shader, 'LINES', {'pos': marker})
    shader.bind(); shader.uniform_float('color', (1.0, 1.0, 1.0, 1.0)); batch.draw(shader)
    gpu.state.line_width_set(1.0)
    gpu.state.depth_test_set('LESS_EQUAL')


class WL_OT_brush_hover(bpy.types.Operator):
    """One-shot hover update. Never installs a modal handler."""
    bl_idname = 'wavelength.brush_hover'
    bl_label = 'Brush Hover'
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return (workspace.active(context) and context.area is not None and context.area.type == 'VIEW_3D' and
                context.region is not None and context.region.type == 'WINDOW' and
                context.mode == 'OBJECT' and hasattr(context.scene, 'wavelength'))

    def invoke(self, context, event):
        global _HOVER_POINT, _HOVER_STEP, _HOVER_AREA_PTR
        step = _step(context)
        if step is None or not _event_in_window_region(context, event):
            return {'PASS_THROUGH'}
        plane_point, u, v, n = _plane_from_mouse(context, event)
        point = _snapped_point(context, event, plane_point, u, v, n, step)
        if point is not None:
            _HOVER_POINT = point.copy()
            _HOVER_STEP = _neutral_size(context.scene.wavelength)
            _HOVER_AREA_PTR = context.area.as_pointer()
            context.area.tag_redraw()
        return {'PASS_THROUGH'}


class WL_OT_cube_brush_create(bpy.types.Operator):
    bl_idname = 'wavelength.cube_brush_create'
    bl_label = 'Create Cube Brush'
    bl_description = 'Create a brush starting at a neutral size with infinite mouse dragging'
    bl_options = {'REGISTER', 'UNDO', 'GRAB_CURSOR', 'BLOCKING'}

    _handle = None
    _start = None
    _initial_drag = None
    _hover = None
    _drag = None
    _plane_point = None
    _u = _v = _n = None
    _step_value = None
    _creating = False
    _stage = 'IDLE'
    _start_mouse_2d = None
    _virt_mouse = None
    _last_mouse = None
    _height_mouse_start = None
    _height_start_m = 1.0
    _height_m = 1.0

    @classmethod
    def poll(cls, context):
        return (workspace.active(context) and context.area is not None and context.area.type == 'VIEW_3D' and
                context.mode == 'OBJECT' and hasattr(context.scene, 'wavelength') and
                _step(context) is not None)

    def _remove_draw(self):
        if self._handle is not None:
            try:
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            except Exception:
                pass
            self._handle = None

    def _draw(self, context):
        if self._hover is None:
            return
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        gpu.state.depth_test_set('NONE')
        gpu.state.line_width_set(2.0)
        s = max(_neutral_size(context.scene.wavelength) * 0.18, 0.02)
        p = self._hover
        marker = [(p.x-s,p.y,p.z),(p.x+s,p.y,p.z),(p.x,p.y-s,p.z),(p.x,p.y+s,p.z),(p.x,p.y,p.z-s),(p.x,p.y,p.z+s)]
        batch = batch_for_shader(shader, 'LINES', {'pos': marker})
        shader.bind(); shader.uniform_float('color', (1.0, 1.0, 1.0, 1.0)); batch.draw(shader)

        if self._creating and self._start is not None and self._drag is not None:
            verts, _faces = _preview_geometry(context.scene.wavelength, self._start, self._drag, self._u, self._v, self._n, self._step_value, self._height_m)
            edge_set = set()
            for face in _faces:
                for i, a in enumerate(face):
                    b = face[(i + 1) % len(face)]
                    edge_set.add(tuple(sorted((a, b))))
            lines = []
            for a, b in edge_set:
                lines.extend((verts[a], verts[b]))
            batch = batch_for_shader(shader, 'LINES', {'pos': lines})
            shader.bind(); shader.uniform_float('color', (1.0, 1.0, 1.0, 0.9)); batch.draw(shader)
        gpu.state.line_width_set(1.0)
        gpu.state.depth_test_set('LESS_EQUAL')

    def _update_hover(self, context, event, choose_plane=False):
        if choose_plane or self._plane_point is None:
            self._plane_point, self._u, self._v, self._n = _plane_from_mouse(context, event)
        self._hover = _snapped_point(context, event, self._plane_point, self._u, self._v, self._n, self._step_value)
        return self._hover

    def _accumulate_mouse(self, context, event):
        """Accumulate continuous virtual mouse coordinates across GRAB_CURSOR screen wraps."""
        if self._last_mouse is None or self._virt_mouse is None:
            self._last_mouse = (float(event.mouse_x), float(event.mouse_y))
            self._virt_mouse = (float(event.mouse_region_x), float(event.mouse_region_y))
            return
        dx = float(event.mouse_x) - self._last_mouse[0]
        dy = float(event.mouse_y) - self._last_mouse[1]
        self._last_mouse = (float(event.mouse_x), float(event.mouse_y))
        if context.region is not None:
            if abs(dx) > context.region.width * 0.45:
                dx = 0.0
            if abs(dy) > context.region.height * 0.45:
                dy = 0.0
        self._virt_mouse = (self._virt_mouse[0] + dx, self._virt_mouse[1] + dy)

    def _footprint_drag_from_mouse(self, context):
        """Compute continuous 3D footprint drag point from virtual mouse coordinates without horizon or border limits."""
        if self._start is None or self._initial_drag is None or self._start_mouse_2d is None or self._virt_mouse is None:
            return self._drag
        mdx = self._virt_mouse[0] - self._start_mouse_2d[0]
        mdy = self._virt_mouse[1] - self._start_mouse_2d[1]
        if (mdx * mdx + mdy * mdy) < 4.0:
            return self._initial_drag.copy()
        p0 = view3d_utils.region_2d_to_location_3d(context.region, context.region_data, self._start_mouse_2d, self._start)
        p1 = view3d_utils.region_2d_to_location_3d(context.region, context.region_data, self._virt_mouse, self._start)
        delta_view = p1 - p0
        d0 = view3d_utils.region_2d_to_vector_3d(context.region, context.region_data, self._start_mouse_2d).normalized()
        denom = d0.dot(self._n)
        if abs(denom) < 0.25:
            denom = -0.25 if denom <= 0 else 0.25
        delta_plane = delta_view - d0 * (delta_view.dot(self._n) / denom)
        raw_point = self._initial_drag + delta_plane
        plane_d = self._plane_point.dot(self._n)
        su = _snap(raw_point.dot(self._u), self._step_value)
        sv = _snap(raw_point.dot(self._v), self._step_value)
        return self._u * su + self._v * sv + self._n * plane_d

    primitive = ''

    def invoke(self, context, event):
        if not _event_in_window_region(context, event):
            return {'PASS_THROUGH'}
        st = context.scene.wavelength
        if self.primitive=='TERRAIN' and st.engine!='blender' and not profiles.is_source(st.engine):
            self.report({'ERROR'},'Terrain currently supports Blender and Source profiles');return {'CANCELLED'}
        if self.primitive:
            st.brush_type = self.primitive
        self._step_value = _step(context)
        if self._step_value is None:
            return {'CANCELLED'}
        st.brush_height_steps = 1
        neutral = _neutral_size(st)
        self._height_m = neutral * 4.0 if st.brush_type == 'STAIRS' else neutral
        self._height_start_m = self._height_m
        self._creating = True
        self._stage = 'FOOTPRINT'
        self._sphere_axis = None
        self._start = self._drag = self._initial_drag = None
        self._plane_point = None
        self._update_hover(context, event, choose_plane=True)
        if self._hover is None:
            return {'PASS_THROUGH'}
        self._start = self._hover.copy()
        self._initial_drag = _initial_drag_point(st, self._start, self._u, self._v)
        self._drag = self._initial_drag.copy()
        self._start_mouse_2d = (float(event.mouse_region_x), float(event.mouse_region_y))
        self._virt_mouse = self._start_mouse_2d
        self._last_mouse = (float(event.mouse_x), float(event.mouse_y))
        self._handle = bpy.types.SpaceView3D.draw_handler_add(self._draw, (context,), 'WINDOW', 'POST_VIEW')
        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def _update_height_from_mouse(self, context):
        """Drive brush height continuously from virtual mouse motion along the projected brush normal."""
        if self._start is None or self._height_mouse_start is None or self._virt_mouse is None:
            return
        dx = float(self._virt_mouse[0] - self._height_mouse_start[0])
        dy = float(self._virt_mouse[1] - self._height_mouse_start[1])
        p0 = view3d_utils.location_3d_to_region_2d(context.region, context.region_data, self._start)
        p1 = view3d_utils.location_3d_to_region_2d(context.region, context.region_data, self._start + self._n)
        if p0 is not None and p1 is not None:
            vx, vy = float(p1.x - p0.x), float(p1.y - p0.y)
            pixels = (vx * vx + vy * vy) ** 0.5
        else:
            vx = vy = 0.0; pixels = 0.0
        if pixels >= 4.0:
            delta_m = (dx * vx + dy * vy) / (pixels * pixels)
        else:
            delta_m = (dy / 48.0) * _neutral_size(context.scene.wavelength)
        raw_h = self._height_start_m + delta_m
        step = self._step_value
        min_h = min(_neutral_size(context.scene.wavelength), step) if (step and step > 0.0) else 1e-3
        if step and step > 0.0:
            self._height_m = max(min_h, _snap(raw_h, step))
        else:
            self._height_m = max(min_h, raw_h)

    def _reset_prototype(self, context, event=None):
        self._creating = False
        self._stage = 'IDLE'
        self._sphere_axis = None
        self._height_mouse_start = None
        self._start = self._drag = self._initial_drag = None
        self._start_mouse_2d = self._virt_mouse = self._last_mouse = None
        self._plane_point = None
        if event is not None and _event_in_window_region(context, event):
            self._update_hover(context, event, choose_plane=True)
        else:
            self._hover = None
        if context.area:
            context.area.tag_redraw()

    def _set_origins_to_geometry(self, context, objects):
        """Finalize every committed solid with its origin at its own geometry."""
        for obj in objects or ():
            scene.origin_to_geometry(obj)

    def modal(self, context, event):
        if not workspace.active(context):
            self._remove_draw(); return {'CANCELLED'}
        in_window = _event_in_window_region(context, event)

        if event.type in {'ESC', 'RIGHTMOUSE'}:
            if self._stage != 'IDLE':
                self._remove_draw()
                self._reset_prototype(context, event)
                return {'CANCELLED'}
            return {'PASS_THROUGH'}

        if self._stage != 'IDLE' and context.scene.wavelength.brush_type == 'SPHERE' and event.type in {'X','Y','Z'}:
            if event.value == 'PRESS' and event.ctrl:
                self._sphere_axis = event.type
                context.area.tag_redraw()
                return {'RUNNING_MODAL'}
            if event.value == 'RELEASE' and self._sphere_axis == event.type:
                self._sphere_axis = None
                context.area.tag_redraw()
                return {'RUNNING_MODAL'}
        if self._stage != 'IDLE' and event.ctrl and event.type in {'WHEELUPMOUSE','WHEELDOWNMOUSE'}:
            st=context.scene.wavelength; delta=1 if event.type=='WHEELUPMOUSE' else -1
            if st.brush_type in {'CYLINDER','CONE'}:
                st.brush_sides=max(3,min(64,st.brush_sides+delta))
            elif st.brush_type=='SPHERE':
                if getattr(st,'sphere_type','UV')=='ICO':
                    st.sphere_subdivisions=max(0,min(1,getattr(st,'sphere_subdivisions',1)+delta))
                elif self._sphere_axis == 'Z':
                    st.brush_sides=max(3,min(64,st.brush_sides+delta))
                elif self._sphere_axis in {'X','Y'}:
                    st.brush_rings=max(2,min(32,st.brush_rings+delta))
                else:
                    st.brush_sides=max(3,min(64,st.brush_sides+delta))
                    st.brush_rings=max(2,min(32,st.brush_rings+delta))
            elif st.brush_type=='ARCH':
                st.arch_segments=max(3,min(32,st.arch_segments+delta))
            elif st.brush_type=='STAIRS':
                st.stair_steps=max(1,min(64,getattr(st,'stair_steps',8)+delta))
            context.area.tag_redraw(); return {'RUNNING_MODAL'}

        if event.type in {'LEFT_BRACKET', 'RIGHT_BRACKET'} and event.value == 'PRESS':
            bpy.ops.wavelength.grid_step(direction=-1 if event.type == 'LEFT_BRACKET' else 1)
            new_step = _step(context)
            if new_step is not None:
                self._step_value = new_step
            if self._stage == 'FOOTPRINT':
                self._drag = self._footprint_drag_from_mouse(context)
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}
        if event.type in {'MIDDLEMOUSE','WHEELUPMOUSE','WHEELDOWNMOUSE','WHEELINMOUSE','WHEELOUTMOUSE',
                          'NDOF_MOTION','NDOF_BUTTON_MENU','NDOF_BUTTON_FIT'}:
            return {'PASS_THROUGH'}
        if event.type not in {'MOUSEMOVE','LEFTMOUSE'}:
            return {'PASS_THROUGH'}
        if not self._creating and not in_window:
            return {'PASS_THROUGH'}

        if event.type == 'MOUSEMOVE':
            self._accumulate_mouse(context, event)
            if self._stage == 'FOOTPRINT':
                self._drag = self._footprint_drag_from_mouse(context)
                if self._drag is not None:
                    self._hover = self._drag.copy()
                context.area.tag_redraw()
                return {'RUNNING_MODAL'}
            if self._stage == 'HEIGHT':
                self._update_height_from_mouse(context)
                context.area.tag_redraw()
                return {'RUNNING_MODAL'}

            self._update_hover(context, event, choose_plane=True)
            context.area.tag_redraw()
            return {'PASS_THROUGH'}

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            if self._stage == 'IDLE':
                self._update_hover(context, event, choose_plane=True)
                if self._hover is None:
                    return {'PASS_THROUGH'}
                st = context.scene.wavelength
                neutral = _neutral_size(st)
                self._height_m = neutral * 4.0 if st.brush_type == 'STAIRS' else neutral
                self._height_start_m = self._height_m
                self._start = self._hover.copy()
                self._initial_drag = _initial_drag_point(st, self._start, self._u, self._v)
                self._drag = self._initial_drag.copy()
                self._start_mouse_2d = (float(event.mouse_region_x), float(event.mouse_region_y))
                self._virt_mouse = self._start_mouse_2d
                self._last_mouse = (float(event.mouse_x), float(event.mouse_y))
                self._creating = True
                self._stage = 'FOOTPRINT'
                self._sphere_axis = None
                context.area.tag_redraw()
                return {'RUNNING_MODAL'}

            if self._stage == 'FOOTPRINT':
                self._accumulate_mouse(context, event)
                self._drag = self._footprint_drag_from_mouse(context)
                if context.scene.wavelength.brush_type=='TERRAIN':
                    from . import terrain
                    verts,_=_primitive_parts(context.scene.wavelength,self._start,self._drag,self._u,self._v,self._n,self._step_value)[0]
                    terrain.create_footprint(context,verts[0],verts[2],self._u,self._v,self._n)
                    self._remove_draw();self._reset_prototype(context,event);return {'FINISHED'}
                if st := getattr(context.scene, 'wavelength', None):
                    if st.brush_type == 'SPHERE':
                        self._stage = 'HEIGHT'
                self._stage = 'HEIGHT'
                self._height_mouse_start = self._virt_mouse
                self._height_start_m = self._height_m
                context.area.tag_redraw()
                return {'RUNNING_MODAL'}

            if self._stage == 'HEIGHT':
                st=context.scene.wavelength
                is_engine_brush=profiles.get(st.engine).get('brush_semantics',False)
                name=_primitive_name(st,is_engine_brush)
                created=[]
                if st.brush_type in {'CUBE','CYLINDER','CONE','ARCH','SPHERE','STAIRS'}:
                    from . import primitive_ui
                    from mathutils import Matrix
                    root=bpy.data.objects.new(name,None);context.collection.objects.link(root)
                    root.empty_display_size=0.2;root['wl_exclude']=True;root['wl_assembly_locked']=True
                    if st.brush_type=='CUBE':
                        vertices,_=_box_geometry(st,self._start,self._drag,self._n,self._step_value,self._height_m)
                        u_dir,v_dir,_=_axis_basis(self._n);unit=profiles.unit_meters(st)
                        values=dict(primitive_ui.DEFAULTS,width=(vertices[1]-vertices[0]).length/unit,run=(vertices[3]-vertices[0]).length/unit,depth=self._height_m/unit)
                        basis=Matrix((u_dir,v_dir,self._n)).transposed().to_4x4();basis.translation=sum(vertices,Vector())/8;root.matrix_world=basis
                    elif st.brush_type in {'CYLINDER','CONE'}:
                        unit=profiles.unit_meters(st);delta=self._drag-self._start
                        raw=(delta-self._n*delta.dot(self._n)).length
                        minimum=min(_neutral_size(st)*.5,self._step_value) if self._step_value and self._step_value>0 else .001
                        radius=max(minimum,_snap(raw,self._step_value) if self._step_value and self._step_value>0 and raw>=self._step_value else raw)
                        values=dict(primitive_ui.DEFAULTS,radius=radius/unit,depth=self._height_m/unit,segments=st.brush_sides)
                        basis=Matrix((self._u,self._v,self._n)).transposed().to_4x4();basis.translation=self._start+self._n*self._height_m*.5;root.matrix_world=basis
                    elif st.brush_type=='STAIRS':
                        values,origin,u_dir,v_dir,_unit=_stairs_values_and_basis(st,self._start,self._drag,self._u,self._v,self._n,self._step_value,self._height_m)
                        basis=Matrix((u_dir,v_dir,self._n)).transposed().to_4x4()
                        basis.translation=origin;root.matrix_world=basis
                    else:
                        unit=profiles.unit_meters(st)
                        neutral_u=_neutral_size(st)/unit
                        raw_r=(self._drag-self._start).length
                        snapped_r=_snap(raw_r,self._step_value) if (self._step_value and self._step_value>0.0 and raw_r>=self._step_value) else raw_r
                        min_r=min(neutral_u*0.5,(self._step_value/unit) if (self._step_value and self._step_value>0.0) else 1e-2)
                        radius=max(min_r,snapped_r/unit)
                        max_thick=radius*0.85
                        thickness=max(1e-3,min(max_thick,st.arch_thickness_steps*(neutral_u*0.5)))
                        values=dict(
                            primitive_ui.DEFAULTS,
                            sphere_type=getattr(st,'sphere_type','UV'),
                            subdivisions=getattr(st,'sphere_subdivisions',1),
                            radius=max(radius,2. if profiles.requires_convex_brushes(st.engine) else 1e-2),
                            depth=self._height_m/unit,
                            thickness=thickness,
                            angle=st.arch_angle,
                            segments=st.brush_sides if st.brush_type=='SPHERE' else st.arch_segments,
                            rings=st.brush_rings,
                        )
                        basis=Matrix((self._u,-self._n,self._v)).transposed().to_4x4() if st.brush_type=='ARCH' else Matrix((self._u,self._v,self._n)).transposed().to_4x4()
                        basis.translation=self._start;root.matrix_world=basis
                    context.view_layer.update()
                    try:primitive_ui.rebuild(root,st.brush_type,values,context)
                    except ValueError as exc:
                        bpy.data.objects.remove(root,do_unlink=True);self.report({'ERROR'},str(exc));self._remove_draw();return {'CANCELLED'}
                    bpy.ops.object.select_all(action='DESELECT')
                    primitive_ui.select_assembly(root,context,True)
                    context.view_layer.objects.active=primitive_ui.parts_for(root)[0]
                    primitive_ui._SELECTED_ROOTS.add(root.as_pointer())
                    self._remove_draw()
                    self._reset_prototype(context, event)
                    return {'FINISHED'}
                parts=_primitive_parts(st,self._start,self._drag,self._u,self._v,self._n,self._step_value,self._height_m)
                for index,(verts,faces) in enumerate(parts):
                    part_name=name if len(parts)==1 else f'{name} {index+1:02d}'
                    mesh=bpy.data.meshes.new(part_name); mesh.from_pydata(verts,[],faces); mesh.update()
                    obj=bpy.data.objects.new(part_name,mesh); context.collection.objects.link(obj)
                    if is_engine_brush:
                        scene.mark_brush(obj); obj['wl_created_engine']=st.engine
                    created.append(obj)

                self._set_origins_to_geometry(context, created)
                bpy.ops.object.select_all(action='DESELECT')
                for obj in created: obj.select_set(True)
                if created: context.view_layer.objects.active=created[0]
                self._remove_draw()
                self._reset_prototype(context, event)
                return {'FINISHED'}

        return {'PASS_THROUGH'}


class _WLBrushToolBase:
    bl_space_type='VIEW_3D'; bl_context_mode='OBJECT'; bl_widget=None
    primitive='CUBE'; tool_label='Create Cube Brush'; tool_icon='ops.generic.select_box'
    @classmethod
    def draw_settings(cls,context,layout,tool):
        if not hasattr(context.scene,'wavelength'): return
        st=context.scene.wavelength
        layout.label(text=cls.tool_label)
        if cls.primitive!='TERRAIN':layout.prop(st,'brush_height_steps',text='Height Steps')
        if cls.primitive in {'CYLINDER','CONE'}:
            layout.prop(st,'brush_sides',text='Segments')
        if cls.primitive=='SPHERE':
            layout.prop(st,'sphere_type',text='Type')
            if getattr(st,'sphere_type','UV')=='ICO':
                layout.prop(st,'sphere_subdivisions',text='Subdivisions')
            else:
                layout.prop(st,'brush_sides',text='Segments')
                layout.prop(st,'brush_rings',text='Rings')
        if cls.primitive=='ARCH':
            layout.prop(st,'arch_segments',text='Segments'); layout.prop(st,'arch_angle',text='Arc')
            layout.prop(st,'arch_thickness_steps',text='Thickness Steps')
        if cls.primitive=='STAIRS':
            layout.prop(st,'stair_steps',text='Steps')
            layout.prop(st,'stair_curved',text='Curved')
            if getattr(st,'stair_curved',False):
                layout.prop(st,'stair_angle',text='Arc')
                layout.prop(st,'stair_inner_radius',text='Inner Radius')
            layout.prop(st,'stair_landing',text='Landing')
        if st.engine!='blender':
            layout.prop(st,'grid_step',text='Grid')
        elif hasattr(st,'snap_to_grid'):
            layout.prop(st,'snap_to_grid',text='Snap to Grid')
        layout.label(text='Ctrl+Wheel: subdivisions / steps')


def _tool_class(name,idname,label,primitive,operator_id,icon='ops.mesh.primitive_cube_add_gizmo'):
    return type(name,(_WLBrushToolBase,bpy.types.WorkSpaceTool),{
        'bl_idname':idname,'bl_label':label,'bl_description':f'Prototype a snapped {primitive.lower()}',
        'bl_icon':icon,'primitive':primitive,'tool_label':label,
        'bl_keymap':((WL_OT_brush_hover.bl_idname,{'type':'MOUSEMOVE','value':'ANY'},None),
                     (operator_id,{'type':'LEFTMOUSE','value':'PRESS'},None)),
    })

class WL_OT_cube_brush(WL_OT_cube_brush_create):
    bl_idname='wavelength.create_cube'; bl_label='Create Cube Brush'; primitive='CUBE'
class WL_OT_cylinder_brush(WL_OT_cube_brush_create):
    bl_idname='wavelength.create_cylinder'; bl_label='Create Cylinder Brush'; primitive='CYLINDER'
class WL_OT_cone_brush(WL_OT_cube_brush_create):
    bl_idname='wavelength.create_cone'; bl_label='Create Cone Brush'; primitive='CONE'
class WL_OT_sphere_brush(WL_OT_cube_brush_create):
    bl_idname='wavelength.create_sphere'; bl_label='Create Sphere Brush'; primitive='SPHERE'
class WL_OT_arch_brush(WL_OT_cube_brush_create):
    bl_idname='wavelength.create_arch'; bl_label='Create Arch Brush'; primitive='ARCH'
class WL_OT_stairs_brush(WL_OT_cube_brush_create):
    bl_idname='wavelength.create_stairs'; bl_label='Create Stairs Brush'; primitive='STAIRS'
class WL_OT_terrain_brush(WL_OT_cube_brush_create):
    bl_idname='wavelength.create_terrain'; bl_label='Create Terrain Plane'; primitive='TERRAIN'

WL_Tool_CreateCubeBrush=_tool_class('WL_Tool_CreateCubeBrush','wavelength.create_cube_brush_tool','Create Cube Brush','CUBE',WL_OT_cube_brush.bl_idname)
WL_Tool_CreateCylinderBrush=_tool_class('WL_Tool_CreateCylinderBrush','wavelength.create_cylinder_brush_tool','Create Cylinder Brush','CYLINDER',WL_OT_cylinder_brush.bl_idname,'ops.mesh.primitive_cylinder_add_gizmo')
WL_Tool_CreateConeBrush=_tool_class('WL_Tool_CreateConeBrush','wavelength.create_cone_brush_tool','Create Cone Brush','CONE',WL_OT_cone_brush.bl_idname,'ops.mesh.primitive_cone_add_gizmo')
WL_Tool_CreateSphereBrush=_tool_class('WL_Tool_CreateSphereBrush','wavelength.create_sphere_brush_tool','Create Sphere Brush','SPHERE',WL_OT_sphere_brush.bl_idname,'ops.mesh.primitive_sphere_add_gizmo')
WL_Tool_CreateArchBrush=_tool_class('WL_Tool_CreateArchBrush','wavelength.create_arch_brush_tool','Create Arch Brush','ARCH',WL_OT_arch_brush.bl_idname)
WL_Tool_CreateStairsBrush=_tool_class('WL_Tool_CreateStairsBrush','wavelength.create_stairs_brush_tool','Create Stairs Brush','STAIRS',WL_OT_stairs_brush.bl_idname)
WL_Tool_CreateTerrainBrush=_tool_class('WL_Tool_CreateTerrainBrush','wavelength.create_terrain_brush_tool','Create Terrain Plane','TERRAIN',WL_OT_terrain_brush.bl_idname,'ops.mesh.primitive_grid_add_gizmo')
TOOLS=(WL_Tool_CreateCubeBrush,WL_Tool_CreateCylinderBrush,WL_Tool_CreateConeBrush,WL_Tool_CreateSphereBrush,WL_Tool_CreateArchBrush,WL_Tool_CreateStairsBrush,WL_Tool_CreateTerrainBrush)

_TOOL_REGISTERED=False

def register_tool():
    global _TOOL_REGISTERED, _HOVER_HANDLE
    if _TOOL_REGISTERED:return
    registered=[]
    try:
        bpy.utils.register_tool(TOOLS[0],after={'builtin.scale_cage'},separator=True,group=True); registered.append(TOOLS[0])
        # Add the remaining primitives directly after the previous member; Blender
        # keeps them in the nested group started by the first tool.
        for prev,tool in zip(TOOLS,TOOLS[1:]):
            bpy.utils.register_tool(tool,after={prev.bl_idname},group=False); registered.append(tool)
        if _HOVER_HANDLE is None:
            _HOVER_HANDLE = bpy.types.SpaceView3D.draw_handler_add(_draw_idle_hover, (), 'WINDOW', 'POST_VIEW')
        _TOOL_REGISTERED=True
    except Exception:
        for tool in reversed(registered):
            try:bpy.utils.unregister_tool(tool)
            except Exception:pass
        raise

def sync_tool_for_engine(settings): return None

def unregister_tool():
    global _TOOL_REGISTERED, _HOVER_HANDLE, _HOVER_POINT
    if _HOVER_HANDLE is not None:
        try: bpy.types.SpaceView3D.draw_handler_remove(_HOVER_HANDLE, 'WINDOW')
        except Exception: pass
        _HOVER_HANDLE = None
    _HOVER_POINT = None
    for tool in reversed(TOOLS):
        try:bpy.utils.unregister_tool(tool)
        except Exception:pass
    _TOOL_REGISTERED=False

