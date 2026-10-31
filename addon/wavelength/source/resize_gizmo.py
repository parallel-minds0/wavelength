"""Engine-mode brush boundary resize gizmos.

Unlike Blender's proportional Scale transform, these handles move one brush
boundary while the opposite boundary remains fixed.  The dragged boundary is
quantized to Wavelength's engine grid during the interaction.
"""
import bpy
import bmesh
from mathutils import Matrix, Vector
from . import scene, editor, profiles, workspace, tool_snap

_GROUP = 'WL_GGT_engine_resize'
_pending_origins = {}


def _finish_origins():
    """Rebase after the native handle releases, never during its transaction."""
    for key, (obj, gizmo) in tuple(_pending_origins.items()):
        try:
            if gizmo.is_modal:
                continue
            if obj.name in bpy.data.objects:
                if obj.type=='MESH':scene.origin_to_geometry(obj)
                else:
                    try:bpy.ops.ed.undo_push(message='Resize Procedural Geometry')
                    except RuntimeError:pass
        except ReferenceError:
            pass
        _pending_origins.pop(key, None)
    return .02 if _pending_origins else None


def _brush(context):
    obj = context.active_object
    from . import primitive_ui,procedural
    root=primitive_ui.root_for(obj)
    if root and procedural.state(root)=='PROCEDURAL' and context.mode=='EDIT_MESH':
        settings=getattr(context.scene,'wavelength',None)
        return root if settings and settings.grid_mode=='ENGINE' else None
    if not obj or obj.type != 'MESH' or obj.mode != 'EDIT' or obj.get('wl_role') != 'BRUSH':
        return None
    settings = getattr(context.scene, 'wavelength', None)
    if not settings or settings.grid_mode != 'ENGINE':
        return None
    return obj


def _local_bounds(obj):
    if obj.type!='MESH':
        from . import primitive_ui
        inverse=obj.matrix_world.inverted_safe();graph=bpy.context.evaluated_depsgraph_get()
        values=[inverse @ part.matrix_world @ Vector(corner)
                for part in primitive_ui.parts_for(obj)
                for corner in part.evaluated_get(graph).bound_box]
        if not values:return None
        return ([min(v[i] for v in values) for i in range(3)],
                [max(v[i] for v in values) for i in range(3)])
    if not obj.data.vertices:
        return None
    if obj.mode == 'EDIT':
        bm = bmesh.from_edit_mesh(obj.data)
        values = [v.co for v in bm.verts]
    else:
        values = [v.co for v in obj.data.vertices]
    return ([min(v[i] for v in values) for i in range(3)],
            [max(v[i] for v in values) for i in range(3)])


def _snap(value, step):
    return round(value / step) * step


def _handle_matrix(matrix, point, direction):
    """Inherit world position/direction, never object scale or shear."""
    world_direction=(matrix.to_3x3() @ direction).normalized()
    result=world_direction.to_track_quat('Z','Y').to_matrix().to_4x4()
    result.translation=matrix @ point
    return result


def _boundary_delta(matrix, anchor, axis, sign, distance, step, snap):
    """Convert handle travel to local displacement, snapping in world space."""
    direction = matrix.to_3x3().col[axis].copy()
    length = direction.length
    if length < 1e-12:
        return 0.0
    delta = sign * distance / length
    if snap:
        # Align the dominant world coordinate along the handle's direction.
        # Rounding a local coordinate ignores translated origins/object scale.
        component = max(range(3), key=lambda i: abs(direction[i]))
        start = (matrix @ anchor)[component]
        delta = (_snap(start + direction[component] * delta, step) - start) / direction[component]
    return delta


def _boundary_vertices(bm, axis, sign):
    """Resolve a whole outward face, including coplanar triangulated pieces.

    Coordinate extrema identify corners on sloped faces, not face membership.
    Capture membership before dragging and retain it for the entire interaction.
    """
    bm.normal_update()
    bm.verts.index_update()
    direction = Vector(tuple(sign if i == axis else 0 for i in range(3)))
    faces = [f for f in bm.faces if not f.hide and f.normal.dot(direction) > 1e-6]
    if not faces:
        return set()
    alignment = max(f.normal.dot(direction) for f in faces)
    face = max((f for f in faces if f.normal.dot(direction) >= alignment - 1e-5),
               key=lambda f: f.calc_center_median().dot(direction))
    normal = face.normal.copy()
    origin = face.verts[0].co
    extent = max(((v.co - origin).length for v in bm.verts), default=1.0)
    tolerance = max(1e-6, extent * 1e-6)
    return {v.index for f in faces
            if f.normal.dot(normal) >= 1 - 1e-5 and
            all(abs((v.co - origin).dot(normal)) <= tolerance for v in f.verts)
            for v in f.verts}


class WL_GGT_engine_resize(bpy.types.GizmoGroup):
    bl_idname = _GROUP
    bl_label = 'Wavelength Engine Resize'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT'}

    @classmethod
    def poll(cls, context):
        settings = getattr(getattr(context, 'scene', None), 'wavelength', None)
        # These boundary handles are independent of Blender's active toolbar
        # tool. Switching to Move/Rotate must not remove shape editing controls.
        return (workspace.active(context, 'gizmos') and context.mode=='EDIT_MESH' and settings is not None and
                context.space_data.show_gizmo and
                settings.grid_mode == 'ENGINE' and _brush(context) is not None)

    def setup(self, context):
        self._handles = []
        # One arrow per local brush boundary: -X,+X,-Y,+Y,-Z,+Z.
        for axis in range(3):
            for sign in (-1, 1):
                gizmo = self.gizmos.new('GIZMO_GT_arrow_3d')
                gizmo.draw_style = 'BOX'
                gizmo.length = 1.15
                gizmo.line_width = 3
                gizmo.use_draw_modal = True
                gizmo.use_draw_value = False
                gizmo.scale_basis = 0.48
                color=((0.95,0.12,0.12),(0.18,0.85,0.2),(0.18,0.4,1.0))[axis]
                gizmo.color = color
                gizmo.alpha = 0.9
                gizmo.color_highlight = tuple(min(1.,c+.22) for c in color)
                gizmo.alpha_highlight = 1.0
                state = {'axis': axis, 'sign': sign, 'obj': None, 'base_min': None,
                         'base_max': None, 'base_verts': None, 'unit': None,
                         'last': 0.0, 'undo_started': False}

                def getter(st=state):
                    # Arrow offset is interaction-local. Reset when not modal.
                    return 0.0

                def setter(value, st=state, handle=gizmo):
                    obj = st.get('obj')
                    if obj is None or obj.name not in bpy.data.objects:
                        return
                    axis = st['axis']; sign = st['sign']
                    settings = bpy.context.scene.wavelength
                    unit = profiles.unit_meters(settings)
                    step = profiles.active_grid_step_meters(settings)
                    # Snap the actual world boundary, independently of its origin.
                    raw_delta = float(value)
                    matrix=st['base_matrix'] if obj.type!='MESH' else obj.matrix_world
                    base_min, base_max = st['base_min'], st['base_max']
                    base_face = base_max[axis] if sign > 0 else base_min[axis]
                    target = base_face + _boundary_delta(matrix, st['side_anchor'], axis, sign,
                                                         raw_delta, step, tool_snap.grid_enabled(bpy.context))
                    delta = target - base_face
                    # Prevent inversion/collapse; one engine unit is the minimum thickness.
                    opposite = base_min[axis] if sign > 0 else base_max[axis]
                    local_unit = unit / max(matrix.to_3x3().col[axis].length, 1e-12)
                    if sign > 0:
                        target = max(target, opposite + local_unit)
                    else:
                        target = min(target, opposite - local_unit)
                    delta = target - base_face
                    if abs(delta - st.get('last', 0.0)) < 1e-10:
                        return
                    st['last'] = delta
                    if obj.type!='MESH':
                        # Stretch the live assembly about its opposite boundary.
                        # No mesh/modifier replacement and no forced finalization.
                        pivot=Vector((0,0,0));pivot[axis]=opposite
                        scale=Vector((1,1,1));scale[axis]=(target-opposite)/(base_face-opposite)
                        if not st.get('undo_started'):
                            try:bpy.ops.ed.undo_push(message='Begin Procedural Resize')
                            except RuntimeError:pass
                            st['undo_started']=True
                        obj.matrix_world=matrix @ Matrix.Translation(pivot) @ Matrix.Diagonal((*scale,1.)) @ Matrix.Translation(-pivot)
                        _pending_origins[obj.as_pointer()]=(obj,handle)
                        if not bpy.app.timers.is_registered(_finish_origins):bpy.app.timers.register(_finish_origins,first_interval=.02)
                        return
                    # The gizmo exists only while the brush is already in Mesh Edit Mode.
                    # Never switch modes from a target setter: doing so invalidates Blender's
                    # active gizmo transaction.  Edit the live BMesh in-place so Ctrl+Z remains
                    # part of Blender's native Edit Mode undo history.
                    if obj.mode != 'EDIT' or bpy.context.mode != 'EDIT_MESH':
                        return
                    editor.note_edit_session(obj)
                    if not st.get('undo_started'):
                        try:
                            bpy.ops.ed.undo_push(message='Wavelength Resize Brush')
                        except RuntimeError:
                            pass
                        st['undo_started'] = True
                    bm = bmesh.from_edit_mesh(obj.data)
                    bm.verts.ensure_lookup_table()
                    for index, (vertex, base) in enumerate(zip(bm.verts, st['base_verts'])):
                        co = Vector(base)
                        if index in st['side_vertices']:
                            co[axis] = base[axis] + delta
                        vertex.co = co
                    bmesh.update_edit_mesh(obj.data, loop_triangles=False, destructive=False)
                    _pending_origins[obj.as_pointer()] = (obj, handle)
                    if not bpy.app.timers.is_registered(_finish_origins):
                        bpy.app.timers.register(_finish_origins, first_interval=.02)

                gizmo.target_set_handler('offset', get=getter, set=setter)
                self._handles.append((gizmo, state))

    def refresh(self, context):
        obj = _brush(context)
        if obj is None:
            return
        if obj.type=='MESH':editor.note_edit_session(obj)
        bounds = _local_bounds(obj)
        if bounds is None:
            return
        low, high = bounds
        center = [(low[i] + high[i]) * 0.5 for i in range(3)]
        unit = profiles.unit_meters(context.scene.wavelength)
        for gizmo, st in self._handles:
            # Never move the gizmo or replace its immutable drag baseline while modal.
            if getattr(gizmo, 'is_modal', False):
                continue
            axis, sign = st['axis'], st['sign']
            p = Vector(center)
            p[axis] = high[axis] if sign > 0 else low[axis]
            # Orient arrow's local +Z along the requested local axis/sign.
            direction = Vector((0, 0, 0)); direction[axis] = sign
            gizmo.matrix_basis = _handle_matrix(obj.matrix_world,p,direction)
            # Capture a fresh baseline whenever Blender asks us to refresh outside a drag.
            # target_set_handler's setter then works only from this immutable baseline.
            st.update(obj=obj, base_min=list(low), base_max=list(high),
                      base_matrix=obj.matrix_world.copy(),
                      base_verts=[tuple(v.co) for v in bmesh.from_edit_mesh(obj.data).verts] if obj.type=='MESH' else [],
                      side_vertices=_boundary_vertices(bmesh.from_edit_mesh(obj.data), axis, sign) if obj.type=='MESH' else set(),
                      unit=unit, last=0.0, undo_started=False)
            members = st['side_vertices']
            st['side_anchor'] = (sum((Vector(st['base_verts'][i]) for i in members), Vector()) / len(members)
                                 if members else p.copy())


_CLASSES = [WL_GGT_engine_resize]


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    if bpy.app.timers.is_registered(_finish_origins):
        bpy.app.timers.unregister(_finish_origins)
    _pending_origins.clear()
    for cls in reversed(_CLASSES):
        try: bpy.utils.unregister_class(cls)
        except RuntimeError: pass
