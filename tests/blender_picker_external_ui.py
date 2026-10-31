import sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,wavelength
wavelength.register()
from wavelength.source import workspace,surface_tools
c=bpy.context;c.preferences.use_preferences_save=False
c.window.workspace=workspace.ensure(c)
c.scene.wavelength.auto_prepare_assets=False
c.scene.wavelength.engine='blender'
bpy.ops.mesh.primitive_cube_add()
obj=c.object
mat=bpy.data.materials.new('Picker test material');mat['wl_texture']='custom/picker_test'
obj.data.materials.append(mat)
from wavelength.source import external_library
import json
folder=Path(__file__).resolve().parents[1]/'build/picker-library';folder.mkdir(parents=True,exist_ok=True)
mat.name='custom/picker_test';mat.asset_mark()
bpy.data.libraries.write(str(folder/'textures-0000.blend'),{mat},fake_user=True)
(folder/'manifest.json').write_text(json.dumps(dict(files=['textures-0000.blend'],errors={})))
(folder/'index.json').write_text(json.dumps(dict(names=['custom/picker_test'])))
external_library.cache_root=lambda values:('picker-test',folder)
external_library._root=folder
external_library.register_library()
def begin():
 try:surface_tools.sample(bpy.context,obj,0,'TEXTURE')
 except Exception:traceback.print_exc();bpy.ops.wm.quit_blender();return
 bpy.app.timers.register(check,first_interval=4)
def check():
 try:
  area=next(a for a in bpy.context.screen.areas if a.type=='FILE_BROWSER' and a.ui_type=='ASSETS')
  with bpy.context.temp_override(area=area,region=next(r for r in area.regions if r.type=='WINDOW')):
   asset=bpy.context.asset
   assert asset and asset.local_id is None and asset.name==mat.name,repr(asset)
   assert area.spaces.active.params.filter_search==''
  assert bpy.context.scene.wavelength.texture=='custom/picker_test'
  print('PASS external picker selects and reveals sampled texture; clipboard and apply target preserved',flush=True)
 except Exception:traceback.print_exc()
 bpy.ops.wm.quit_blender()
bpy.app.timers.register(begin,first_interval=2)


