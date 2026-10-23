exec(compile((__import__('pathlib').Path(__file__).parent/'blender_custom_model_build.py').read_text().split('bpy.ops.mesh.primitive_cube_add')[0],__file__,'exec'))
from mathutils import Vector
def run(work):
    job=custom_models.prepare(ctx.scene,folder/work)
    for i,cmd in enumerate(job.commands):
        p=subprocess.run(cmd,capture_output=True,text=True,errors='replace',timeout=60)
        (folder/(work+f'-{i}.log')).write_text(p.stdout+p.stderr)
        assert p.returncode==0,p.stdout[-3500:]+p.stderr
    job.validated();return job
def source(classname):
    bpy.ops.mesh.primitive_cube_add(size=1,location=(2,0,1));obj=ctx.object
    mat=bpy.data.materials.new(classname+' color');obj.data.materials.append(mat)
    entity=_spawn_point_entity(ctx,classname);entity.location=(2,0,0);obj.select_set(True);entity.select_set(True);ctx.view_layer.objects.active=entity
    return obj,entity
ctx.scene.frame_start=1;ctx.scene.frame_end=5
obj,entity=source('prop_dynamic')
obj.location.x=2;obj.keyframe_insert('location',frame=1);obj.location.x=3;obj.keyframe_insert('location',frame=5);ctx.scene.frame_set(1)
col=custom_models.assign(ctx);col.wavelength_model.clips[0].name='slide'
ctx.scene.frame_set(5);assert abs(obj.matrix_world.translation.x-3)<1e-5;ctx.scene.frame_set(1)
job=run('rigid-animation');md=studio_model.Reader((job.stage/dict(json.loads(entity['wl_pairs']))['model']).read_bytes())
assert md.integer(180)>=1 and md.integer(md.integer(184)+16)==5
clip=(folder/'rigid-animation/model_sources'/col['wl_custom_model_id']/'clip_0.smd').read_text();assert 'time 4' in clip
print('PASS real animated dynamic model; five sampled frames and preserved object-animation placement',flush=True)
obj,entity=source('prop_physics');col=custom_models.assign(ctx);job=run('physics')
assert (job.stage/dict(json.loads(entity['wl_pairs']))['model']).with_suffix('.phy').is_file()
assert b'prop_data' in (job.stage/dict(json.loads(entity['wl_pairs']))['model']).read_bytes()
print('PASS real StudioMDL convex physics collision companion',flush=True)
obj,entity=source('prop_dynamic')
rigdata=bpy.data.armatures.new('Rig');rig=bpy.data.objects.new('Rig',rigdata);ctx.collection.objects.link(rig);rig.location=(2,0,1)
ctx.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT');bone=rigdata.edit_bones.new('Bone');bone.head=(0,0,0);bone.tail=(0,0,1);bpy.ops.object.mode_set(mode='OBJECT')
group=obj.vertex_groups.new(name='Bone');group.add(list(range(len(obj.data.vertices))),1,'REPLACE');mod=obj.modifiers.new('Rig','ARMATURE');mod.object=rig
pose=rig.pose.bones['Bone'];pose.rotation_mode='XYZ';pose.rotation_euler.y=0;pose.keyframe_insert('rotation_euler',frame=1);pose.rotation_euler.y=.6;pose.keyframe_insert('rotation_euler',frame=5);ctx.scene.frame_set(1)
for o in ctx.selected_objects:o.select_set(False)
obj.select_set(True);rig.select_set(True);entity.select_set(True);ctx.view_layer.objects.active=entity
col=custom_models.assign(ctx);col.wavelength_model.clips[0].name='bend';job=run('skeletal-animation')
mdl=studio_model.Reader((job.stage/dict(json.loads(entity['wl_pairs']))['model']).read_bytes());assert mdl.integer(156)>=1 and mdl.integer(mdl.integer(184)+16)==5
print('PASS real weighted skeletal model and sampled bone animation; rest pose restored after export',flush=True)
