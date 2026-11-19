"""Wavelength Blender add-on entry point."""
bl_info = {
    "name": "Wavelength",
    "author": "Wavelength contributors",
    "version": (0, 51, 0),
    "blender": (4, 5, 0),
    "location": "Wavelength Workspace; Scene and Object Properties",
    "description": "Quake and GoldSrc level authoring",
    "category": "Import-Export",
}

def register():
    from .source import register as source_register
    source_register()

def unregister():
    from .source import unregister as source_unregister
    source_unregister()


class glTF2ExportUserExtension:
    """glTF's supported extension point for wavelength inclusion checks."""
    def gather_tree_filter_tag_hook(self,tree,export_settings):
        from .source.regular_exports import filter_gltf_tree
        filter_gltf_tree(tree,export_settings)
