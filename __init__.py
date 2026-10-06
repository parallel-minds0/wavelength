"""Wavelength Blender add-on package entry point.

The installable repository is self-contained. Implementation lives in source/.
"""
from .source import bl_info

def register():
    from .source import register as _register
    _register()

def unregister():
    from .source import unregister as _unregister
    _unregister()
