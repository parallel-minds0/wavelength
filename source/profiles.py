"""Engine authoring profiles.  Tools read units/behavior from the active profile."""
PROFILES = {
 'blender': {'label':'Blender — No Engine — Any Platform', 'format':None, 'grid':None, 'unit_meters':1.0,
             'stages':[], 'bsp_version':None, 'brush_semantics':False, 'create_cube_label':'Create Cube'},
 'quake': {'label':'Quake — Quake — Custom Platform', 'format':'classic', 'grid':16, 'unit_meters':0.0254,
           'stages':['qbsp','vis','light'], 'bsp_version':29, 'brush_semantics':True, 'create_cube_label':'Create Cube Brush'},
 'goldsrc': {'label':'Half-Life — GoldSrc — Custom Platform', 'family':'goldsrc', 'format':'valve220', 'grid':16, 'unit_meters':0.0254,
             'stages':['hlcsg','hlbsp','hlvis','hlrad'], 'bsp_version':30, 'brush_semantics':True, 'create_cube_label':'Create Cube Brush'},
 'goldsrc_linux': {'label':'Half-Life — GoldSrc — Linux', 'family':'goldsrc', 'platform':'linux', 'format':'valve220', 'grid':16, 'unit_meters':0.0254,
             'stages':['hlcsg','hlbsp','hlvis','hlrad'], 'bsp_version':30, 'brush_semantics':True, 'create_cube_label':'Create Cube Brush'},
}
SCHEMA_VERSION=1

def get(engine):
    return PROFILES.get(engine, PROFILES['blender'])

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
    if not profile.get('brush_semantics'):
        return None
    return engine_to_world(settings, grid_step_units(settings))


def create_cube_label(settings):
    return get(settings.engine).get('create_cube_label', 'Create Cube')


def unit_meters(settings):
    """Meters represented by one authoring unit for the active profile."""
    return float(get(settings.engine).get('unit_meters', 1.0))

def engine_to_world(settings, value):
    return float(value) * unit_meters(settings)

def world_to_engine(settings, value):
    return float(value) / unit_meters(settings)

def snap_world_value(settings, value):
    """Snap a world-space scalar through engine-unit space, then convert back."""
    if not get(settings.engine).get('brush_semantics'):
        return float(value)
    step = grid_step_units(settings)
    return engine_to_world(settings, round(world_to_engine(settings, value) / step) * step)


def snap_world_length(settings, value, minimum_steps=1):
    """Snap a positive world-space length to an exact engine-grid multiple."""
    if not get(settings.engine).get('brush_semantics'):
        return float(value)
    step = grid_step_units(settings)
    units = abs(world_to_engine(settings, value))
    return engine_to_world(settings, max(float(minimum_steps) * step, round(units / step) * step))
