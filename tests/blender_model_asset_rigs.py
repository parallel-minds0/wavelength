"""Independent model variants retain rig weights, NLA clips and curve controls."""
import sys,json,uuid
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import model_lifecycle as life
ctx=bpy.context;s=ctx.scene.wavelength;s.engine='source_hl2_windows';s.auto_prepare_assets=False
s.game_dir='C:/Program Files (x86)/Steam/steamapps/common/Half-Life 2/hl2_complete';s.unit_scale=.0254
for o in list(ctx.scene.objects):bpy.data.objects.remove(o,do_unlink=True)
bpy.ops.mesh.primitive_cube_add(size=1,location=(0,0,1));mesh=ctx.object
rigdata=bpy.data.armatures.new('Track Rig');rig=bpy.data.objects.new('Track Rig',rigdata);ctx.scene.collection.objects.link(rig)
for o in ctx.selected_objects:o.select_set(False)
rig.select_set(True);ctx.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
bone=rigdata.edit_bones.new('Bend');bone.head=(0,0,0);bone.tail=(0,0,2);bpy.ops.object.mode_set(mode='OBJECT')
group=mesh.vertex_groups.new(name='Bend');group.add(list(range(len(mesh.data.vertices))),1,'REPLACE')
modifier=mesh.modifiers.new('Rig','ARMATURE');modifier.object=rig
pose=rig.pose.bones['Bend'];pose.rotation_mode='XYZ'
pose.rotation_euler.y=0;pose.keyframe_insert('rotation_euler',frame=1)
pose.rotation_euler.y=.6;pose.keyframe_insert('rotation_euler',frame=5)
action=rig.animation_data.action;rig.animation_data.action=None
track=rig.animation_data.nla_tracks.new();track.strips.new('bend',1,action)
rig['wl_model_clips']=json.dumps([dict(name='bend',start=1,end=5,fps=24,loop=True,activity='')])
asset=life._adopt(ctx,[mesh,rig],'Animated Track','source1','synthetic',[])
owner=bpy.data.objects.new('Animated Placement',None);ctx.scene.collection.objects.link(owner)
owner['wl_role']='ENTITY';owner['wl_id']=uuid.uuid4().hex;owner['wl_unit_meters']=.0254
owner['wl_pairs']=json.dumps([['classname','prop_dynamic']]);ctx.scene.frame_set(1)
life.attach(ctx,asset,owner)
variant=life.make_unique(ctx,asset,owner);ctx.view_layer.update()
copy=next(o for o in variant.objects if o.type=='MESH');copy_rig=next(o for o in variant.objects if o.type=='ARMATURE')
assert copy.modifiers[0].object==copy_rig and copy_rig.data!=rig.data
assert copy.vertex_groups['Bend'] and copy_rig.animation_data.nla_tracks[0].strips[0].action!=action
assert variant.wavelength_model.clips[0].fps==24 and variant.wavelength_model.clips[0].loop
def evaluated(obj):return [obj.matrix_world@v.co for v in obj.evaluated_get(ctx.evaluated_depsgraph_get()).data.vertices]
first=evaluated(copy);ctx.scene.frame_set(5);last=evaluated(copy)
assert max((a-b).length for a,b in zip(first,last))>.1,'Variant lost skeletal animation'
ctx.scene.frame_set(1);before=evaluated(copy)
old_variant=variant;variant=life.detach(ctx,old_variant,owner);ctx.view_layer.update()
assert owner['wl_custom_model']==old_variant
copy=next(o for o in variant.objects if o.type=='MESH');copy_rig=next(o for o in variant.objects if o.type=='ARMATURE')
assert max((a-b).length for a,b in zip(before,evaluated(copy)))<1e-5
assert variant.wavelength_model.clips[0].name=='bend' and copy.modifiers[0].object==copy_rig
# Preparing a detached edited asset must retain edited clip definitions.
from wavelength.source.model_backend_source1 import Source1
s.compiler_dir='C:/Program Files (x86)/Steam/steamapps/common/Half-Life 2/bin'
variant.wavelength_model.clips[0].name='edited_bend';variant.wavelength_model.clips[0].start=2;variant.wavelength_model.clips[0].end=4
stage=root/'build/model-lifecycle/edited-clips';stage.mkdir(parents=True,exist_ok=True)
job=Source1().prepare(ctx,variant,stage)
assert job.definition==variant and variant.wavelength_model.clips[0].name=='edited_bend'
assert variant.wavelength_model.clips[0].start==2 and variant.wavelength_model.clips[0].end==4
assert not life.bindings(variant),'Private compile origin counted as a placement'
# Modelling controls are sources too; a unique bend must not edit another curve.
bpy.ops.mesh.primitive_cube_add(size=1);track_mesh=ctx.object
curve_data=bpy.data.curves.new('Track Bend','CURVE');curve_data.dimensions='3D'
spline=curve_data.splines.new('BEZIER');spline.bezier_points.add(1)
spline.bezier_points[0].co=(0,0,0);spline.bezier_points[1].co=(2,2,0)
curve=bpy.data.objects.new('Track Bend',curve_data);ctx.scene.collection.objects.link(curve)
mod=track_mesh.modifiers.new('90 degree bend','CURVE');mod.object=curve
mirror=track_mesh.modifiers.new('Native mirror','MIRROR');mirror.mirror_object=curve
nodes=bpy.data.node_groups.new('Native modelling group','GeometryNodeTree')
nodes.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry')
nodes.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
input_node=nodes.nodes.new('NodeGroupInput');output_node=nodes.nodes.new('NodeGroupOutput')
nodes.links.new(input_node.outputs['Geometry'],output_node.inputs['Geometry'])
info=nodes.nodes.new('GeometryNodeObjectInfo');info.inputs['Object'].default_value=curve
node_modifier=track_mesh.modifiers.new('Native Geometry Nodes','NODES');node_modifier.node_group=nodes
control_asset=life._adopt(ctx,[track_mesh,curve],'Curved Track','source1','synthetic',[])
clone_asset=life.make_unique(ctx,control_asset)
clone_mesh=next(o for o in clone_asset.objects if o.type=='MESH');clone_curve=next(o for o in clone_asset.objects if o.type=='CURVE')
assert clone_mesh.modifiers[0].object==clone_curve and clone_curve.data!=curve.data
assert clone_mesh.modifiers[1].mirror_object==clone_curve
assert clone_mesh.modifiers[2].node_group!=nodes
assert next(n for n in clone_mesh.modifiers[2].node_group.nodes if n.bl_idname=='GeometryNodeObjectInfo').inputs['Object'].default_value==clone_curve
clone_curve.data.splines[0].bezier_points[1].co.x=7
assert curve.data.splines[0].bezier_points[1].co.x==2
print('PASS independent armatures, vertex weights, NLA actions, clip metadata, animated detach and independent curve modifier controls',flush=True)
