"""Engine authoring profiles.  Tools read units/behavior from the active profile."""
from .profile_registry import TEMPLATES
PROFILES = TEMPLATES.selectable()
SCHEMA_VERSION=2

def is_mesh_export(engine):return bool(get(engine).get('mesh_export'))

# Preserve persisted RNA enum numbers when adding profiles or changing dict order.
PROFILE_ORDER=('blender','quake','goldsrc','goldsrc_windows','goldsrc_linux','goldsrc_linux_steam','source_hl2_linux','source_hl2_windows','source_gmod_windows','godot4','source2_cs2_windows','source_windows')
PROFILE_ITEMS=[(key,PROFILES[key]['label'],PROFILES[key]['label'],index) for index,key in enumerate(PROFILE_ORDER)]

def is_source(engine):
    return family(engine)=='source'

def is_source2(engine):return family(engine)=='source2'

def uses_valve_axes(engine):
    return is_goldsrc(engine) or is_source(engine)


def get(engine):
    if engine in PROFILES:return PROFILES[engine]
    if engine in TEMPLATES.definitions:return TEMPLATES.resolve(engine)
    return PROFILES['blender']

# docs:begin convex-contract
def requires_convex_brushes(engine):
    """Return whether the profile explicitly requires convex BSP brushes.

    Unrecognized or mesh-based profiles are unrestricted unless they opt in.
    This is an authoring/export constraint, independent of Blender's display.
    """
    # A new engine must not inherit BSP constraints merely because it uses brushes.
    return bool(get(engine).get('requires_convex_brushes',False))
# docs:end convex-contract


def family(engine):
    return get(engine).get('family', engine)

def is_goldsrc(engine):
    return family(engine) == 'goldsrc'


def grid_step_units(settings):
    """Selected engine-grid increment, in engine authoring units."""
    return float(settings.grid_step)

def active_grid_step_meters(settings):
    """Authoritative creation/grid increment for the active engine profile.

    None means the profile has no engine-unit snap; Blender viewport-grid snapping is resolved from the active 3D view by the creation tool.
    """
    profile = get(settings.engine)
    if profile.get('grid') is None:
        return None
    return engine_to_world(settings, grid_step_units(settings))


def create_cube_label(settings):
    return get(settings.engine).get('create_cube_label', 'Create Cube')


def unit_meters(settings):
    """Meters represented by one authoring unit for the active profile."""
    return float(getattr(settings, 'unit_scale', get(settings.engine).get('unit_meters', 1.0))) if settings.engine!='blender' else 1.0

def engine_to_world(settings, value):
    return float(value) * unit_meters(settings)

def world_to_engine(settings, value):
    return float(value) / unit_meters(settings)

def snap_enabled(settings, context=None):
    """Whether grid snapping should be enforced for the active profile."""
    if get(settings.engine).get('brush_semantics'):
        return True
    if bool(getattr(settings, 'snap_to_grid', False)):
        return True
    if context is not None:
        ts = getattr(getattr(context, 'scene', None), 'tool_settings', None)
        if bool(getattr(ts, 'use_snap', False)):
            return True
    return False


def active_snap_step_units(settings, context=None):
    """Active snap step in authoring units (engine units or Blender meters), or None if unsnapped."""
    if get(settings.engine).get('brush_semantics'):
        return grid_step_units(settings)
    if snap_enabled(settings, context):
        return max(1e-4, float(getattr(settings, 'metric_grid_step', 1.0)))
    return None


def active_snap_step_meters(settings, context=None):
    """Active snap step in world meters, or None if unsnapped."""
    if get(settings.engine).get('brush_semantics'):
        return engine_to_world(settings, grid_step_units(settings))
    if snap_enabled(settings, context):
        return max(1e-4, float(getattr(settings, 'metric_grid_step', 1.0)))
    return None


def snap_world_value(settings, value, context=None):
    """Snap a world-space scalar through engine-unit space (or Blender grid if enabled), then convert back."""
    if get(settings.engine).get('brush_semantics'):
        step = grid_step_units(settings)
        return engine_to_world(settings, round(world_to_engine(settings, value) / step) * step)
    step_m = active_snap_step_meters(settings, context)
    if step_m:
        return round(float(value) / step_m) * step_m
    return float(value)


def snap_world_length(settings, value, minimum_steps=1, context=None):
    """Snap a positive world-space length to an exact grid multiple when snapping is active."""
    if get(settings.engine).get('brush_semantics'):
        step = grid_step_units(settings)
        units = abs(world_to_engine(settings, value))
        return engine_to_world(settings, max(float(minimum_steps) * step, round(units / step) * step))
    step_m = active_snap_step_meters(settings, context)
    if step_m:
        return max(float(minimum_steps) * step_m, round(abs(float(value)) / step_m) * step_m)
    return max(1e-4, abs(float(value)))


def display_grid(settings):
    """Parent spacing in meters and subdivisions, independent of Blender LOD."""
    metric = get(settings.engine).get('grid') is None or settings.grid_mode == 'BLENDER'
    spacing = float(getattr(settings, 'metric_grid_step', 1.0)) if metric else active_grid_step_meters(settings)
    count = int(getattr(settings, 'grid_subdivisions', 0)) or (10 if metric else int(get(settings.engine).get('grid_subdivisions', 8)))
    return spacing, max(2, count)

