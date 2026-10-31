"""Blender owns snap enable/targets; the profile supplies engine grid spacing."""

def profile_grid_active(context):
    """Opt into engine-grid placement only when this profile uses its grid."""
    from . import profiles
    settings=getattr(context.scene,'wavelength',None)
    if settings is None:return False
    spacing=profiles.active_grid_step_meters(settings)
    return getattr(settings,'grid_mode','BLENDER')=='ENGINE' and spacing is not None and spacing>0
def enabled(context, event=None, kind='TRANSLATE'):
    if profile_grid_active(context):
        from . import workspace
        if workspace.active(context):return True
    ts = context.scene.tool_settings
    active = bool(ts.use_snap)
    if event is not None and getattr(event, 'ctrl', False):
        active = not active
    return active and bool(getattr(ts, 'use_snap_' + kind.lower(), True))


def grid_enabled(context, event=None, kind='TRANSLATE'):
    if profile_grid_active(context):
        from . import workspace
        if workspace.active(context):return True
    return enabled(context, event, kind) and bool(set(context.scene.tool_settings.snap_elements) & {'INCREMENT', 'GRID'})


def step(context):
    from . import profiles
    st = context.scene.wavelength
    if profile_grid_active(context):
        return profiles.active_grid_step_meters(st)
    if st.engine=='blender':return max(1e-6,float(getattr(context.space_data.overlay,'grid_scale',1)))
    return max(1e-6,float(getattr(st,'metric_grid_step',1)))


def move_anchor(obj):
    """Brushes align a world boundary; their centered origin may be off-grid."""
    from . import primitive_ui
    root=primitive_ui.root_for(obj)
    if root:
        from mathutils import Vector
        import bpy
        graph=bpy.context.evaluated_depsgraph_get()
        points=[p.matrix_world@Vector(c) for p in primitive_ui.parts_for(root) for c in p.evaluated_get(graph).bound_box]
        if points:return Vector(tuple(min(p[i] for p in points) for i in range(3)))
    if (obj.type == 'MESH' and obj.get('wl_role') == 'BRUSH' and
            not obj.get('wl_primitive') and not obj.get('wl_assembly') and obj.data.vertices):
        from mathutils import Vector
        points = [obj.matrix_world @ v.co for v in obj.data.vertices]
        return Vector(tuple(min(p[i] for p in points) for i in range(3)))
    return obj.matrix_world.translation.copy()


def point(context, event, value, origin):
    """Profile grids use world origin; other grids retain Blender's snap mode."""
    if not grid_enabled(context, event):
        return value
    spacing = step(context)
    absolute = (profile_grid_active(context) or 'GRID' in context.scene.tool_settings.snap_elements or
                getattr(context.scene.tool_settings, 'use_snap_grid_absolute', False))
    anchor = value * 0 if absolute else origin
    return anchor + type(value)(tuple(round((value[i]-anchor[i])/spacing)*spacing for i in range(3)))
