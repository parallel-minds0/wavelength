"""Real CS2 Asset Browser controls with a prebuilt material-library shard."""
import sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import external_library,mesh_assets,context_policy
bpy.context.preferences.use_preferences_save=False
root=Path(__file__).resolve().parents[1]/'build'
def verify():
    try:
        areas=[area for area in bpy.context.screen.areas if area.type=='FILE_BROWSER' and area.ui_type=='ASSETS']
        assert areas and bpy.context.scene.wavelength.asset_browser_section=='TEXTURES'
        assert mesh_assets.WL_OT_source2_library.poll(bpy.context)
        assert any(m.get('wl_source2_material') for m in bpy.data.materials)
        bpy.ops.screen.screenshot(filepath=str(root/'source2-material-browser.png'))
        print('PASS SOURCE2 UI: CS2 materials browser and preparation controls',flush=True)
    except Exception:traceback.print_exc()
    bpy.ops.wm.quit_blender()
def start():
    s=bpy.context.scene.wavelength;s.engine='source2_cs2_windows'
    bpy.context.workspace['wl_workspace']=True;bpy.context.workspace['wl_layout_ready']=True
    key,_=external_library.cache_root(external_library.snapshot(s))
    external_library._key=key;external_library._root=root/'source2-library';external_library._completed.add(key)
    external_library._display_name='CS2 Materials';external_library.register_library()
    from wavelength.source import textures
    textures.material(s,'anubis/mudbrick02')
    assert bpy.ops.wavelength.entity_browser(section='TEXTURES')=={'FINISHED'}
    bpy.app.timers.register(verify,first_interval=3)
bpy.app.timers.register(start,first_interval=2)
