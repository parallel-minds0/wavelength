"""Native File menu IO is explicit and independent of workspace activation."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import native_ui,context_policy
bpy.context.preferences.use_preferences_save=False
bpy.context.workspace['wl_workspace']=False
class Menu:
    def __init__(self):self.layout=self;self.items=[]
    def operator(self,identifier,**kwargs):self.items.append((identifier,kwargs['text']))
for engine,extension in [('blender','.map'),('source_hl2_windows','.vmf'),('godot4','.glb'),('source2_cs2_windows','.vmdl')]:
    bpy.context.scene.wavelength.engine=engine
    menu=Menu();native_ui.draw_import(menu,bpy.context);native_ui.draw_export(menu,bpy.context)
    assert len(menu.items)==2 and all(text.startswith('wavelength IO (.') and text.endswith(')') for _,text in menu.items),menu.items
    assert menu.items[0][1]=='wavelength IO (.map, .vmf, .vmap)'
    assert menu.items[1]==('wavelength.export_map','wavelength IO (.map, .vmf, .vmap, .glb, .vmdl)')
    assert extension in menu.items[1][1],menu.items
    assert context_policy.operation_allowed(bpy.context,'wavelength.import_map')
    assert context_policy.operation_allowed(bpy.context,'wavelength.export_map')
    assert '.vmap' in menu.items[1][1]
print('PASS NATIVE IO: format labels and IO outside wavelength workspace',flush=True)

# File-browser format changes update both filename and filter without changing
# the scene's profile. Export a real GLB through the unified operator as well.
from wavelength.source import ui
root=Path(__file__).resolve().parents[1]/'build/native-io'
root.mkdir(exist_ok=True)
from types import SimpleNamespace
op=SimpleNamespace(filepath=str(root/'selector.map'))
for fmt,ext in [('VMF','.vmf'),('GLB','.glb'),('VMDL','.vmdl'),('MAP','.map')]:
    op.export_format=fmt
    ui.WL_OT_export.format_changed(op,bpy.context)
    assert op.filepath.endswith(ext) and op.filter_glob=='*'+ext
bpy.context.scene.wavelength.engine='blender'
assert bpy.ops.wavelength.export_map('EXEC_DEFAULT',export_format='GLB',filepath=str(root/'browser.glb'))=={'FINISHED'}
assert (root/'browser.glb').read_bytes()[:4]==b'glTF'
assert bpy.context.scene.wavelength.engine=='blender'
print('PASS FILE BROWSER IO: format selector and GLB output without profile mutation',flush=True)
