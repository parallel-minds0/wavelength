"""Engine-mode brush boundary resize gizmos.

Unlike Blender's proportional Scale transform, these handles move one brush
boundary while the opposite boundary remains fixed.  The dragged boundary is
quantized to Wavelength's engine grid during the interaction.
"""
import bpy
import bmesh
from mathutils import Matrix, Vector
from . import scene, editor, profiles

_GROUP = 'WL_GGT_engine_resize'


def _brush(context):
    obj = context.active_object
    if not obj or obj.type != 'MESH' or obj.mode != 'EDIT' or obj.get('wl_role') != 'BRUSH':
        return None
    settings = getattr(context.scene, 'wavelength', None)
    if not settings or settings.grid_mode != 'ENGINE':
        return None
    return obj


def _local_bounds(obj):
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


class WL_GGT_engine_resize(bpy.types.GizmoGroup):
    bl_idname = _GROUP
    bl_label = 'Wavelength Engine Resize'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_options = {'3D', 'PERSISTENT'}

    @classmethod
    def poll(cls, context):
        settings = getattr(getattr(context, 'scene', None), 'wavelength', None)
        return (context.mode == 'EDIT_MESH' and settings is not None and
                settings.grid_mode == 'ENGINE' and _brush(context) is not None)

    def setup(self, context):
        self._handles = []
        # One arrow per local brush boundary: -X,+X,-Y,+Y,-Z,+Z.
        for axis in range(3):
            for sign in (-1, 1):
                gizmo = self.gizmos.new('GIZMO_GT_arrow_3d')
                gizmo.draw_style = 'BOX'
                gizmo.length = 0.8
                gizmo.line_width = 2
                gizmo.use_draw_modal = True
                gizmo.use_draw_value = False
                gizmo.scale_basis = 0.35
                gizmo.color = (0.8, 0.8, 0.8)
                gizmo.alpha = 0.65
                gizmo.color_highlight = (1.0, 1.0, 1.0)
                gizmo.alpha_highlight = 1.0
                state = {'axis': axis, 'sign': sign, 'obj': None, 'base_min': None,
                         'base_max': None, 'base_verts': None, 'unit': None,
                         'last': 0.0, 'undo_started': False}

                def getter(st=state):
                    # Arrow offset is interaction-local. Reset when not modal.
                    return 0.0

                def setter(value, st=state):
                    obj = st.get('obj')
                    if obj is None or obj.name not in bpy.data.objects:
                        return
                    axis = st['axis']; sign = st['sign']
                    settings = bpy.context.scene.wavelength
                    unit = profiles.unit_meters(settings)
                    step = profiles.active_grid_step_meters(settings)
                    # Arrow value is a Blender-space displacement along its displayed direction.
                    # Snap the dragged boundary's world/local coordinate, not object scale.
                    raw_delta = float(value)
                    base_min, base_max = st['base_min'], st['base_max']
                    base_face = base_max[axis] if sign > 0 else base_min[axis]
                    target = _snap(base_face + sign * raw_delta, step)
                    delta = target - base_face
                    # Prevent inversion/collapse; one engine unit is the minimum thickness.
                    opposite = base_min[axis] if sign > 0 else base_max[axis]
                    if sign > 0:
                        target = max(target, opposite + unit)
                    else:
                        target = min(target, opposite - unit)
                    delta = target - base_face
                    if abs(delta - st.get('last', 0.0)) < 1e-10:
                        return
                    st['last'] = delta
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
                    for vertex, base in zip(bm.verts, st['base_verts']):
                        co = Vector(base)
                        on_side = abs(base[axis] - base_face) <= 1e-7
                        if on_side:
                            co[axis] = base[axis] + delta
                        vertex.co = co
                    bmesh.update_edit_mesh(obj.data, loop_triangles=False, destructive=False)

                gizmo.target_set_handler('offset', get=getter, set=setter)
                self._handles.append((gizmo, state))

    def refresh(self, context):
        obj = _brush(context)
        if obj is None:
            return
        editor.note_edit_session(obj)
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
            q = direction.to_track_quat('Z', 'Y')
            gizmo.matrix_basis = obj.matrix_world @ Matrix.Translation(p) @ q.to_matrix().to_4x4()
            # Capture a fresh baseline whenever Blender asks us to refresh outside a drag.
            # target_set_handler's setter then works only from this immutable baseline.
            st.update(obj=obj, base_min=list(low), base_max=list(high),
                      base_verts=[tuple(v.co) for v in bmesh.from_edit_mesh(obj.data).verts], unit=unit, last=0.0, undo_started=False)


_CLASSES = [WL_GGT_engine_resize]


def register():
    for cls in _CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(_CLASSES):
        try: bpy.utils.unregister_class(cls)
        except RuntimeError: pass
