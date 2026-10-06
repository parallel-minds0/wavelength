"""wavelength Blender add-on. Core format modules import without Blender."""
bl_info={'name':'wavelength','author':'wavelength contributors','version': (0, 10, 25),'blender':(4,5,0),
         'location':'3D View > Sidebar > wavelength','description':'Quake and GoldSrc level authoring','category':'Import-Export'}

def register():
    from . import ui
    ui.register()

def unregister():
    from . import ui
    ui.unregister()
