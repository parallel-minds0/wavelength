"""Native grid state bridge. Python never submits grid geometry or GPU shaders.

The patched Blender renderer owns plane intersection, coverage, native depth and
compositing. This module only supplies per-viewport settings and restores them.
"""
import bpy
from . import profiles

_handles = []
_keymaps = []
_native = {}
_error = None
_FIELDS = ('show_floor', 'show_ortho_grid', 'wavelength_grid_enabled',
           'wavelength_grid_spacing', 'wavelength_grid_subdivisions')


def engine_enabled(settings):
    return settings is not None and settings.engine != 'blender' and settings.grid_mode == 'ENGINE'


def native_available(space):
    return all(hasattr(space.overlay, name) for name in _FIELDS)


def _assign(overlay, name, value):
    if getattr(overlay, name) != value:
        setattr(overlay, name, value)


def sync_native():
    from .workspace import active
    global _error
    owned = set()
    unavailable = False
    for window in bpy.context.window_manager.windows:
        with bpy.context.temp_override(window=window):
            if not active(bpy.context, 'grid'):
                continue
            settings = getattr(window.scene, 'wavelength', None)
            if settings is None:
                continue
            spacing, subdivisions = profiles.display_grid(settings)
            for area in window.screen.areas:
                if area.type != 'VIEW_3D':
                    continue
                space = area.spaces.active
                if not native_available(space):
                    unavailable = True
                    continue
                key = space.as_pointer()
                owned.add(key)
                if key not in _native:
                    _native[key] = (space, tuple(getattr(space.overlay, name) for name in _FIELDS))
                # Native axis flags and theme colors are never overridden.
                for name, value in zip(_FIELDS, (True, True, True, spacing, subdivisions)):
                    _assign(space.overlay, name, value)
    for key in list(_native):
        if key not in owned:
            space, values = _native.pop(key)
            try:
                for name, value in zip(_FIELDS, values):
                    _assign(space.overlay, name, value)
            except ReferenceError:
                pass
    _error = 'Native grid unavailable: close Blender and repair its native patch with the wavelength installer' if unavailable else None
    return .1


@bpy.app.handlers.persistent
def restore_native(*_):
    for space, values in list(_native.values()):
        try:
            for name, value in zip(_FIELDS, values):
                _assign(space.overlay, name, value)
        except ReferenceError:
            pass
    _native.clear()


def update(settings, context):
    sync_native()
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


def _draw_label():
    import blf
    from .workspace import active
    if not active(bpy.context, 'grid'):
        return
    settings = getattr(bpy.context.scene, 'wavelength', None)
    if settings is None or not bpy.context.space_data.overlay.show_overlays:
        return
    spacing, subdivisions = profiles.display_grid(settings)
    units = f'{settings.grid_step} engine units' if engine_enabled(settings) else f'{spacing:g} m'
    label = _error or f'NATIVE GRID  |  {units}  |  {subdivisions} subdivisions'
    blf.size(0, 15)
    blf.color(0, 1.0, 0.85, 0.10, 1.0)
    blf.position(0, 20, 46, 0)
    blf.draw(0, label)


def register():
    if not bpy.app.timers.is_registered(sync_native):
        bpy.app.timers.register(sync_native, persistent=True)
    for handlers in (bpy.app.handlers.save_pre, bpy.app.handlers.load_pre):
        if restore_native not in handlers:
            handlers.append(restore_native)
    config = bpy.context.window_manager.keyconfigs.addon
    if config:
        keymap = config.keymaps.new(name='3D View', space_type='VIEW_3D')
        for key, direction in (('LEFT_BRACKET', -1), ('RIGHT_BRACKET', 1)):
            item = keymap.keymap_items.new('wavelength.grid_step', key, 'PRESS')
            item.properties.direction = direction
            _keymaps.append((keymap, item))
    if not _handles:
        # Text only. No POST_VIEW handler, GPU shader, batch, or depth override.
        _handles.append(bpy.types.SpaceView3D.draw_handler_add(_draw_label, (), 'WINDOW', 'POST_PIXEL'))


def unregister():
    if bpy.app.timers.is_registered(sync_native):
        bpy.app.timers.unregister(sync_native)
    for handlers in (bpy.app.handlers.save_pre, bpy.app.handlers.load_pre):
        if restore_native in handlers:
            handlers.remove(restore_native)
    restore_native()
    for keymap, item in _keymaps:
        keymap.keymap_items.remove(item)
    _keymaps.clear()
    for handle in _handles:
        bpy.types.SpaceView3D.draw_handler_remove(handle, 'WINDOW')
    _handles.clear()
