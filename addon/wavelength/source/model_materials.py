"""Convert supported Blender model materials to owned VMT/VTF dependencies."""
from array import array
import json,base64
from . import model_formats,source_assets


def texture(image,normal=False):
    if image.source not in {'FILE','GENERATED'} or image.is_multiview:raise ValueError('Model textures must be single file/generated images; bake tiled/movie/procedural textures first')
    w,h=image.size
    if not w or not h:raise ValueError('Model image is missing pixels: '+image.name)
    pixels=array('f',[0.]*(w*h*4));image.pixels.foreach_get(pixels);out=bytearray(w*h*4)
    srgb=not normal and image.colorspace_settings.name in {'Linear','Linear Rec.709','Linear Rec.2020'}
    for y in range(h):
        for x in range(w):
            src=((h-1-y)*w+x)*4;dst=(y*w+x)*4
            for c in range(4):
                v=max(0.,min(1.,pixels[src+c]))
                if normal and c==1:v=1-v
                if c<3 and srgb:v=12.92*v if v<=.0031308 else 1.055*v**(1/2.4)-.055
                out[dst+c]=round(max(0.,min(1.,v))*255)
    return model_formats.vtf(w,h,out,normal)


def _convert_basic(material,name,settings,ignore_source=False):
    assets={};base='materials/'+name;props={}
    if material and material.get('wl_texture') and not ignore_source:
        original=source_assets.library(settings.game_dir).material(material['wl_texture'])
        if original.get('$basetexture2'):raise ValueError('Bake blended Source terrain materials to a single model texture first')
        if not original.get('$basetexture'):raise ValueError('Source model material needs a base texture: '+material.name)
        for key in ('$basetexture','$bumpmap','$alphatest','$translucent','$nocull','$selfillum'):
            if key in original:props[key]=original[key]
    else:
        color=(.8,.8,.8,1.)
        if material and material.use_nodes:
            output=next((n for n in material.node_tree.nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output),None)
            links=output.inputs['Surface'].links if output else []
            shader=links[0].from_node if links else None
            if shader is None or shader.type!='BSDF_PRINCIPLED':raise ValueError('Bake this model material to a Principled shader before export: '+material.name)
            for key in ('Metallic','Transmission Weight','Subsurface Weight','Emission Strength'):
                if shader.inputs.get(key) and shader.inputs[key].default_value>1e-6:raise ValueError(f'{material.name}: {key} requires a baked/engine-specific material before Source model export')
            for socket in shader.inputs:
                if socket.is_linked and socket.name not in {'Base Color','Normal','Alpha'}:raise ValueError(f'{material.name}: bake connected {socket.name} before Source model export')
            color=tuple(shader.inputs['Base Color'].default_value)
            source=shader.inputs['Base Color'].links
            if source:
                node=source[0].from_node
                if node.type!='TEX_IMAGE' or node.image is None:raise ValueError('Bake procedural model color to an image: '+material.name)
                vector=node.inputs['Vector'].links
                if vector and vector[0].from_node.type not in {'UVMAP','TEX_COORD'}:raise ValueError('Bake transformed model UVs before export: '+material.name)
                if vector and vector[0].from_node.type=='TEX_COORD' and vector[0].from_socket.name!='UV':raise ValueError('Source model textures require UV coordinates')
                assets[base+'_color.vtf']=texture(node.image);props['$basetexture']=name+'_color'
            normal=shader.inputs['Normal'].links
            if normal:
                node=normal[0].from_node
                if node.type!='NORMAL_MAP' or node.space!='TANGENT' or not node.inputs['Color'].is_linked:raise ValueError('Source model normal maps need a tangent Normal Map node')
                if abs(node.inputs['Strength'].default_value-1)>1e-6:raise ValueError('Bake the normal-map strength into the image before Source export')
                image=node.inputs['Color'].links[0].from_node
                if image.type!='TEX_IMAGE' or image.image is None:raise ValueError('Bake the model normal map to an image')
                assets[base+'_normal.vtf']=texture(image.image,True);props['$bumpmap']=name+'_normal'
            alpha=shader.inputs['Alpha']
            if alpha.is_linked and (not source or alpha.links[0].from_node!=source[0].from_node or alpha.links[0].from_socket.name!='Alpha'):raise ValueError('Bake model alpha into its base-color image')
            if alpha.is_linked or alpha.default_value<.999:props['$translucent']='1'
            if not alpha.is_linked and alpha.default_value<.999:props['$alpha']=str(alpha.default_value)
        elif material:color=tuple(material.diffuse_color)
        if '$basetexture' not in props:
            rgba=[]
            for c,v in enumerate(color):
                if c<3:v=12.92*v if v<=.0031308 else 1.055*v**(1/2.4)-.055
                rgba.append(round(max(0,min(1,v))*255))
            assets[base+'_color.vtf']=model_formats.vtf(1,1,rgba);props['$basetexture']=name+'_color'
    text='"VertexLitGeneric"\n{\n'+''.join(' '+model_formats.quote(k)+' '+model_formats.quote(v)+'\n' for k,v in props.items())+'}\n'
    assets[base+'.vmt']=text.encode();return assets


TEXTURES={'$basetexture','$bumpmap','$detail','$envmapmask','$selfillummask','$phongexponenttexture','$lightwarptexture','$blendmodulatetexture','$bumpmap2'}


def _source(material,settings):
    if material.get('wl_model_source_vmt'):
        return json.loads(material['wl_model_source_vmt']),json.loads(material.get('wl_model_source_files','{}'))
    game=material.get('wl_source_game') or settings.game_dir
    library=source_assets.library(game);props=library.material(material['wl_texture']);files={}
    for field in TEXTURES:
        value=props.get(field)
        if value:
            path='materials/'+source_assets.asset_path(value).removeprefix('materials/').removesuffix('.vtf')+'.vtf'
            files[field]=base64.b64encode(library.read(path)).decode('ascii')
    return props,files


def realize(material,settings):
    """Own full-resolution source images and retain native shader dependencies.

    Only model-owned materials call this function. Engine preview caches are
    untouched; the source VMT/texture bytes survive a portable blend/package.
    """
    if not material or not material.get('wl_texture') or material.get('wl_model_material_editable'):return []
    import bpy,numpy as np
    props,files=_source(material,settings)
    if props.get('$basetexture2'):raise ValueError(material.name+': blended terrain needs baking before model compilation')
    material['wl_model_source_vmt']=json.dumps(props);material['wl_model_source_files']=json.dumps(files)
    warnings=[];material.use_nodes=True;nodes=material.node_tree.nodes
    shader=next((n for n in nodes if n.type=='BSDF_PRINCIPLED'),None)
    # Preserve an existing edited graph; populate only untouched engine previews.
    existing=bool(shader and shader.inputs['Base Color'].is_linked)
    if not existing:
        nodes.clear();shader=nodes.new('ShaderNodeBsdfPrincipled');output=nodes.new('ShaderNodeOutputMaterial')
        material.node_tree.links.new(shader.outputs['BSDF'],output.inputs['Surface']);shader.inputs['Roughness'].default_value=.7
        uv=nodes.new('ShaderNodeUVMap');uv.uv_map=''
        for field,encoded in files.items():
            try:
                _,_,w,h,pixels=source_assets.decode_vtf(base64.b64decode(encoded),max_dimension=None)
            except ValueError as exc:
                if field=='$basetexture':raise
                warnings.append(material.name+': native '+field+' retained without editable preview: '+str(exc));continue
            image=bpy.data.images.new(material.name+' '+field,w,h,alpha=True)
            image.colorspace_settings.name='Non-Color' if field!='$basetexture' else 'sRGB'
            data=np.frombuffer(pixels,dtype=np.uint8).astype(np.float32)/255
            if field=='$bumpmap':data[1::4]=1-data[1::4]
            image.pixels.foreach_set(data);image.update()
            from .model_lifecycle import _pack_image
            _pack_image(image);image['wl_model_owned_image']=True
            tex=nodes.new('ShaderNodeTexImage');tex.image=image;tex['wl_model_texture_field']=field
            material.node_tree.links.new(uv.outputs['UV'],tex.inputs['Vector'])
            if field=='$basetexture':
                material.node_tree.links.new(tex.outputs['Color'],shader.inputs['Base Color'])
                if props.get('$translucent')=='1' or props.get('$alphatest')=='1':material.node_tree.links.new(tex.outputs['Alpha'],shader.inputs['Alpha'])
            elif field=='$bumpmap':
                normal=nodes.new('ShaderNodeNormalMap');material.node_tree.links.new(tex.outputs['Color'],normal.inputs['Color']);material.node_tree.links.new(normal.outputs['Normal'],shader.inputs['Normal'])
    material['wl_model_material_editable']=True
    for key in ('wl_source_native_material','wl_source_cache_key','wl_source_pending'):material.pop(key,None)
    return warnings


def convert(material,name,settings):
    """Build self-contained dependencies; edited nodes override native inputs."""
    if not material or not material.get('wl_texture'):return _convert_basic(material,name,settings)
    from . import keyvalues
    props,files=_source(material,settings)
    if props.get('$basetexture2'):raise ValueError('Bake blended Source terrain materials to a single model texture first')
    shader=props.get('_wl_shader','vertexlitgeneric').lower()
    if shader not in {'vertexlitgeneric','unlitgeneric','lightmappedgeneric'}:raise ValueError(material.name+': unsupported model shader '+shader+'; bake or author a compatible model material')
    result={};values={k:v for k,v in props.items() if not k.startswith('_wl_')}
    editable=material.get('wl_model_material_editable',False)
    for field,encoded in files.items():
        if editable and field in {'$basetexture','$bumpmap'}:continue
        path=name+'_'+field.lstrip('$');result['materials/'+path+'.vtf']=base64.b64decode(encoded);values[field]=path
    if editable:
        graph=_convert_basic(material,name,settings,ignore_source=True)
        graph_props=keyvalues.values(keyvalues.child(keyvalues.parse(graph['materials/'+name+'.vmt'].decode()),'VertexLitGeneric'))
        if '$bumpmap' not in graph_props:
            # Unsupported native normal encodings remain a native dependency.
            if '$bumpmap' in files and not any(n.get('wl_model_texture_field')=='$bumpmap' for n in material.node_tree.nodes):
                path=name+'_native_normal';result['materials/'+path+'.vtf']=base64.b64decode(files['$bumpmap']);values['$bumpmap']=path
            else:values.pop('$bumpmap',None)
        values.update(graph_props);result.update({k:v for k,v in graph.items() if not k.endswith('.vmt')})
    text=model_formats.quote('UnlitGeneric' if shader=='unlitgeneric' else 'VertexLitGeneric')+'\n{\n'+''.join(' '+model_formats.quote(k)+' '+model_formats.quote(v)+'\n' for k,v in values.items())+'}\n'
    result['materials/'+name+'.vmt']=text.encode()
    return result
