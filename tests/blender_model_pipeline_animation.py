exec(compile((__import__('pathlib').Path(__file__).parent/'blender_model_pipeline.py').read_text().split('# Extract an installed')[0],__file__,'exec'))
from wavelength.source import studio_animation
from mathutils import Matrix,Quaternion,Vector
source=next(p for p in (root/'build/custom-models/skeletal-animation/model_game').rglob('*.mdl') if any(c['name']=='bend' for c in studio_animation.read(p.read_bytes(),lambda name:p.with_name(Path(name).name).read_bytes())['clips']))
original=studio_animation.read(source.read_bytes(),lambda name:source.with_name(Path(name).name).read_bytes())
asset=model_io.import_asset(ctx,str(source));rig=next(o for o in asset.objects if o.type=='ARMATURE');mesh=next(o for o in asset.objects if o.type=='MESH')
assert mesh.modifiers[0].object==rig and mesh.vertex_groups
clip=original['clips'][0]
def expected(frame):
 result=[]
 for i,(pos,q) in enumerate(frame):
  local=Matrix.Translation(Vector(pos)*.0254)@Quaternion((q[3],*q[:3])).to_matrix().to_4x4()
  parent=original['bones'][i]['parent'];result.append(result[parent]@local if parent>=0 else local)
 return result
for frame in (1,5):
 ctx.scene.frame_set(frame);ctx.view_layer.update()
 for bone,matrix in zip(original['bones'],expected(clip['frames'][frame-1])):
  actual=rig.pose.bones[bone['name']].matrix
  assert max(abs(a-b) for rowa,rowb in zip(actual,matrix) for a,b in zip(rowa,rowb))<1e-4,(frame,bone['name'],actual,matrix)
ctx.scene.frame_set(1)
job=model_pipeline.get('source1').prepare(ctx,asset,folder/'animated-stage')
assert dict(json.loads(job.owner['wl_pairs']))['classname']=='prop_dynamic'
assert job.owner.get('wl_exclude') and len(job.definition.wavelength_model.clips)==1
for command in job.commands:
 result=subprocess.run(command,capture_output=True,text=True,errors='replace',timeout=90)
 (folder/'animated-compiler.log').write_text(result.stdout+result.stderr)
 assert result.returncode==0,result.stdout[-3000:]+result.stderr
path=dict(json.loads(job.owner['wl_pairs']))['model'];rebuilt=studio_animation.read((job.build.stage/path).read_bytes(),lambda name:(job.build.stage/path).with_name(Path(name).name).read_bytes())
assert rebuilt['clips'][0]['name']=='bend' and len(rebuilt['clips'][0]['frames'])==5
print('PASS weighted skeleton, imported keyframe poses, named NLA clip, dynamic StudioMDL recompile and excluded compile origin',flush=True)
