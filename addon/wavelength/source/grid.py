"""Blender-native viewport grid integration.

Wavelength never draws a custom grid. Engine profiles configure Blender's native
viewport grid for visuals only; profile/tool code remains authoritative for snap.
"""
import bpy
from pathlib import Path

# Blender's native floor grid divides grid_scale by grid_subdivisions for the
# visible fine interval. Keep a conventional subdivision count and choose the
# scale so one visible fine interval equals one Wavelength engine-grid step.
_EXPERIMENTAL = (Path(__file__).resolve().parents[1]/'experimental-grid.json').is_file()
_NATIVE_SUBDIVISIONS = 10 if _EXPERIMENTAL else 1


def _engine_visuals(overlay, step):
    overlay.show_floor = True
    overlay.show_ortho_grid = True
    overlay.grid_subdivisions = _NATIVE_SUBDIVISIONS
    # No Blender-side subdivision math: one native grid interval is exactly
    # one Wavelength world-space engine-grid step.
    overlay.grid_scale = float(step)


def _blender_visuals(overlay):
    # Blender / No Engine is intentionally deterministic. Do not restore a
    # stale snapshot from a previous engine view, which could have the native
    # grid hidden. These are Blender's normal viewport-grid defaults.
    overlay.show_floor = True
    overlay.show_ortho_grid = True
    overlay.grid_scale = 1.0
    overlay.grid_subdivisions = 10


def update(settings, context):
    """Synchronize Blender's native grid visuals with the active profile."""
    from . import profiles

    engine_grid = settings.grid_mode == 'ENGINE' and settings.engine != 'blender'
    if _EXPERIMENTAL and engine_grid:
        context.scene.unit_settings.system='NONE'
    step = profiles.active_grid_step_meters(settings) if engine_grid else None

    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != 'VIEW_3D':
                continue
            overlay = area.spaces.active.overlay
            if engine_grid and step is not None and step > 0.0:
                _engine_visuals(overlay, step)
            else:
                _blender_visuals(overlay)
            area.tag_redraw()


def restore():
    # On add-on disable, leave every 3D view with a visible ordinary Blender
    # grid instead of retaining engine-specific scale.
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                try:
                    _blender_visuals(area.spaces.active.overlay)
                    area.tag_redraw()
                except ReferenceError:
                    pass


def register():
    pass


def unregister():
    restore()

# A non-invasive yellow snap indicator. Blender's native grid color is a global
# theme setting; changing it would affect unrelated files and other add-ons.
_snap_indicator_handle = None


def _draw_snap_indicator():
    try:
        import blf
        from . import profiles
        context = bpy.context
        scene = context.scene
        settings = getattr(scene, 'wavelength', None) if scene else None
        if settings is None:
            return
        if settings.engine == 'blender' or settings.grid_mode != 'ENGINE':
            label = 'GRID SNAP  |  Blender native'
        else:
            label = f'GRID SNAP  |  {settings.grid_step} engine units'
        font = 0
        blf.size(font, 15)
        blf.color(font, 1.0, 0.85, 0.10, 1.0)
        blf.position(font, 20, 46, 0)
        blf.draw(font, label)
    except (AttributeError, ReferenceError, RuntimeError):
        pass


_original_register = register
_original_unregister = unregister


def register():
    global _snap_indicator_handle
    if _snap_indicator_handle is None:
        _snap_indicator_handle = bpy.types.SpaceView3D.draw_handler_add(
            _draw_snap_indicator, (), 'WINDOW', 'POST_PIXEL')


def unregister():
    global _snap_indicator_handle
    if _snap_indicator_handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_snap_indicator_handle, 'WINDOW')
        _snap_indicator_handle = None
    restore()


from bpy.app.handlers import persistent
@persistent
def _sync_loaded_grid(_unused=None):
    scene=getattr(bpy.context,'scene',None)
    if scene and hasattr(scene,'wavelength'):update(scene.wavelength,bpy.context)

def _sync_grid_tick():
    try:
        scene=getattr(bpy.context,'scene',None)
        if scene and hasattr(scene,'wavelength'):
            settings=scene.wavelength
            if settings.grid_mode=='ENGINE' and settings.engine!='blender':
                from . import profiles
                step=profiles.active_grid_step_meters(settings)
                if _EXPERIMENTAL and scene.unit_settings.system!='NONE':scene.unit_settings.system='NONE'
                for screen in bpy.data.screens:
                    for area in screen.areas:
                        if area.type=='VIEW_3D':
                            overlay=area.spaces.active.overlay
                            if overlay.grid_subdivisions!=_NATIVE_SUBDIVISIONS or abs(overlay.grid_scale-step)>1e-7:
                                _engine_visuals(overlay,step);area.tag_redraw()
    except (AttributeError,ReferenceError,RuntimeError):pass
    return .25

_previous_register=register
_previous_unregister=unregister
def register():
    _previous_register()
    if _sync_loaded_grid not in bpy.app.handlers.load_post:bpy.app.handlers.load_post.append(_sync_loaded_grid)
    if not bpy.app.timers.is_registered(_sync_grid_tick):bpy.app.timers.register(_sync_grid_tick,first_interval=.25,persistent=True)
    _sync_loaded_grid()

def unregister():
    if _sync_loaded_grid in bpy.app.handlers.load_post:bpy.app.handlers.load_post.remove(_sync_loaded_grid)
    if bpy.app.timers.is_registered(_sync_grid_tick):bpy.app.timers.unregister(_sync_grid_tick)
    _previous_unregister()
