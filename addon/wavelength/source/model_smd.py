"""Evaluate editable Blender sources into reference SMD and scene-frame clips."""
import math
import bpy,bmesh
from mathutils import Matrix,Vector
from .model_formats import quote


def number(v):
    if not math.isfinite(v):raise ValueError('Model contains non-finite coordinates')
    return f'{v:.8f}'


def export(definition,scene,material_names):
    settings=definition.wavelength_model;root=settings.origin
    if root is None:raise ValueError('Custom model origin entity is missing')
    objects=[o for o in definition.objects if o.type in {'MESH','ARMATURE'} and o.name in scene.objects]
    meshes=[o for o in objects if o.type=='MESH' and o!=settings.collision]
    rigs=[o for o in objects if o.type=='ARMATURE']
    if not meshes:raise ValueError('Custom model has no render meshes')
    if len(rigs)>1:raise ValueError('Use one armature per custom model')
    if settings.clips and any(o.data.shape_keys and o.data.shape_keys.animation_data for o in meshes):raise ValueError('Animated shape keys require vertex-animation export; bake to a supported skeletal setup first')
    unit=root['wl_unit_meters'];origin=root.matrix_world.inverted();nodes=[('root',-1)];bone_ids={};object_ids={}
    def relative(obj):
        current=obj;matrix=Matrix.Identity(4)
        while current and current!=root:
            if current.constraints or current.parent_type!='OBJECT':return origin@obj.matrix_world
            matrix=current.matrix_local@matrix;current=current.parent
        return matrix if current==root else origin@obj.matrix_world
    for o in objects:
        object_ids[o]=len(nodes);nodes.append(('object_'+o.name,0))
        if o.type=='ARMATURE':
            pending=list(o.data.bones)
            while pending:
                ready=[b for b in pending if b.parent is None or b.parent.name in bone_ids]
                if not ready:raise ValueError('Invalid armature hierarchy')
                for bone in ready:
                    bone_ids[bone.name]=len(nodes);nodes.append((bone.name,bone_ids[bone.parent.name] if bone.parent else object_ids[o]));pending.remove(bone)
    if len(nodes)>128:raise ValueError('Model exceeds the supported 128-bone limit')
    def transforms(rest=False):
        matrices=[Matrix.Identity(4)]
        for obj in objects:
            matrices.append(relative(obj))
            if obj.type=='ARMATURE':
                bones=sorted(obj.data.bones,key=lambda b:bone_ids[b.name])
                matrices.extend(relative(obj)@(b.matrix_local if rest else obj.pose.bones[b.name].matrix) for b in bones)
        return matrices
    def skeleton(matrices):
        lines=[]
        for i,m in enumerate(matrices):
            parent=nodes[i][1];local=matrices[parent].inverted()@m if parent>=0 else m
            pos,rot,scale=local.decompose()
            if (scale-Vector((1,1,1))).length>1e-4 and settings.clips:raise ValueError('Apply armature/object scale before exporting animated models')
            values=[*(v/unit for v in pos),*rot.to_euler('XYZ')]
            lines.append(str(i)+' '+' '.join(number(v) for v in values))
        return lines
    header=['version 1','nodes',*[f'{i} {quote(name)} {parent}' for i,(name,parent) in enumerate(nodes)],'end','skeleton']
    frame=scene.frame_current;subframe=scene.frame_subframe;poses={r:r.data.pose_position for r in rigs}
    result={};collision_points=[]
    try:
        for r in rigs:r.data.pose_position='REST'
        bpy.context.view_layer.update();reference=transforms(True)
        lines=[*header,'time 0',*skeleton(reference),'end','triangles']
        dg=bpy.context.evaluated_depsgraph_get()
        for obj in meshes:
            if settings.clips:
                for mod in obj.modifiers:
                    if mod.type in {'WAVE','CLOTH','SOFT_BODY','MESH_CACHE','MESH_SEQUENCE_CACHE'}:raise ValueError('Animated mesh deformation needs skeletal export: '+obj.name)
                    if mod.type=='NODES' and mod.node_group and any(n.bl_idname=='GeometryNodeInputSceneTime' for n in mod.node_group.nodes):raise ValueError('Bake time-dependent Geometry Nodes to supported animation before model export')
            evaluated=obj.evaluated_get(dg);mesh=evaluated.to_mesh(preserve_all_data_layers=True,depsgraph=dg)
            try:
                mesh.calc_loop_triangles();matrix=relative(obj);normal_matrix=matrix.to_3x3().inverted().transposed()
                uv=next((layer for layer in mesh.uv_layers if layer.active_render),mesh.uv_layers.active)
                if not uv:raise ValueError('UV unwrap the model before compiling: '+obj.name)
                arm=next((m.object for m in obj.modifiers if m.type=='ARMATURE' and m.object),None)
                if arm and arm not in rigs:raise ValueError('Include the mesh armature in the model assignment')
                for tri in mesh.loop_triangles:
                    mat=mesh.materials[tri.material_index] if tri.material_index<len(mesh.materials) else None
                    if mat:mat=mat.original
                    lines.append(material_names[mat])
                    face_uv=uv
                    if mat and mat.use_nodes:
                        requested={n.uv_map for n in mat.node_tree.nodes if n.type=='UVMAP' and n.uv_map}
                        if len(requested)>1:raise ValueError('Bake model material UV layers to one UV set: '+mat.name)
                        if requested:
                            face_uv=mesh.uv_layers.get(next(iter(requested)))
                            if face_uv is None:raise ValueError('Model material requests a missing UV layer: '+mat.name)
                    loops=list(tri.loops)
                    if matrix.determinant()<0:loops.reverse()
                    for li in loops:
                        vertex=mesh.vertices[mesh.loops[li].vertex_index];p=matrix@vertex.co/unit;n=(normal_matrix@mesh.corner_normals[li].vector).normalized();tex=face_uv.data[li].uv
                        weights=[]
                        if arm:
                            weights=[(bone_ids[obj.vertex_groups[g.group].name],g.weight) for g in vertex.groups if g.group<len(obj.vertex_groups) and obj.vertex_groups[g.group].name in bone_ids and g.weight>1e-6]
                            if len(weights)>3:raise ValueError('Limit model vertex influences to three bones: '+obj.name)
                        if not weights:weights=[(object_ids[obj],1.)]
                        total=sum(w for _,w in weights);weights=[(i,w/total) for i,w in weights]
                        values=[*p,*n,tex.x,tex.y];links=' '.join(str(i)+' '+number(w) for i,w in weights)
                        lines.append(str(weights[0][0])+' '+' '.join(number(v) for v in values)+' '+str(len(weights))+' '+links)
                        collision_points.append(tuple(p))
            finally:evaluated.to_mesh_clear()
        lines.append('end');result['reference.smd']='\n'.join(lines)+'\n'
        for r in rigs:r.data.pose_position=poses[r]
        for i,clip in enumerate(settings.clips):
            if clip.end<clip.start or clip.end-clip.start>10000:raise ValueError('Invalid model animation clip range')
            lines=[*header]
            for at,fr in enumerate(range(clip.start,clip.end+1)):
                scene.frame_set(fr);lines.extend(['time '+str(at),*skeleton(transforms())])
            result[f'clip_{i}.smd']='\n'.join([*lines,'end'])+'\n'
        if settings.collision:
            obj=settings.collision;ev=obj.evaluated_get(dg);mesh=ev.to_mesh()
            try:collision_points=[tuple(relative(obj)@v.co/unit) for v in mesh.vertices]
            finally:ev.to_mesh_clear()
        if settings.collision_mode=='NONE':return result
        bm=bmesh.new()
        try:
            for p in set(collision_points):bm.verts.new(p)
            if len(bm.verts)<4:raise ValueError('Model collision needs a volume')
            bmesh.ops.convex_hull(bm,input=list(bm.verts),use_existing_faces=False);bmesh.ops.triangulate(bm,faces=list(bm.faces))
            bm.normal_update()
            lines=['version 1','nodes','0 "root" -1','end','skeleton','time 0','0 0 0 0 0 0 0','end','triangles']
            for face in bm.faces:
                lines.append(next(iter(material_names.values())))
                for v in face.verts:lines.append('0 '+' '.join(number(x) for x in (*v.co,*face.normal,0.,0.)))
            result['collision.smd']='\n'.join([*lines,'end'])+'\n'
        finally:bm.free()
        return result
    finally:
        for r,value in poses.items():r.data.pose_position=value
        scene.frame_set(frame,subframe=subframe);bpy.context.view_layer.update()
