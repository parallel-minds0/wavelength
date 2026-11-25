"""Authored placements, live masks and portable PBR material composition."""
import json
from pathlib import Path
import sys
import bpy
from mathutils import Matrix

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'addon'))
import wavelength
from wavelength.source import environment_adopt as adopt,environment_layers as env,environment_materials as mats
wavelength.register();ctx=bpy.context;ctx.workspace['wl_workspace']=True
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete()
mesh=bpy.data.meshes.new('Terrain');mesh.from_pydata([(x,y,0) for y in range(-4,5) for x in range(-4,5)],[],[(y*9+x,y*9+x+1,(y+1)*9+x+1,(y+1)*9+x) for y in range(8) for x in range(8)])
terrain=bpy.data.objects.new('Terrain',mesh);ctx.collection.objects.link(terrain)
base=bpy.data.materials.new('Base');base.use_nodes=True;mesh.materials.append(base)
bpy.ops.mesh.primitive_cube_add();proto=ctx.object;proto.name='Prototype';proto.hide_set(True)
points=bpy.data.meshes.new('Existing points');points.from_pydata([(-3,0,0),(-1,0,0),(1,0,0),(3,0,0),(8,0,0)],[],[])
points.attributes.new('instance_scale','FLOAT_VECTOR','POINT').data.foreach_set('vector',[value for i in range(5) for value in [.5+i*.2]*3])
points.attributes.new('instance_rotation','FLOAT_VECTOR','POINT').data.foreach_set('vector',[0,0,.3]*5)
source=bpy.data.objects.new('Existing layout',points);ctx.collection.objects.link(source)
group=bpy.data.node_groups.new('Existing GN layout','GeometryNodeTree');info=group.nodes.new('GeometryNodeObjectInfo');info.inputs['Object'].default_value=proto
group.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry')
group.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
info.inputs['As Instance'].default_value=True
instance=group.nodes.new('GeometryNodeInstanceOnPoints')
group.links.new(group.nodes.new('NodeGroupInput').outputs['Geometry'],instance.inputs['Points'])
group.links.new(info.outputs['Geometry'],instance.inputs['Instance'])
for name,target in (('instance_rotation','Rotation'),('instance_scale','Scale')):
    field=group.nodes.new('GeometryNodeInputNamedAttribute');field.data_type='FLOAT_VECTOR';field.inputs['Name'].default_value=name
    group.links.new(field.outputs['Attribute'],instance.inputs[target])
group.links.new(instance.outputs['Instances'],group.nodes.new('NodeGroupOutput').inputs['Geometry'])
source.modifiers.new('Instances','NODES').node_group=group
before=[tuple(v.co) for v in points.vertices];ctx.view_layer.update()
layer=adopt.adopt(ctx,terrain,source)
assert len(layer.placements.data.vertices)==4 and len(layer.adopt_remainder.data.vertices)==1
for name in ('instance_rotation','instance_scale'):
    assert tuple(layer.adopt_remainder.data.attributes[name].data[0].vector)==tuple(source.data.attributes[name].data[4].vector)
ctx.view_layer.update()
assert len([i for i in ctx.evaluated_depsgraph_get().object_instances if i.is_instance])==1
assert before==[tuple(v.co) for v in points.vertices]
records=env.records(ctx,terrain,layer);assert len(records)==4
address=records[0]['id'];pose=Matrix(records[0]['matrix']);pose.translation.y+=1
env.set_override(layer,address,proto,pose)
clearing=env.add_layer(terrain,'EXCLUSION','Clearing');env.stamp(terrain,clearing,(-1,0,0),.5,1)
ctx.view_layer.update();assert len(env.records(ctx,terrain,layer))==3
for v in mesh.vertices:v.co.z+=2
mesh.update();ctx.view_layer.update()
resolved=env.records(ctx,terrain,layer)
assert next(r for r in resolved if r['id']==address)['matrix']==[list(r) for r in pose]
assert all(abs(Matrix(r['matrix']).translation.z-2)<1e-6 for r in resolved if r['id']!=address)
paint=env.add_layer(terrain,'MATERIAL','PBR paint');paint.material=bpy.data.materials.new('Paint');paint.material.use_nodes=True
paint.material.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.9,.1,.1,1)
env.stamp(terrain,paint,(0,0,2),2,1)
original_nodes=len(base.node_tree.nodes);mats.refresh(terrain)
assert len(base.node_tree.nodes)==original_nodes and terrain.data.materials[0]!=base
ctx.view_layer.update();snapshot=env.Surface(ctx,terrain)
assert snapshot.mesh.attributes.get('wl_env_mask_'+paint.uid) is not None
snapshot.close()
old=layer.overrides;path=ROOT/'build/privateer-complete/adoption-regression.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(path));bpy.ops.wm.open_mainfile(filepath=str(path))
terrain=bpy.data.objects['Terrain'];layer=terrain.wavelength_environment_layers[0]
assert layer.overrides==old
assert {r['id']:r for r in env.records(ctx,terrain,layer)}=={r['id']:r for r in resolved}
assert terrain.get(env.OVERRIDES)
print('PASS ADOPTION: untouched original and remainder, exact overrides, sculpt following, live shader masks and save/reopen',flush=True)
wavelength.unregister()
