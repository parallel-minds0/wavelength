"""Blender-native viewport grid integration.

Wavelength never draws a custom grid. Engine profiles configure Blender's native
viewport grid for visuals only; profile/tool code remains authoritative for snap.
"""
import bpy

# Blender's native floor grid divides grid_scale by grid_subdivisions for the
# visible fine interval. Keep a conventional subdivision count and choose the
# scale so one visible fine interval equals one Wavelength engine-grid step.
_NATIVE_SUBDIVISIONS = 1


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
