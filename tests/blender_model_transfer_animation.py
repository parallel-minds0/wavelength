"""Cross-target skeletal clips preserve source actions and explicit omissions."""
import sys,json,struct,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import model_lifecycle as life,model_transfer as transfer,model_bundle
ctx=bpy.context;s=ctx.scene.wavelength;s.engine='source_hl2_windows';s.auto_prepare_assets=False
s.game_dir='C:/Program Files (x86)/Steam/steamapps/common/Half-Life 2/hl2_complete'
s.compiler_dir='C:/Program Files (x86)/Steam/steamapps/common/Half-Life 2/bin';s.unit_scale=.0254
folder=root/'build/model-transfer-animation';folder.mkdir(parents=True,exist_ok=True);s.project_dir=str(folder)
for o in list(ctx.scene.objects):bpy.data.objects.remove(o,do_unlink=True)
bpy.ops.mesh.primitive_cube_add(size=1);mesh=ctx.object
rig=bpy.data.objects.new('Rig',bpy.data.armatures.new('Rig'));ctx.scene.collection.objects.link(rig)
for o in ctx.selected_objects:o.select_set(False)
rig.select_set(True);ctx.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
bone=rig.data.edit_bones.new('Bend');bone.head=(0,0,0);bone.tail=(0,0,1);bpy.ops.object.mode_set(mode='OBJECT')
weights=mesh.vertex_groups.new(name='Bend');weights.add(list(range(8)),1,'REPLACE')
mesh.modifiers.new('Rig','ARMATURE').object=rig
pose=rig.pose.bones['Bend'];pose.rotation_mode='XYZ';pose.rotation_euler.y=0;pose.keyframe_insert('rotation_euler',frame=1)
pose.rotation_euler.y=.6;pose.keyframe_insert('rotation_euler',frame=5)
action=rig.animation_data.action;rig.animation_data.action=None
track=rig.animation_data.nla_tracks.new();track.name='bend';track.strips.new('bend',1,action)
asset=life._adopt(ctx,[mesh,rig],'Animated asset','source1','synthetic',[])
clip=asset.wavelength_model.clips.add();clip.name='bend';clip.start=1;clip.end=5;clip.fps=24;clip.loop=True
ctx.scene.render.fps=30;ctx.scene.frame_start=1;ctx.scene.frame_end=5;ctx.scene.frame_set(1)
job=transfer.prepare(ctx,asset,folder/'godot-job','godot4',folder/'godot',publish=False,package=True)
try:
 output=job.finish();payload=Path(output).read_bytes();size,kind=struct.unpack_from('<II',payload,12);data=json.loads(payload[20:20+size])
 assert len(data.get('skins',[]))==1 and data.get('animations'),data.keys()
 animation=next(a for a in data['animations'] if a['name']=='bend')
 durations=[data['accessors'][sampler['input']]['max'][0] for sampler in animation['samplers']]
 assert abs(max(durations)-4/24)<.002,durations
finally:job.close()
assert rig.animation_data.action is None and rig.animation_data.nla_tracks[0].name=='bend'
assert rig.animation_data.nla_tracks[0].strips[0].scale==1
loaded=model_bundle.import_asset(ctx,folder/'godot/asset.wlmodel')
copyrig=next(o for o in life.sources(loaded) if o.type=='ARMATURE')
assert copyrig.animation_data.nla_tracks[0].strips[0].scale==1,'Package captured target-retimed tracks instead of authoring clips'
assert loaded.wavelength_model.clips[0].loop and loaded.wavelength_model.clips[0].fps==24
print('PASS Godot skeletal GLB, named clip timing/FPS, source and packaged NLA left unchanged',flush=True)
for target in ('source2_cs2_windows',):
 try:transfer.prepare(ctx,asset,folder/'strict',target,folder/'strict-output',publish=False)
 except ValueError as exc:assert 'animated' in str(exc)
 else:raise AssertionError('Unsupported animation silently dropped')
job=transfer.prepare(ctx,asset,folder/'source-job','source_hl2_windows',folder/'source',publish=False,package=True)
try:
 for command in job.commands:
  result=subprocess.run(command,capture_output=True,text=True,errors='replace',timeout=120)
  (folder/'compiler.log').write_text(result.stdout+result.stderr);assert result.returncode==0,result.stdout[-2000:]
 assert Path(job.finish()).is_file()
finally:job.close()
print('PASS native animated Source1 rebuild and strict unsupported CS2 animation guard',flush=True)
# A selected external collision mesh becomes an owned dependency, not a live
# link back into the level. It must never enter the render triangles.
bpy.ops.mesh.primitive_cube_add(size=.8);collision=ctx.object
asset.wavelength_model.collision_mode='OBJECT';asset.wavelength_model.collision=collision
job=transfer.prepare(ctx,asset,folder/'collision-job','source_hl2_windows',folder/'collision',publish=False)
user_object=bpy.data.objects.new('Created while compiling',None);ctx.scene.collection.objects.link(user_object)
try:
 copied=job.snapshot.asset.wavelength_model.collision
 assert copied!=collision and copied.data!=collision.data and copied.get('wl_model_collision_only')
 for command in job.commands:
  result=subprocess.run(command,capture_output=True,text=True,errors='replace',timeout=120)
  assert result.returncode==0,result.stdout[-2000:]
 output=job.finish();assert Path(output).with_suffix('.phy').is_file()
finally:job.close()
assert user_object.name in bpy.data.objects and collision.name in ctx.scene.objects
assert asset.wavelength_model.collision==collision
print('PASS copied external collision compilation and modal cleanup preserves newly created user objects',flush=True)
job=transfer.prepare(ctx,asset,folder/'cached-job','source_hl2_windows',folder/'cached',publish=False)
try:
 assert not job.commands,'Unchanged model did not use its validated compiler cache'
 assert Path(job.finish()).is_file()
finally:job.close()
asset.wavelength_model.collision=mesh
job=transfer.prepare(ctx,asset,folder/'shared-job','source_gmod_windows',folder/'shared',publish=False,game=s.game_dir,compiler=s.compiler_dir,model_name='custom-track')
try:
 copied=job.snapshot.asset.wavelength_model.collision
 assert not copied.get('wl_model_collision_only')
 for command in job.commands:
  result=subprocess.run(command,capture_output=True,text=True,errors='replace',timeout=120)
  assert result.returncode==0,result.stdout[-2000:]
 output=job.finish();assert Path(output).name=='custom-track.mdl'
 assert Path(output).with_suffix('.phy').is_file()
 from wavelength.source import studio_model,source_assets
 class Output:
  def read(self,name):return (folder/'shared'/name).read_bytes()
 data=studio_model.load(Output(),job.primary)
 assert data['faces'],'Using the render mesh as collision removed its render triangles'
 assert job.report['target_profile']=='source_gmod_windows' and s.engine=='source_hl2_windows'
finally:job.close()
print('PASS validated cache reuse, Source1 profile conversion and shared render/collision mesh',flush=True)
