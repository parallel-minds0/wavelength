"""Convert supported Blender model materials to owned VMT/VTF dependencies."""
from array import array
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


def convert(material,name,settings):
    assets={};base='materials/'+name;props={}
    if material and material.get('wl_texture'):
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
