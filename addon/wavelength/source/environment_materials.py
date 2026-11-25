"""Independent live native paint attributes and shader composition.

Privateer's six-biome palette is an explicit material adapter, not engine policy.
"""
import bpy
from pathlib import Path
import re

BIOMES=('Mixed Woodland','Meadow','Conifer Upland','Wetland','Rocky Heath','Coastal Shore')


PALETTES=((6,17,12),(7,6,13),(3,4,5),(8,9,15),(10,11,14),(0,1,16))


def local_biomes(obj,base):
    """Read actual control texels in this module, avoiding unused GPU samplers."""
    from mathutils import Vector
    points=[obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    x0,x1=min(p.x for p in points),max(p.x for p in points)
    y0,y1=min(p.y for p in points),max(p.y for p in points)
    result=set()
    for node in base.node_tree.nodes:
        if node.type!='TEX_IMAGE' or not node.image:continue
        suffix='a' if 'biome-control-a' in node.image.name else 'b' if 'biome-control-b' in node.image.name else None
        if suffix is None:continue
        image=node.image;width,height=image.size
        lo_x=max(0,min(width-1,int((x0/12000+.5)*width)))
        hi_x=max(0,min(width-1,int((x1/12000+.5)*width)))
        lo_y=max(0,min(height-1,int((y0/12000+.5)*height)))
        hi_y=max(0,min(height-1,int((y1/12000+.5)*height)))
        pixels=image.pixels[:]
        for y in range(lo_y,hi_y+1):
            for x in range(lo_x,hi_x+1):
                values=pixels[(y*width+x)*4:(y*width+x)*4+4]
                for channel in range(4 if suffix=='a' else 2):
                    if values[channel]>.001:result.add(channel if suffix=='a' else channel+4)
                if suffix=='b' and values[2]>.001 and values[1]>.001:result.add(4)
    return result


def shader_group(material,biome=None,allowed=None):
    if not material.use_nodes:raise ValueError('Paint materials require shader nodes')
    tree=bpy.data.node_groups.new(material.name+' · paint shader','ShaderNodeTree')
    mapping={}
    for source in material.node_tree.nodes:
        copy=tree.nodes.new(source.bl_idname);mapping[source]=copy
        for prop in source.bl_rna.properties:
            if prop.is_readonly or prop.identifier in {'rna_type','name','parent','inputs','outputs'} or prop.type=='COLLECTION':continue
            try:setattr(copy,prop.identifier,getattr(source,prop.identifier))
            except (AttributeError,TypeError,ValueError):pass
        for original,target in zip(source.inputs,copy.inputs):
            if hasattr(original,'default_value'):
                try:target.default_value=original.default_value
                except (AttributeError,TypeError,ValueError):pass
        if source.type in {'VALTORGB','CURVE_RGB','CURVE_VEC','CURVE_FLOAT'}:
            bpy.data.node_groups.remove(tree)
            raise ValueError('Bake curve/ramp paint shaders before composing them')
    for link in material.node_tree.links:
        source,target=mapping[link.from_node],mapping[link.to_node]
        out=list(link.from_node.outputs).index(link.from_socket)
        inp=list(link.to_node.inputs).index(link.to_socket)
        tree.links.new(source.outputs[out],target.inputs[inp])
    if allowed is not None:
        needed={texture for index in allowed for texture in PALETTES[index]}
        for node in list(tree.nodes):
            match=re.fullmatch(r'(albedo|surface)_(\d+)',node.label)
            if not match or int(match[2]) in needed:continue
            for link in list(node.outputs['Color'].links):
                socket=link.to_socket;tree.links.remove(link)
                socket.default_value=(.5,.5,.5,1) if socket.type=='RGBA' else (.5,.5,.5) if socket.type=='VECTOR' else .5
            for link in list(node.outputs['Alpha'].links):
                socket=link.to_socket;tree.links.remove(link);socket.default_value=1.
            tree.nodes.remove(node)
    tree['wl_environment_material_group']=True
    outputs=[n for n in tree.nodes if n.type=='OUTPUT_MATERIAL']
    active=next((n for n in outputs if n.is_active_output),None)
    socket=active.inputs['Surface'].links[0].from_socket if active and active.inputs['Surface'].links else None
    if socket is None:raise ValueError('Material has no active Surface shader')
    if biome is not None:
        # Keep the original projection, source textures and per-biome detail graph.
        images={}
        for node in tree.nodes:
            if node.type=='TEX_IMAGE' and node.image:
                for suffix in ('a','b'):
                    if 'biome-control-'+suffix in node.image.name:images[suffix]=node
        if set(images)!= {'a','b'}:raise ValueError('Privateer biome adapter needs biome-control-a and biome-control-b inputs')
        sockets=[]
        for suffix in ('a','b'):
            image=images[suffix]
            separate=next((link.to_node for link in image.outputs['Color'].links if link.to_node.type=='SEPARATE_COLOR'),None)
            if separate is None:raise ValueError('Missing Privateer biome channel separation')
            sockets.extend(list(separate.outputs)[:3] if suffix=='a' else list(separate.outputs)[:2])
            if suffix=='a':sockets.append(image.outputs['Alpha'])
        for index,output in enumerate(sockets):
            for link in list(output.links):
                target=link.to_socket;tree.links.remove(link);target.default_value=1. if index==biome else 0.
    for node in outputs:tree.nodes.remove(node)
    tree.interface.new_socket(name='Shader',in_out='OUTPUT',socket_type='NodeSocketShader')
    output=tree.nodes.new('NodeGroupOutput');tree.links.new(socket,output.inputs['Shader'])
    return tree


def biome_preview_group(base,biome=None):
    """GPU-friendly authoring proxy. Native export retains all three surfaces/biome."""
    tree=bpy.data.node_groups.new('Privateer biome authoring preview','ShaderNodeTree')
    tree['wl_environment_material_group']=True
    tree.interface.new_socket(name='Shader',in_out='OUTPUT',socket_type='NodeSocketShader')
    nodes,links=tree.nodes,tree.links
    images={n.label:n.image for n in base.node_tree.nodes if n.type=='TEX_IMAGE' and n.image}
    controls={suffix:next((n.image for n in base.node_tree.nodes if n.type=='TEX_IMAGE' and n.image and 'biome-control-'+suffix in n.image.name),None) for suffix in ('a','b')}
    def math(op,a,b):
        n=nodes.new('ShaderNodeMath');n.operation=op
        for i,v in enumerate((a,b)):
            if isinstance(v,(int,float)):n.inputs[i].default_value=v
            else:links.new(v,n.inputs[i])
        return n.outputs[0]
    def vector(op,a,b):
        n=nodes.new('ShaderNodeVectorMath');n.operation=op;links.new(a,n.inputs[0])
        if op=='SCALE':
            if isinstance(b,(int,float)):n.inputs['Scale'].default_value=b
            else:links.new(b,n.inputs['Scale'])
        elif isinstance(b,tuple):n.inputs[1].default_value=b
        else:links.new(b,n.inputs[1])
        return n.outputs['Vector']
    position=nodes.new('ShaderNodeNewGeometry').outputs['Position']
    weights=[]
    if biome is None:
        coords=vector('ADD',vector('SCALE',position,1/12000),(.5,.5,0))
        for suffix in ('a','b'):
            if controls[suffix] is None:raise ValueError('Privateer biome control images are missing')
            texture=nodes.new('ShaderNodeTexImage');texture.image=controls[suffix];texture.extension='EXTEND'
            links.new(coords,texture.inputs['Vector']);channels=nodes.new('ShaderNodeSeparateColor')
            links.new(texture.outputs['Color'],channels.inputs[0]);weights.extend(list(channels.outputs)[:3] if suffix=='a' else list(channels.outputs)[:2])
            if suffix=='a':weights.append(texture.outputs['Alpha'])
        total=weights[0]
        for weight in weights[1:]:total=math('ADD',total,weight)
        total=math('MAXIMUM',total,.001);weights=[math('DIVIDE',weight,total) for weight in weights]
    color=None;roughness=None
    for index in range(6) if biome is None else (biome,):
        surface=PALETTES[index][0]
        tile=4. if surface==0 else .42 if surface==3 else 1. if surface in {5,10,12} else 2.
        coords=vector('SCALE',position,1/tile)
        samples={}
        for kind in ('albedo','surface'):
            image=images.get(f'{kind}_{surface}')
            if image is None:raise ValueError(f'Privateer preview missing {kind}_{surface}')
            texture=nodes.new('ShaderNodeTexImage');texture.image=image;texture.projection='BOX';texture.projection_blend=.25
            links.new(coords,texture.inputs['Vector']);samples[kind]=texture.outputs['Color']
        channels=nodes.new('ShaderNodeSeparateColor');links.new(samples['surface'],channels.inputs[0])
        weighted_color=samples['albedo'] if biome is not None else vector('SCALE',samples['albedo'],weights[index])
        weighted_rough=channels.outputs[0] if biome is not None else math('MULTIPLY',channels.outputs[0],weights[index])
        color=weighted_color if color is None else vector('ADD',color,weighted_color)
        roughness=weighted_rough if roughness is None else math('ADD',roughness,weighted_rough)
    shader=nodes.new('ShaderNodeBsdfPrincipled');links.new(color,shader.inputs['Base Color']);links.new(roughness,shader.inputs['Roughness'])
    links.new(shader.outputs[0],nodes.new('NodeGroupOutput').inputs['Shader'])
    return tree


def refresh(obj):
    if obj.type!='MESH' or obj.data.users>1:raise ValueError('Use a single-user terrain mesh')
    if len(obj.data.materials)!=1:raise ValueError('Live environment material composition currently requires one base material slot')
    base=obj.get('wl_environment_base_material') or obj.data.materials[0]
    if base is None:raise ValueError('Assign a base terrain material')
    enabled=[l for l in obj.wavelength_environment_layers if l.kind=='MATERIAL' and l.enabled]
    # Build all replacements before changing the native authoring stack.
    groups=[];material=None;attributes=None
    try:
        material=bpy.data.materials.new(base.name+' · painted environment');material.use_nodes=True
        material['wl_environment_preview_material']=True
        nodes=material.node_tree.nodes;nodes.clear();links=material.node_tree.links
        base_node=nodes.new('ShaderNodeGroup')
        base_node.node_tree=biome_preview_group(base) if obj.wavelength_environment_material_adapter=='PRIVATEER' else shader_group(base)
        groups.append(base_node.node_tree)
        result=base_node.outputs['Shader']
        attributes=bpy.data.node_groups.new('Environment material mask attributes','GeometryNodeTree')
        attributes.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry')
        attributes.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
        geometry=attributes.nodes.new('NodeGroupInput').outputs['Geometry']
        for layer in enabled:
            paint=nodes.new('ShaderNodeGroup')
            if obj.wavelength_environment_material_adapter=='PRIVATEER' and layer.biome!='CUSTOM':
                paint.node_tree=biome_preview_group(base,int(layer.biome))
            elif layer.material:paint.node_tree=shader_group(layer.material)
            else:raise ValueError(f'{layer.name}: choose a paint material')
            groups.append(paint.node_tree)
            name='wl_env_mask_'+layer.uid
            weight=attributes.nodes.new('GeometryNodeInputNamedAttribute');weight.data_type='FLOAT';weight.inputs['Name'].default_value=layer.mask
            store=attributes.nodes.new('GeometryNodeStoreNamedAttribute');store.data_type='FLOAT';store.domain='POINT'
            store.inputs['Name'].default_value=name
            attributes.links.new(geometry,store.inputs['Geometry']);attributes.links.new(weight.outputs['Attribute'],store.inputs['Value'])
            geometry=store.outputs['Geometry']
            attribute=nodes.new('ShaderNodeAttribute');attribute.attribute_name=name
            mix=nodes.new('ShaderNodeMixShader');links.new(attribute.outputs['Fac'],mix.inputs[0])
            links.new(result,mix.inputs[1]);links.new(paint.outputs['Shader'],mix.inputs[2]);result=mix.outputs[0]
        attributes.links.new(geometry,attributes.nodes.new('NodeGroupOutput').inputs['Geometry'])
        links.new(result,nodes.new('ShaderNodeOutputMaterial').inputs['Surface'])
    except Exception:
        if material:bpy.data.materials.remove(material)
        if attributes:bpy.data.node_groups.remove(attributes)
        for tree in groups:
            if tree.users==0:bpy.data.node_groups.remove(tree)
        raise
    old=obj.data.materials[0]
    obj['wl_environment_base_material']=base;obj.data.materials[0]=material
    modifier=next((m for m in obj.modifiers if m.type=='NODES' and m.node_group and m.node_group.get('wl_environment_mask_attributes')),None)
    if modifier is None:modifier=obj.modifiers.new('Environment paint masks (live)','NODES')
    old_tree=modifier.node_group;attributes['wl_environment_mask_attributes']=True;modifier.node_group=attributes
    if old_tree and old_tree.users==0:bpy.data.node_groups.remove(old_tree)
    if old and old.get('wl_environment_preview_material') and old.users==0:
        old_groups=[n.node_tree for n in old.node_tree.nodes if n.type=='GROUP' and n.node_tree]
        bpy.data.materials.remove(old)
        for tree in old_groups:
            if tree.users==0:bpy.data.node_groups.remove(tree)
    return material


def save_image(image,path):
    copy=bpy.data.images.new('.environment image export',*image.size,alpha=True)
    try:
        copy.colorspace_settings.name=image.colorspace_settings.name
        copy.pixels[:]=image.pixels[:];copy.file_format='PNG';copy.filepath_raw=str(path);copy.save()
    finally:bpy.data.images.remove(copy)


def pbr_description(material,stage,key):
    from . import mesh_assets
    shader=mesh_assets._shader(material)
    image=mesh_assets._base_image(material)
    result={'color':list(shader.inputs['Base Color'].default_value) if shader else list(material.diffuse_color),
            'roughness':float(shader.inputs['Roughness'].default_value) if shader else .5}
    if shader and any(shader.inputs[name].is_linked for name in ('Roughness','Metallic','Normal')):
        raise ValueError(f'{material.name}: use a baked paint material or the native biome adapter for linked normal/roughness inputs')
    if image:
        path=stage/'materials'/f'{key}.png';path.parent.mkdir(exist_ok=True)
        save_image(image,path);result['texture']=path.relative_to(stage).as_posix()
    return result


def export_description(obj,surface,stage):
    enabled=[l for l in obj.wavelength_environment_layers if l.kind=='MATERIAL' and l.enabled]
    native=obj.wavelength_environment_native_material.strip()
    if not enabled and not native:return None
    adapter=obj.wavelength_environment_material_adapter
    if adapter=='PRIVATEER' and not native:raise ValueError('Privateer terrain painting requires its Godot base material path')
    if native and (not native.startswith('res://') or '..' in native.split('/')):raise ValueError('Godot base material must be a res:// reference')
    base=obj.get('wl_environment_base_material') or obj.data.materials[0]
    result={'adapter':adapter,'native_material':native,'layers':[]}
    if adapter=='PBR':result['base']=pbr_description(base,stage,env_id(obj)+'_base')
    x0,y0,x1,y1=surface.bounds
    result['bounds']=[x0,-y1,x1,-y0]
    size=obj.wavelength_environment_mask_resolution
    folder=stage/'materials';folder.mkdir(exist_ok=True)
    for layer in enabled:
        image=bpy.data.images.new('.environment mask export',size,size,alpha=True)
        try:
            image.colorspace_settings.name='Non-Color'
            pixels=[]
            for row in range(size):
                y=y0+(row+.5)/size*(y1-y0)
                for column in range(size):
                    x=x0+(column+.5)/size*(x1-x0)
                    hit=surface.hit(x,y)
                    value=surface.weight(layer.mask,hit[0],hit[2]) if hit else 0.
                    pixels.extend((value,value,value,1))
            image.pixels[:]=pixels;image.file_format='PNG';path=folder/f'{layer.uid}_mask.png'
            image.filepath_raw=str(path);image.save()
        finally:bpy.data.images.remove(image)
        spec={'id':layer.uid,'mask':path.relative_to(stage).as_posix()}
        if adapter=='PRIVATEER':
            if layer.biome=='CUSTOM':raise ValueError('Choose one of the six native Privateer paint biomes')
            spec['biome']=int(layer.biome)
        else:
            if layer.material is None:raise ValueError(f'{layer.name}: choose a paint material')
            spec['pbr']=pbr_description(layer.material,stage,layer.uid)
            if spec['pbr'].get('texture') and not obj.data.uv_layers:
                raise ValueError('UV unwrap the terrain before using textured PBR paint, or select the native biome adapter')
        result['layers'].append(spec)
    return result


def env_id(obj):
    from .environment_layers import identity
    return identity(obj)
