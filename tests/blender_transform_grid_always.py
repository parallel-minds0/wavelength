"""Compatibility entry point for native profile-grid scaling regression."""
import runpy
from pathlib import Path
runpy.run_path(str(Path(__file__).with_name("blender_native_scale.py")),run_name="__main__")
