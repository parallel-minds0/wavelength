"""Wavelength Blender add-on entry point."""
bl_info = {
    "name": "Wavelength",
    "author": "Wavelength contributors",
    "version": (0, 10, 25),
    "blender": (4, 5, 0),
    "location": "3D View > Sidebar > Wavelength",
    "description": "Quake and GoldSrc level authoring",
    "category": "Import-Export",
}

def register():
    from .source import register as source_register
    source_register()

def unregister():
    from .source import unregister as source_unregister
    source_unregister()
