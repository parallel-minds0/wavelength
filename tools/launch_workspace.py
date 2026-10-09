"""Load this source tree into a temporary Blender session without installation."""
import sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'addon'))
import wavelength
wavelength.register()
def enter():
 from wavelength.source import workspace
 ws=workspace.ensure(bpy.context)
 if ws:bpy.context.window.workspace=ws
 bpy.context.scene.wavelength.engine='source_hl2_linux'
 return None
bpy.app.timers.register(enter,first_interval=.6)
