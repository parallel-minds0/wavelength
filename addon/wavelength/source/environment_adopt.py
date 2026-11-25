"""Adopt existing native point-instance sets without flattening or losing the remainder."""
import json
import uuid

import bmesh
import bpy
from mathutils import Matrix, Vector
from . import environment_layers as env


def prototype(source):
    objects=[]
    for modifier in source.modifiers:
        if modifier.type=='NODES' and modifier.node_group:
            objects.extend(node.inputs['Object'].default_value for node in modifier.node_group.nodes
                           if node.bl_idname=='GeometryNodeObjectInfo' and node.inputs['Object'].default_value)
    objects=list(dict.fromkeys(objects))
    if source.type!='MESH' or source.data.polygons or len(objects)!=1:
        raise ValueError(f'{source.name}: select a point mesh with one Object Info prototype')
    for name in ('instance_rotation','instance_scale'):
        attr=source.data.attributes.get(name)
        if attr is None or attr.data_type!='FLOAT_VECTOR' or attr.domain!='POINT':
            raise ValueError(f'{source.name}: missing point vector attribute {name}')
    return objects[0]


def normalize_atlas(original):
    """Explicit local copy of photographic emission/transparent cards for PBR handoff."""
    from . import mesh_assets
    if all(not m or _supported(m) for m in original.data.materials):return original
    copies=[]
    for material in original.data.materials:
        if material is None:copies.append(None);continue
        if _supported(material):copies.append(material);continue
        nodes=material.node_tree.nodes if material.use_nodes else []
        images=[n.image for n in nodes if n.type=='TEX_IMAGE' and n.image]
        if len(images)!=1 or not any(n.type=='EMISSION' for n in nodes) or not any(n.type=='BSDF_TRANSPARENT' for n in nodes):
            raise ValueError(f'{original.name}: unsupported prototype shader; use an explicit PBR copy or Godot scene reference')
        copy=bpy.data.materials.new(material.name+' · editable PBR atlas');copy.use_nodes=True
        shader=copy.node_tree.nodes.get('Principled BSDF');shader.inputs['Roughness'].default_value=.92
        image=copy.node_tree.nodes.new('ShaderNodeTexImage');image.image=images[0]
        copy.node_tree.links.new(image.outputs['Color'],shader.inputs['Base Color'])
        copy.node_tree.links.new(image.outputs['Alpha'],shader.inputs['Alpha'])
        copy.use_backface_culling=False
        copies.append(copy)
    obj=original.copy();obj.data=original.data.copy();obj.name=original.name+' · editable palette'
    obj['wl_environment_id']=uuid.uuid4().hex
    obj.data.materials.clear()
    for mat in copies:obj.data.materials.append(mat)
    return obj


def _supported(material):
    from . import mesh_assets
    try:mesh_assets._base_image(material);return True
    except ValueError:return False


def adopt(context,terrain,source):
    """Create independent authored point layer for the footprint; retain outside points.

    Input convention matches Privateer's existing Geometry Nodes point meshes.
    Transforms and IDs survive adoption exactly. No inferred resampling or count cap.
    """
    proto=prototype(source)
    if not proto.matrix_world.is_identity:raise ValueError('Normalize the point prototype transforms first')
    scale=source.matrix_world.to_scale()
    if max(scale)-min(scale)>1e-5:
        raise ValueError('Bake nonuniform source-object scale into the point rotation/scale attributes before adoption')
    surface=env.Surface(context,terrain)
    selected=[];ground=[]
    try:
        for vertex in source.data.vertices:
            point=source.matrix_world @ vertex.co
            x0,y0,x1,y1=surface.bounds
            if not (x0<=point.x<x1 and y0<=point.y<y1):continue
            hit=surface.hit(point.x,point.y)
            if hit is not None:selected.append(vertex.index);ground.append(hit[0].z)
    finally:surface.close()
    if not selected:return None
    proto=normalize_atlas(proto)
    collection=bpy.data.collections.new(source.name+' · palette');context.scene.collection.children.link(collection)
    if not proto.users_collection:collection.objects.link(proto)
    elif proto.name not in collection.objects:collection.objects.link(proto)
    proto.hide_set(True);proto.hide_render=True
    env.identity(proto)
    layer=env.add_layer(terrain,name=source.name.removeprefix('Forest_Points_Editable_')+' · adopted')
    layer.palette=collection;layer.mode='PLACEMENTS';layer.scale_min=1;layer.scale_max=1
    layer.seed=1;layer.source_origin=source.get('wl_adoption_origin',env.identity(source))
    layer.density=1
    mask=terrain.vertex_groups[layer.mask]
    mask.add(list(range(len(terrain.data.vertices))),1.,'REPLACE')
    points=bpy.data.meshes.new(source.name+' · authored patch points')
    points.from_pydata([source.matrix_world @ source.data.vertices[i].co for i in selected],[],[])
    for name in ('instance_rotation','instance_scale'):
        attr=points.attributes.new(name,'FLOAT_VECTOR','POINT')
        # Adopt arbitrary source-object transform into each point's local pose.
        values=[]
        for i in selected:
            rotation=source.data.attributes['instance_rotation'].data[i].vector
            scale=source.data.attributes['instance_scale'].data[i].vector
            from mathutils import Euler
            matrix=source.matrix_world @ Matrix.LocRotScale(source.data.vertices[i].co,Euler(rotation).to_quaternion(),Vector(scale))
            values.extend(matrix.to_euler() if name=='instance_rotation' else matrix.to_scale())
        attr.data.foreach_set('vector',values)
    id_attr=source.data.attributes.get('wl_adopted_id')
    points.attributes.new('wl_adopted_id','INT','POINT').data.foreach_set('value',[id_attr.data[i].value if id_attr else i for i in selected])
    points.attributes.new('wl_ground','FLOAT','POINT').data.foreach_set('value',ground)
    host=bpy.data.objects.new(source.name+' · authored placement data',points);context.scene.collection.objects.link(host)
    host.hide_set(True);host.hide_render=True;host['wl_editor_helper']=True;host['wl_exclude']=True
    layer.placements=host;layer.adopt_source=source
    remainder=source.copy();remainder.data=source.data.copy();remainder.name=source.name+' · outside adopted patch'
    remainder['wl_adoption_origin']=layer.source_origin;remainder['wl_environment_id']=uuid.uuid4().hex
    if not remainder.data.attributes.get('wl_adopted_id'):
        remainder.data.attributes.new('wl_adopted_id','INT','POINT').data.foreach_set('value',list(range(len(source.data.vertices))))
    bm=bmesh.new();bm.from_mesh(remainder.data);bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[bm.verts[i] for i in selected],context='VERTS');bm.to_mesh(remainder.data);bm.free()
    context.scene.collection.objects.link(remainder);layer.adopt_remainder=remainder
    layer.source_hidden=source.hide_get();layer.source_render_hidden=source.hide_render
    source.hide_set(True);source.hide_render=True
    return layer


def placement_candidates(surface,layer):
    source=layer.placements
    if source is None:raise ValueError(f'{layer.name}: adopted placement data is missing')
    proto=env.palette(layer)[0]
    from mathutils import Euler
    for vertex in source.data.vertices:
        index=vertex.index
        address=f"adopted:{layer.source_origin}:{source.data.attributes['wl_adopted_id'].data[index].value}"
        point=source.matrix_world @ vertex.co
        hit=surface.hit(point.x,point.y)
        if hit is None:continue
        if layer.follow_terrain:point.z+=hit[0].z-source.data.attributes['wl_ground'].data[index].value
        rotation=Euler(source.data.attributes['instance_rotation'].data[index].vector).to_quaternion()
        scale=Vector(source.data.attributes['instance_scale'].data[index].vector)
        variation=layer.scale_min+(layer.scale_max-layer.scale_min)*env.distribution.random_value(layer.seed,address,'scale')
        matrix=Matrix.LocRotScale(point,rotation,scale*variation)
        yield address,hit,proto,matrix
