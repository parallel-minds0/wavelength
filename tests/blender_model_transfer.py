"""Real native model build, owned edited textures and portable target handoffs."""
import sys,json,subprocess,struct,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import model_lifecycle as life,model_io,model_transfer as transfer,model_bundle,source_assets,studio_model
ctx=bpy.context;s=ctx.scene.wavelength;s.engine='source_hl2_windows';s.auto_prepare_assets=False
s.game_dir='C:/Program Files (x86)/Steam/steamapps/common/Half-Life 2/hl2_complete'
s.compiler_dir='C:/Program Files (x86)/Steam/steamapps/common/Half-Life 2/bin';s.unit_scale=.0254
folder=root/'build/model-transfer';folder.mkdir(parents=True,exist_ok=True);s.project_dir=str(folder)
for obj in list(ctx.scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
from wavelength.source.model_backend_source1 import Source1
result=Source1().import_reference(ctx,'models/props_c17/oildrum001.mdl')
asset=life._adopt(ctx,result.objects,'Editable Barrel','source1','mounted',result.warnings)
mesh=next(o for o in life.sources(asset) if o.type=='MESH');material=mesh.data.materials[0]
assert material['wl_model_material_editable'] and material['wl_model_source_files']
shader=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
image=shader.inputs['Base Color'].links[0].from_node.image
assert max(image.size)>=512,'Editable textures should use the original resolution'
# Distinct color edits must survive compilation, independent of native caches.
image.pixels[:]=[.75,.1,.2,1.]*(image.size[0]*image.size[1]);image.update()
life.select_sources(ctx,asset);selected=set(ctx.selected_objects);active=ctx.object
# A configured duplicate hides the owning template in the target enum.
from types import SimpleNamespace
from unittest.mock import patch
from wavelength.source import profile_ui,profiles
configured='c6889855-5780-404e-a6d2-ccf96b9382d1'
with patch.object(profile_ui, 'items', return_value=[
    (configured, profiles.get(s.engine)['label'], '', 1000),
    ('godot4', profiles.get('godot4')['label'], '', 1),
]):
    dialog=SimpleNamespace(source_name='',properties=SimpleNamespace(is_property_set=lambda key:False))
    dialog_context=SimpleNamespace(scene=ctx.scene,window_manager=SimpleNamespace(
        invoke_props_dialog=lambda operator, **kwargs: {'RUNNING_MODAL'}))
    with patch.object(model_io, 'active_asset', return_value=asset):
        assert model_io.WL_OT_convert_model_asset.invoke(dialog,dialog_context,None)=={'RUNNING_MODAL'}
    assert dialog.target_profile==configured
    assert asset['wl_model_profile']==s.engine
    asset['wl_model_publish_settings']=json.dumps({
        'model_name':'curved_track','target_profile':'removed-profile','output_directory':str(folder/'remembered')})
    with patch.object(model_io,'active_asset',return_value=asset):
        assert model_io.WL_OT_convert_model_asset.invoke(dialog,dialog_context,None)=={'RUNNING_MODAL'}
    assert dialog.model_name=='curved_track'
    assert dialog.target_profile==configured
    assert dialog.output_directory==str(folder/'remembered')
    asset.pop('wl_model_publish_settings')

# The native compiler origin is temporary and can inherit editor render
# suppression. Its checkbox must never stand in for the editable sources.
from wavelength.source import custom_models
prepare_native=custom_models.prepare
def prepare_with_hidden_origin(scene,work,entities=None,**kwargs):
    owner,=entities
    assert owner['wl_model_private_origin'] and owner['wl_exclude']
    owner.hide_render=True
    return prepare_native(scene,work,entities=entities,**kwargs)

original_vertices=[tuple(v.co) for v in mesh.data.vertices];original_matrix=mesh.matrix_world.copy()
counts={k:len(getattr(bpy.data,k)) for k in transfer.KINDS}
def run(job,log):
 for command in job.commands:
  result=subprocess.run(command,capture_output=True,text=True,errors='replace',timeout=120)
  (folder/log).write_text(result.stdout+result.stderr)
  assert result.returncode==0,result.stdout[-3000:]+result.stderr[-500:]
 return job.finish()
with patch.object(custom_models,'prepare',side_effect=prepare_with_hidden_origin):
 job=transfer.prepare(ctx,asset,folder/'source-job',s.engine,folder/'source-output',publish=False,package=True)
try:
 output=run(job,'source.log');assert Path(output).is_file()
 assert asset['wl_model_id']==job.snapshot.asset['wl_model_id']
 textures=[(name,data) for name,data in job.files.items() if name.endswith('_color.vtf')]
 assert textures
 decoded=[source_assets.decode_vtf(data,max_dimension=None) for name,data in textures]
 assert any(abs(pixels[0]-191)<3 and abs(pixels[1]-26)<3 for _,_,w,h,pixels in decoded),[(w,h,p[:4]) for _,_,w,h,p in decoded]
finally:job.close()
assert s.engine=='source_hl2_windows' and ctx.object==active and set(ctx.selected_objects)==selected
assert [tuple(v.co) for v in mesh.data.vertices]==original_vertices and mesh.matrix_world==original_matrix
assert all(len(getattr(bpy.data,k))==v for k,v in counts.items()),'Build leaked temporary authoring datablocks'
print('PASS independent native build, edited full-resolution VTF, source transforms/profile/selection preserved, snapshot cleanup',flush=True)
package=folder/'source-output/asset.wlmodel'
loaded=model_bundle.import_asset(ctx,package)
assert loaded['wl_model_id']!=asset['wl_model_id']
copy=next(o for o in life.sources(loaded) if o.type=='MESH')
assert copy.data!=mesh.data and not copy.get('wl_custom_model_owner')
loaded['wl_model_game']='missing-original-game'
job=transfer.prepare(ctx,loaded,folder/'godot-job','godot4',folder/'godot-output',publish=False,package=True,allow_lossy=True)
try:
 output=run(job,'godot.log');payload=Path(output).read_bytes()
 size,kind=struct.unpack_from('<II',payload,12);gltf=json.loads(payload[20:20+size])
 assert gltf['meshes'] and gltf.get('images') and gltf.get('materials')
 print('PASS source-free portable package reload and Godot GLB with embedded edited textures',flush=True)
finally:job.close()
# Package-only export must retain source ownership independently of a compiler.
transfer.export_package(ctx,loaded,folder/'standalone.wlmodel')
assert (folder/'standalone.wlmodel').is_file()
last=(folder/'source-output/conversion-report.json').read_bytes()
try:transfer.prepare(ctx,asset,folder/'unsupported','civ5',folder/'source-output',publish=False)
except ValueError as exc:assert 'not implemented' in str(exc)
else:raise AssertionError('Unsupported model conversion was silently accepted')
assert (folder/'source-output/conversion-report.json').read_bytes()==last
# Inject a mid-commit failure: restore both prior files across target roots.
one=folder/'transaction-a';two=folder/'transaction-b';one.mkdir(exist_ok=True);two.mkdir(exist_ok=True)
(one/'old').write_bytes(b'working');(two/'block').mkdir(exist_ok=True)
try:transfer._commit_many([(one,{'old':b'new'}),(two,{'block':b'impossible'})])
except OSError:pass
else:raise AssertionError('Invalid commit should fail')
assert (one/'old').read_bytes()==b'working'
print('PASS standalone package, unsupported-route stub and last-working multi-root rollback',flush=True)
# CS2 native static resource compilation is exercised only when requested.
if '--cs2' in sys.argv:
 job=transfer.prepare(ctx,asset,folder/'cs2-job','source2_cs2_windows',folder/'cs2-output',publish=False,package=True,allow_lossy=True)
 try:
  output=run(job,'cs2.log');assert Path(output).is_file()
  assert any(n.endswith('.vmdl_c') for n in job.files)
  assert any(n.endswith('.vmat_c') for n in job.files)
  print('PASS native CS2 ModelDoc, materials, textures and compiled resources',flush=True)
 finally:job.close()
