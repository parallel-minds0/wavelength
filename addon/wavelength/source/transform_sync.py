"""Settle-time engine-grid snapping for Blender-native brush transforms.

This never replaces G/S/R.  It waits until Blender has stopped changing a brush,
then resolves translation and scale through the active engine profile grid.
"""
import bpy
from mathutils import Vector
from . import profiles, scene

_state = {}
_SETTLE_TICKS = 3


def _signature(obj):
    m = obj.matrix_world
    return tuple(round(v, 10) for row in m for v in row)


def _world_bounds(obj):
    pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    if not pts:
        return None
    lo = Vector(tuple(min(p[i] for p in pts) for i in range(3)))
    hi = Vector(tuple(max(p[i] for p in pts) for i in range(3)))
    return lo, hi


def _snap_object(obj, settings, previous_matrix):
    step = profiles.active_snap_step_meters(settings)
    if not step or step <= 0:
        return
    current = obj.matrix_world.copy()
    # Translation: exact grid coordinates, independent of Blender display scale.
    current.translation = Vector(tuple(profiles.snap_world_value(settings, x) for x in current.translation))

    if obj.type == 'MESH' and obj.data is not None:
        prev_scale = previous_matrix.to_scale() if previous_matrix is not None else current.to_scale()
        cur_scale = current.to_scale()
        scale_changed = any(abs(cur_scale[i] - prev_scale[i]) > 1e-7 for i in range(3))
        if scale_changed:
            obj.matrix_world = current
            bounds = _world_bounds(obj)
            if bounds:
                lo, hi = bounds
                dims = hi - lo
                factors = [1.0, 1.0, 1.0]
                for i in range(3):
                    if dims[i] > 1e-9:
                        snapped = profiles.snap_world_length(settings, dims[i])
                        factors[i] = snapped / dims[i]
                for col in range(3):
                    f = factors[col]
                    for row in range(3):
                        current[row][col] *= f
    obj.matrix_world = current


def tick():
    live = set()
    for owner in bpy.data.scenes:
        settings = getattr(owner, 'wavelength', None)
        if not settings or not profiles.snap_enabled(settings):
            continue
        if settings.engine != 'blender' and settings.grid_mode != 'ENGINE':
            continue
        for obj in owner.objects:
            if obj.library or getattr(obj, 'mode', 'OBJECT') != 'OBJECT':
                continue
            is_root = bool(obj.get('wl_primitive') or obj.get('wl_assembly'))
            if not is_root:
                if obj.type != 'MESH':
                    continue
                if settings.engine != 'blender' and obj.get('wl_role') != 'BRUSH':
                    continue
                if obj.parent and (obj.parent.get('wl_primitive') or obj.parent.get('wl_assembly')) and obj.parent.get('wl_assembly_locked', True):
                    continue
            key = obj.as_pointer(); live.add(key)
            sig = _signature(obj)
            st = _state.get(key)
            if st is None:
                _state[key] = {'sig': sig, 'stable': 0, 'matrix': obj.matrix_world.copy(), 'settled': sig}
                continue
            if sig != st['sig']:
                st['previous'] = st.get('matrix', obj.matrix_world.copy())
                st['matrix'] = obj.matrix_world.copy()
                st['sig'] = sig; st['stable'] = 0
                continue
            if sig != st.get('settled'):
                st['stable'] += 1
                if st['stable'] >= _SETTLE_TICKS:
                    _snap_object(obj, settings, st.get('previous'))
                    st['sig'] = _signature(obj); st['settled'] = st['sig']
                    st['matrix'] = obj.matrix_world.copy(); st['stable'] = 0
    for key in list(_state):
        if key not in live: _state.pop(key, None)
    return .08



def register():
    _state.clear()
    if not bpy.app.timers.is_registered(tick):
        bpy.app.timers.register(tick, first_interval=.08, persistent=True)


def unregister():
    if bpy.app.timers.is_registered(tick): bpy.app.timers.unregister(tick)
    _state.clear()
