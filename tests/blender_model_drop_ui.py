"""Exercise the native drop bridge and async generic job without game writes."""
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import model_io,model_pipeline
ctx=bpy.context;s=ctx.scene.wavelength;s.engine='source_hl2_windows';s.auto_prepare_assets=False
s.project_dir=str(root/'build/model-drop-ui');s.asset_browser_section='MODELS'
asset=bpy.data.collections.new('Editable Asset');ctx.scene.collection.children.link(asset)
asset['wl_model_backend']='fixture';asset['wl_model_profile']=s.engine
bpy.ops.mesh.primitive_cube_add();obj=ctx.object;asset.objects.link(obj);obj['wl_model_asset']=asset
obj['wl_role']='MODEL_SOURCE';obj['wl_exclude']=True
class Job:
 commands=[]
 def finish(self):asset['finished']=True;return 'models/test.mdl'
class Backend:
 id='fixture';extensions={'.fixture'}
 def supports(self,engine):return True
 def prepare(self,context,asset,work):return Job()
model_pipeline.register(Backend())
area=next(a for a in ctx.screen.areas if a.type=='VIEW_3D')
stage=0

def test():
 global stage
 try:
  if stage==0:
   with ctx.temp_override(area=area):assert model_io.WL_FH_model_asset.poll_drop(ctx)
   area.type='FILE_BROWSER';area.ui_type='ASSETS';stage=1;return .5
  if stage==1:
   region=next(r for r in area.regions if r.type=='WINDOW')
   with ctx.temp_override(area=area,region=region):
    assert model_io.WL_OT_publish_model_drop.poll(ctx)
    assert bpy.ops.file.publish_model_asset(source_name=obj.name)=={'FINISHED'}
   stage=2;return .5
  assert asset.get('finished') and asset['wl_model_status']=='Built: models/test.mdl'
  assert not any(o.get('wl_role')=='ENTITY' for o in ctx.scene.objects)
  print('PASS native object-ID publishing bridge, Models-only context, async job, no prop placement',flush=True)
 except Exception:
  import traceback;traceback.print_exc();print('FAIL model drop bridge',flush=True)
 bpy.ops.wm.quit_blender()
bpy.app.timers.register(test,first_interval=1)
