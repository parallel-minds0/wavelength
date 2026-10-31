"""Materialize engine-decoded skeletons as ordinary Blender bones/actions."""
import json
import bpy
from mathutils import Matrix,Vector,Quaternion

def import_skeleton(context,mesh_obj,data,weights,unit):
    bones=data['bones']
    if not bones:return None,[]
    if len(weights)!=len(mesh_obj.data.vertices):raise ValueError('Bone weights do not match editable mesh vertices')
    rigdata=bpy.data.armatures.new(mesh_obj.name+' Skeleton');rig=bpy.data.objects.new(mesh_obj.name+' Skeleton',rigdata)
    context.collection.objects.link(rig);rig.location=mesh_obj.location.copy()
    for o in context.selected_objects:o.select_set(False)
    rig.select_set(True);context.view_layer.objects.active=rig
    bpy.ops.object.mode_set(mode='EDIT');rest=[]
    def transform(pos,quat):return Matrix.Translation(Vector(pos)*unit)@Quaternion((quat[3],*quat[:3])).normalized().to_matrix().to_4x4()
    for bone in bones:
        local=transform(bone['pos'],bone['quat']);matrix=rest[bone['parent']]@local if bone['parent']>=0 else local;rest.append(matrix)
        edit=rigdata.edit_bones.new(bone['name'])
        edit.head=matrix.translation
        edit.tail=edit.head+matrix.to_3x3().col[1]*max(unit,unit*4)
        edit.align_roll(matrix.to_3x3().col[2])
        if bone['parent']>=0:edit.parent=rigdata.edit_bones[bones[bone['parent']]['name']]
    bpy.ops.object.mode_set(mode='OBJECT')
    groups=[mesh_obj.vertex_groups.new(name=b['name']) for b in bones]
    for vi,influences in enumerate(weights):
        for bi,weight in influences:
            if bi>=len(groups) or weight<0:raise ValueError('Invalid vertex bone weight')
            if weight:groups[bi].add([vi],weight,'REPLACE')
    modifier=mesh_obj.modifiers.new('Imported Skeleton','ARMATURE');modifier.object=rig
    rig.animation_data_create();clips=[];cursor=1
    for clip in data['clips']:
        action=bpy.data.actions.new(mesh_obj.name+' · '+clip['name']);rig.animation_data.action=action
        for fi,frame in enumerate(clip['frames'],1):
            global_pose=[]
            for bi,(pos,quat) in enumerate(frame):
                parent=bones[bi]['parent'];matrix=transform(pos,quat)
                if parent>=0:matrix=global_pose[parent]@matrix
                global_pose.append(matrix)
                # Convert absolute engine bone poses to Blender's rest-relative basis.
                local=rest[bi].inverted()@matrix if parent<0 else rest[bi].inverted()@rest[parent]@global_pose[parent].inverted()@matrix
                pose=rig.pose.bones[bones[bi]['name']];pose.rotation_mode='QUATERNION';pose.matrix_basis=local
                pose.keyframe_insert('location',frame=fi);pose.keyframe_insert('rotation_quaternion',frame=fi)
        rig.animation_data.action=None
        track=rig.animation_data.nla_tracks.new();track.name=clip['name'];strip=track.strips.new(clip['name'],cursor,action)
        strip.extrapolation='NOTHING';strip.blend_type='REPLACE'
        count=len(clip['frames']);clips.append(dict(name=clip['name'],start=cursor,end=cursor+count-1,fps=clip['fps'],loop=clip.get('loop',False),activity=clip.get('activity','')))
        cursor+=max(2,count+1)
    for pose in rig.pose.bones:pose.matrix_basis=Matrix.Identity(4)
    rig['wl_model_clips']=json.dumps(clips)
    context.scene.frame_set(context.scene.frame_current)
    return rig,clips
