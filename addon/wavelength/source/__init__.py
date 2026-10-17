"""wavelength Blender add-on. Core format modules import without Blender."""
bl_info={'name':'wavelength','author':'wavelength contributors','version': (0, 10, 30),'blender':(4,5,0),
         'location':'3D View > Sidebar > wavelength','description':'Quake and GoldSrc level authoring','category':'Import-Export'}

def register():
    import bpy
    from . import ui, diagnostics, diagnostics_ui
    try:
        from pathlib import Path
        config = bpy.utils.user_resource('CONFIG')
        if not config:
            raise OSError('Blender config directory is unavailable')
        diagnostics.start(Path(config) / 'wavelength/logs', bpy.app.version_string)
    except OSError as exc:
        print('Wavelength persistent logging unavailable:', exc)
    diagnostics_ui.register()
    try:
        ui.register()
    except Exception as exc:
        diagnostics.error('Add-on registration', exc)
        diagnostics_ui.unregister()
        diagnostics.stop()
        raise

def unregister():
    from . import ui, diagnostics, diagnostics_ui
    try:
        ui.unregister()
    except Exception as exc:
        diagnostics.error('Add-on unregistration', exc)
        raise
    finally:
        diagnostics_ui.unregister()
        diagnostics.stop()
