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


def _step(context):
    settings = context.scene.wavelength
    if settings.engine == 'blender':
        # Blender profile follows the native viewport grid rather than the
        # Wavelength engine-unit grid. grid_scale is the user-visible base
        # spacing for this SpaceView3D.
        space = getattr(context, 'space_data', None)
        overlay = getattr(space, 'overlay', None)
        step = float(getattr(overlay, 'grid_scale', 1.0) or 1.0)
        scene = context.scene
        unit = scene.unit_settings
        if unit.system != 'NONE':
            step *= float(unit.scale_length or 1.0)
        return max(step, 1e-9)
    return profiles.active_grid_step_meters(settings)


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

    axis = max(range(3), key=lambda i: abs(direction[i]))
    n = Vector((0, 0, 0))
    n[axis] = 1.0 if direction[axis] < 0 else -1.0
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


def _height(settings, step):
    return step * max(1, int(getattr(settings, 'brush_height_steps', 1)))


def _box_geometry(settings, a, b, n, step):
    top = n * _height(settings, step)
    u, v, _ = _axis_basis(n)
    plane_d = a.dot(n)
    au, av = a.dot(u), a.dot(v)
    bu, bv = b.dot(u), b.dot(v)
    base = [u*au+v*av+n*plane_d, u*bu+v*av+n*plane_d,
            u*bu+v*bv+n*plane_d, u*au+v*bv+n*plane_d]
    verts = base + [p + top for p in base]
    faces = [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    return verts, faces


def _radial_geometry(settings, center, edge, u, v, n, step, cone=False):
    sides = max(3, min(int(getattr(settings, 'brush_sides', 8)), 64))
    delta = edge-center
    radius=max(step,_snap((delta-n*delta.dot(n)).length,step))
    height=_height(settings,step)
    base=[center+u*(cos(tau*i/sides)*radius)+v*(sin(tau*i/sides)*radius) for i in range(sides)]
    if cone:
        verts=base+[center+n*height]; apex=sides
        faces=[tuple(reversed(range(sides)))]+[(i,(i+1)%sides,apex) for i in range(sides)]
    else:
        top=[p+n*height for p in base]; verts=base+top
        faces=[tuple(reversed(range(sides))),tuple(range(sides,sides*2))]
        faces += [(i,(i+1)%sides,(i+1)%sides+sides,i+sides) for i in range(sides)]
    return verts,faces


def _sphere_geometry(settings, center, edge, u, v, n, step):
    from .primitives import generate
    radius=max(step,(edge-center).length)
    verts,faces=generate('SPHERE',{'radius':max(1.,radius/step),'subdivisions':1})[0]
    return [center+(u*x+v*y+n*z)*step for x,y,z in verts],faces


def _arch_parts(settings, center, edge, u, v, n, step):
    segments=max(3,min(int(getattr(settings,'arch_segments',8)),32))
    angle=max(15.0,min(float(getattr(settings,'arch_angle',180.0)),360.0))*pi/180.0
    delta=edge-center; outer=max(step*2,_snap((delta-n*delta.dot(n)).length,step))
    thickness=max(step,min(outer-step,float(getattr(settings,'arch_thickness_steps',1))*step))
    inner=max(step,outer-thickness); height=_height(settings,step)
    # Each angular slice is a separate convex wedge so engine profiles remain BSP-valid.
    parts=[]; start=pi/2-angle*0.5
    for j in range(segments):
        a0=start+angle*j/segments; a1=start+angle*(j+1)/segments
        ring=[]
        for r,a in ((inner,a0),(outer,a0),(outer,a1),(inner,a1)):
            ring.append(center+u*(cos(a)*r)+v*(sin(a)*r))
        verts=ring+[p+n*height for p in ring]
        faces=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
        parts.append((verts,faces))
    return parts


def _primitive_parts(settings,a,b,u,v,n,step):
    kind=getattr(settings,'brush_type','CUBE')
    if kind=='CYLINDER': return [_radial_geometry(settings,a,b,u,v,n,step,False)]
    if kind=='CONE': return [_radial_geometry(settings,a,b,u,v,n,step,True)]
    if kind=='SPHERE': return [_sphere_geometry(settings,a,b,u,v,n,step)]
    if kind=='ARCH': return _arch_parts(settings,a,b,u,v,n,step)
    return [_box_geometry(settings,a,b,n,step)]


def _preview_geometry(settings,a,b,u,v,n,step):
    verts=[]; faces=[]
    for pv,pf in _primitive_parts(settings,a,b,u,v,n,step):
        off=len(verts); verts.extend(pv); faces.extend(tuple(off+i for i in f) for f in pf)
    return verts,faces


def _primitive_name(settings,engine_brush):
    kind=getattr(settings,'brush_type','CUBE')
    base={'CUBE':'Cube','CYLINDER':'Cylinder','CONE':'Cone','SPHERE':'Sphere','ARCH':'Arch'}.get(kind,'Brush')
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
                    region.y <= y < region.y + region.height)
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
    s = max(_HOVER_STEP * 0.18, 0.002)
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
            _HOVER_STEP = step
            _HOVER_AREA_PTR = context.area.as_pointer()
            context.area.tag_redraw()
        return {'PASS_THROUGH'}


class WL_OT_cube_brush_create(bpy.types.Operator):
    bl_idname = 'wavelength.cube_brush_create'
    bl_label = 'Create Cube Brush'
    bl_description = 'Create a cube brush with live snapping to the active engine grid'
    bl_options = {'REGISTER', 'UNDO'}

    _handle = None
    _start = None
    _hover = None
    _drag = None
    _plane_point = None
    _u = _v = _n = None
    _step_value = None
    _creating = False
    _stage = 'IDLE'
    _height_mouse_start = None
    _height_steps_start = 1

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
        s = max(self._step_value * 0.18, 0.002)
        p = self._hover
        marker = [(p.x-s,p.y,p.z),(p.x+s,p.y,p.z),(p.x,p.y-s,p.z),(p.x,p.y+s,p.z),(p.x,p.y,p.z-s),(p.x,p.y,p.z+s)]
        batch = batch_for_shader(shader, 'LINES', {'pos': marker})
        shader.bind(); shader.uniform_float('color', (1.0, 1.0, 1.0, 1.0)); batch.draw(shader)

        if self._creating and self._start is not None and self._drag is not None:
            verts, _faces = _preview_geometry(context.scene.wavelength, self._start, self._drag, self._u, self._v, self._n, self._step_value)
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

    primitive = ''

    def invoke(self, context, event):
        # This operator is invoked only by a LEFTMOUSE press in the WorkSpaceTool
        # keymap.  There is deliberately no persistent idle modal: once creation
        # finishes/cancels, Blender owns the UI event stream completely again.
        if not _event_in_window_region(context, event):
            return {'PASS_THROUGH'}
        if self.primitive:
            context.scene.wavelength.brush_type = self.primitive
        self._step_value = _step(context)
        if self._step_value is None:
            return {'CANCELLED'}
        self._creating = True
        self._stage = 'FOOTPRINT'
        self._sphere_axis = None
        self._start = self._drag = None
        self._plane_point = None
        self._update_hover(context, event, choose_plane=True)
        if self._hover is None:
            return {'PASS_THROUGH'}
        self._start = self._hover.copy()
        self._drag = self._hover.copy()
        self._handle = bpy.types.SpaceView3D.draw_handler_add(self._draw, (context,), 'WINDOW', 'POST_VIEW')
        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def _update_height_from_mouse(self, context, event):
        """Drive Height Steps from mouse motion along the projected brush normal."""
        if self._start is None or self._height_mouse_start is None:
            return
        p0 = view3d_utils.location_3d_to_region_2d(context.region, context.region_data, self._start)
        p1 = view3d_utils.location_3d_to_region_2d(context.region, context.region_data, self._start + self._n * self._step_value)
        dx = float(event.mouse_region_x - self._height_mouse_start[0])
        dy = float(event.mouse_region_y - self._height_mouse_start[1])
        if p0 is not None and p1 is not None:
            vx, vy = float(p1.x-p0.x), float(p1.y-p0.y)
            pixels = (vx*vx + vy*vy) ** 0.5
        else:
            vx = vy = 0.0; pixels = 0.0
        if pixels >= 4.0:
            # Signed displacement along one visible grid-height step.
            step_delta = round((dx*vx + dy*vy) / (pixels*pixels))
        else:
            # Looking almost straight down the extrusion axis: use vertical
            # screen motion so height remains editable instead of stalling.
            step_delta = round(dy / 24.0)
        context.scene.wavelength.brush_height_steps = max(1, min(256, self._height_steps_start + int(step_delta)))

    def _reset_prototype(self, context, event=None):
        self._creating = False
        self._stage = 'IDLE'
        self._sphere_axis = None
        self._height_mouse_start = None
        self._start = self._drag = None
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
            self._remove_draw();return {'CANCELLED'}
        in_window = _event_in_window_region(context, event)

        # Cancel only the current prototype. Keeping the tool alive avoids the
        # select/cancel/restart trap while still letting Blender own RMB/Esc when idle.
        if event.type in {'ESC', 'RIGHTMOUSE'}:
            if self._stage != 'IDLE':
                self._remove_draw()
                self._reset_prototype(context, event)
                return {'CANCELLED'}
            return {'PASS_THROUGH'}

        # Sphere has two real UV topology dimensions. Ctrl+axis constrains the
        # existing Ctrl+wheel topology editing while either prototype stage is live.
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
                if self._sphere_axis == 'Z':
                    st.brush_sides=max(4,min(64,st.brush_sides+delta))
                elif self._sphere_axis in {'X','Y'}:
                    st.brush_rings=max(2,min(32,st.brush_rings+delta))
                else:
                    st.brush_sides=max(4,min(64,st.brush_sides+delta))
                    st.brush_rings=max(2,min(32,st.brush_rings+delta))
            elif st.brush_type=='ARCH':
                st.arch_segments=max(3,min(32,st.arch_segments+delta))
            context.area.tag_redraw(); return {'RUNNING_MODAL'}

        # Blender always owns navigation and UI events. Wavelength consumes only
        # creation clicks/motion inside the drawable WINDOW region.
        if event.type in {'MIDDLEMOUSE','WHEELUPMOUSE','WHEELDOWNMOUSE','WHEELINMOUSE','WHEELOUTMOUSE',
                          'NDOF_MOTION','NDOF_BUTTON_MENU','NDOF_BUTTON_FIT'}:
            return {'PASS_THROUGH'}
        if event.type not in {'MOUSEMOVE','LEFTMOUSE'}:
            return {'PASS_THROUGH'}
        if not in_window:
            return {'PASS_THROUGH'}

        if event.type == 'MOUSEMOVE':
            if self._stage == 'FOOTPRINT':
                self._hover = _snapped_point(context, event, self._plane_point, self._u, self._v, self._n, self._step_value)
                if self._hover is not None:
                    self._drag = self._hover.copy()
                context.area.tag_redraw()
                return {'RUNNING_MODAL'}
            if self._stage == 'HEIGHT':
                self._update_height_from_mouse(context, event)
                context.area.tag_redraw()
                return {'RUNNING_MODAL'}

            # Idle is observational only: update the snap marker, but don't own
            # Blender's mouse stream. This is what keeps selection/gizmos/UI fluid.
            self._update_hover(context, event, choose_plane=True)
            context.area.tag_redraw()
            return {'PASS_THROUGH'}

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            if self._stage == 'IDLE':
                # Click 1: lock the start point and begin footprint/radius editing.
                self._update_hover(context, event, choose_plane=True)
                if self._hover is None:
                    return {'PASS_THROUGH'}
                self._start = self._hover.copy()
                self._drag = self._hover.copy()
                self._creating = True
                self._stage = 'FOOTPRINT'
                self._sphere_axis = None
                context.area.tag_redraw()
                return {'RUNNING_MODAL'}

            if self._stage == 'FOOTPRINT':
                # Click 2: freeze footprint and enter height-only editing.
                drag = _snapped_point(context, event, self._plane_point, self._u, self._v, self._n, self._step_value)
                if drag is not None:
                    self._drag = drag.copy()
                if self._drag is None or (self._drag - self._start).length < self._step_value * 0.5:
                    return {'RUNNING_MODAL'}
                self._stage = 'HEIGHT'
                self._height_mouse_start = (event.mouse_region_x, event.mouse_region_y)
                self._height_steps_start = int(context.scene.wavelength.brush_height_steps)
                context.area.tag_redraw()
                return {'RUNNING_MODAL'}

            if self._stage == 'HEIGHT':
                # Click 3: commit exactly the frozen footprint + snapped height preview.
                st=context.scene.wavelength
                is_engine_brush=profiles.get(st.engine).get('brush_semantics',False)
                name=_primitive_name(st,is_engine_brush)
                created=[]
                parts=_primitive_parts(st,self._start,self._drag,self._u,self._v,self._n,self._step_value)
                if st.brush_type in {'ARCH','SPHERE'}:
                    from . import primitive_ui
                    from mathutils import Matrix
                    root=bpy.data.objects.new(name,None);context.collection.objects.link(root)
                    root.location=self._start;root['wl_exclude']=True
                    radius=max(self._step_value*(2 if st.brush_type=='ARCH' else 1),_snap((self._drag-self._start).length,self._step_value))/profiles.unit_meters(st)
                    values=dict(primitive_ui.DEFAULTS,radius=max(radius,2.),depth=_height(st,self._step_value)/profiles.unit_meters(st),thickness=min(radius-float(st.grid_step),st.arch_thickness_steps*float(st.grid_step)),angle=st.arch_angle,segments=st.arch_segments)
                    basis=Matrix((self._u,-self._n,self._v)).transposed().to_4x4();basis.translation=self._start;root.matrix_world=basis
                    context.view_layer.update()
                    try:primitive_ui.rebuild(root,st.brush_type,values,context)
                    except ValueError as exc:
                        bpy.data.objects.remove(root,do_unlink=True);self.report({'ERROR'},str(exc));self._remove_draw();return {'CANCELLED'}
                    created=[root];parts=[]
                for index,(verts,faces) in enumerate(parts):
                    part_name=name if len(parts)==1 else f'{name} {index+1:02d}'
                    mesh=bpy.data.meshes.new(part_name); mesh.from_pydata(verts,[],faces); mesh.update()
                    obj=bpy.data.objects.new(part_name,mesh); context.collection.objects.link(obj)
                    if is_engine_brush:
                        scene.mark_brush(obj); obj['wl_created_engine']=st.engine
                    created.append(obj)

                # Origin-to-geometry is a brush finalization invariant. For an Arch,
                # each convex wedge receives its own geometry origin.
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
        layout.prop(st,'brush_height_steps',text='Height Steps')
        if st.brush_type in {'CYLINDER','CONE','SPHERE'}:
            layout.prop(st,'brush_sides',text='Segments')
        if st.brush_type=='SPHERE': layout.prop(st,'brush_rings',text='Rings')
        if st.brush_type=='ARCH':
            layout.prop(st,'arch_segments',text='Segments'); layout.prop(st,'arch_angle',text='Arc')
            layout.prop(st,'arch_thickness_steps',text='Thickness Steps')
        if st.engine!='blender': layout.prop(st,'grid_step',text='Grid')
        layout.label(text='Ctrl+Wheel: subdivisions')

def _tool_class(name,idname,label,primitive,operator_id,icon='ops.generic.select_box'):
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

WL_Tool_CreateCubeBrush=_tool_class('WL_Tool_CreateCubeBrush','wavelength.create_cube_brush_tool','Create Cube Brush','CUBE',WL_OT_cube_brush.bl_idname)
WL_Tool_CreateCylinderBrush=_tool_class('WL_Tool_CreateCylinderBrush','wavelength.create_cylinder_brush_tool','Create Cylinder Brush','CYLINDER',WL_OT_cylinder_brush.bl_idname)
WL_Tool_CreateConeBrush=_tool_class('WL_Tool_CreateConeBrush','wavelength.create_cone_brush_tool','Create Cone Brush','CONE',WL_OT_cone_brush.bl_idname)
WL_Tool_CreateSphereBrush=_tool_class('WL_Tool_CreateSphereBrush','wavelength.create_sphere_brush_tool','Create Sphere Brush','SPHERE',WL_OT_sphere_brush.bl_idname)
WL_Tool_CreateArchBrush=_tool_class('WL_Tool_CreateArchBrush','wavelength.create_arch_brush_tool','Create Arch Brush','ARCH',WL_OT_arch_brush.bl_idname)
TOOLS=(WL_Tool_CreateCubeBrush,WL_Tool_CreateCylinderBrush,WL_Tool_CreateConeBrush,WL_Tool_CreateSphereBrush,WL_Tool_CreateArchBrush)

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

