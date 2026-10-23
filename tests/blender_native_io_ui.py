"""Verify that the native export action opens a file browser, not a dialog."""
import sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
bpy.context.preferences.use_preferences_save=False
bpy.context.workspace['wl_workspace']=False
bpy.context.scene.wavelength.engine='source2_cs2_windows'
def verify():
    try:
        browsers=[area for window in bpy.context.window_manager.windows for area in window.screen.areas if area.type=='FILE_BROWSER']
        assert browsers,'Export did not open the file browser'
        op=browsers[0].spaces.active.active_operator
        assert op.bl_idname=='WAVELENGTH_OT_export_map',op.bl_idname
        properties=op.properties
        assert properties.export_format=='VMAP' and properties.filepath.endswith('.vmap')
        assert {item.identifier for item in properties.bl_rna.properties['export_format'].enum_items}=={'MAP','VMF','VMAP','GLB','VMDL'}
        properties.export_format='GLB'
        assert properties.filepath.endswith('.glb')
        print('PASS NATIVE IO UI: direct file browser with functioning format selector',flush=True)
    except Exception:traceback.print_exc()
    # Close the modal file selector before shutting down the test instance.
    for window in list(bpy.context.window_manager.windows):
        for area in list(window.screen.areas):
            if area.type=='FILE_BROWSER':
                with bpy.context.temp_override(window=window,area=area):bpy.ops.file.cancel()
                break
    bpy.app.timers.register(lambda:bpy.ops.wm.quit_blender() and None,first_interval=1)
def start():
    assert bpy.ops.wavelength.export_map('INVOKE_DEFAULT')=={'RUNNING_MODAL'}
    bpy.app.timers.register(verify,first_interval=2)
bpy.app.timers.register(start,first_interval=2)
