"""Deploy Source 1 material images as editable Source 2 content, never previews."""
import json,shutil,zipfile,os
from types import SimpleNamespace
from pathlib import Path
from . import source_assets,mesh_assets


# These stock paths were checked against CS2's mounted material library. Tool
# identity is compiler metadata: converting its preview image loses semantics.
TOOL_MATERIALS={'tools/toolsskybox','tools/toolsnodraw','tools/toolstrigger','tools/toolsclip','tools/toolsplayerclip','tools/toolsnpcclip','tools/toolsgrenadeclip','tools/toolsskip','tools/toolsinvisible','tools/toolsinvisibleladder','tools/toolsoccluder'}
CLIP_VARIANTS={'concrete','dirt','glass','grass','gravel','metal','metal_sand_barrel','metalgrate','metalvehicle','plastic','rubber','rubbertire','sand','snow','tile','wood','wood_basket','wood_crate'}


def tool_material(material,warnings=None):
    import bpy
    original=bpy.data.materials.get(material.get('wl_source1_original',''))
    name=source_assets.asset_path((original or material).get('wl_texture','')).removeprefix('materials/').removesuffix('.vmt').removesuffix('.vmat')
    if name in TOOL_MATERIALS:return 'materials/'+name+'.vmat'
    if name=='tools/toolsskybox2d':
        if warnings is not None:warnings.append(material.name+': mapped Source 1 2D sky boundary to CS2 sky; review sky environment setup in Hammer')
        return 'materials/tools/toolsskybox.vmat'
    if name.removeprefix('tools/toolsclip_') in CLIP_VARIANTS and name.startswith('tools/toolsclip_'):
        if warnings is not None:warnings.append(material.name+': mapped '+name+' to CS2 toolsclip; clipping retained, Source 1 surface-specific sounds/physics need review')
        return 'materials/tools/toolsclip.vmat'
    if name.startswith('tools/') and not material.get('wl_source2_material'):
        raise ValueError(material.name+': Source tool material needs an explicit CS2 equivalent: '+name)
    return None


def dependencies(root,relative):
    """Only loose, generated VMAT sources and their file texture inputs."""
    from . import keyvalues
    relative=source_assets.asset_path(relative)
    path=Path(root)/relative
    props=keyvalues.values(keyvalues.child(keyvalues.parse(path.read_text(encoding='utf-8-sig')),'Layer0'))
    yield relative
    for key,value in props.items():
        if key.startswith('texture') and value and not value.startswith('['):
            yield source_assets.asset_path(value)


def copy_generated(material,destination):
    relative=material['wl_source2_material']
    source=material.get('wl_source2_content_root')
    if not source or not relative.startswith('materials/wavelength/'):return
    for name in dependencies(source,relative):
        src=Path(source)/name;dst=Path(destination)/name
        if not src.is_file():raise ValueError('Generated CS2 material dependency is missing: '+str(src))
        if src.resolve()!=dst.resolve():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)


def package_project(filepath,root,materials,warnings):
    """Portable editable content; game-provided stock assets remain references."""
    path=Path(filepath);root=Path(root)
    files={}
    for relative in set(materials):
        if relative.startswith('materials/wavelength/'):
            for name in dependencies(root,relative):files[name]=root/name
    destination=path.with_suffix('.project.zip');temporary=destination.with_suffix('.zip.partial')
    try:
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as bundle:
            bundle.write(path,'maps/'+path.name)
            report=path.with_suffix('.crosscompile.json')
            if report.is_file():bundle.write(report,'maps/'+report.name)
            for name,source in sorted(files.items()):bundle.write(source,name)
            bundle.writestr('wavelength-project.json',json.dumps({'schema':1,'engine':'source2_cs2_windows','map':'maps/'+path.name,'files':sorted(files),'warnings':warnings},indent=2))
            bundle.writestr('README.txt','Extract into your CS2 addon content folder. Open maps/'+path.name+' in CS2 Hammer and compile. Stock CS2 assets require a CS2 installation. This is editable source, not a compiled playable map.\n')
        os.replace(temporary,destination)
    finally:
        if temporary.exists():temporary.unlink()
    return destination


def source_game(material,settings):
    # Old native bindings already persist their mount roots. New bindings also
    # record the owning game explicitly so changing the active profile is safe.
    candidates=[material.get('wl_source_game','')]
    if getattr(settings,'source_override',False):candidates.insert(0,str(settings.game_dir))
    candidates.extend(material.get('wl_source_mounts','').splitlines())
    candidates.append(str(settings.game_dir))
    checked=[];name=source_assets.asset_path(material['wl_texture']).removeprefix('materials/').removesuffix('.vmt')
    for value in candidates:
        if not value or not (Path(value)/'gameinfo.txt').is_file():continue
        directory=str(Path(value).resolve())
        if directory in checked:continue
        checked.append(directory)
        # A valid installation can belong to the wrong game. Test the winning
        # mounted VMT before accepting it, then try the remaining owned roots.
        if source_assets.library(directory).fingerprint('materials/'+name+'.vmt'):return value
    if checked:
        raise ValueError('Source material not found: materials/'+name+'.vmt; searched '+', '.join(checked)+'. Choose the correct Source Profile or Source Game Directory')
    raise ValueError(material.name+': original Source 1 game is unavailable; load this material in its source profile before switching to CS2')


def deploy_loaded(material,root,map_name,warnings):
    """Explicit fallback: use resident image pixels, never fabricate texture data."""
    import bpy
    from array import array
    image=mesh_assets._base_image(material)
    if image is None or min(image.size)<=0 or len(image.pixels)!=image.size[0]*image.size[1]*4:
        raise ValueError(material.name+': no loaded base-color texture pixels; locate/load the texture or provide the original game folder')
    relative=Path('materials/wavelength')/map_name/mesh_assets.token(material.name)
    (root/relative.parent).mkdir(parents=True,exist_ok=True)
    texture=relative.with_name(relative.name+'_color').with_suffix('.png')
    copy=bpy.data.images.new('.wavelength loaded texture conversion',width=image.size[0],height=image.size[1],alpha=True,float_buffer=image.is_float)
    try:
        copy.colorspace_settings.name=image.colorspace_settings.name
        pixels=array('f',[0])*len(image.pixels);image.pixels.foreach_get(pixels);copy.pixels.foreach_set(pixels)
        copy.update();copy.filepath_raw=str(root/texture);copy.file_format='PNG';copy.save()
    finally:bpy.data.images.remove(copy)
    shader=mesh_assets._shader(material)
    path=relative.with_suffix('.vmat')
    (root/path).write_text(mesh_assets.vmat(texture.as_posix(),shader.inputs['Roughness'].default_value if shader else .7),encoding='utf-8')
    warnings.append(material.name+': used loaded Blender base-color pixels without the source game; resolution may be a viewport preview, other shader channels need review')
    return path.as_posix()


def deploy(material,settings,root,map_name,warnings,*,use_loaded_textures=False):
    import bpy
    import numpy as np
    native=tool_material(material,warnings)
    if native:return native
    try:game=source_game(material,settings)
    except ValueError:
        if use_loaded_textures:return deploy_loaded(material,root,map_name,warnings)
        raise
    assets=source_assets.library(game)
    props=assets.material(material['wl_texture'])
    base=props.get('$basetexture') or props.get('%tooltexture')
    if not base:raise ValueError(material.name+': Source material has no base texture to convert')
    key=mesh_assets.token(str(assets.game)+'/'+material['wl_texture'])
    relative=Path('materials/wavelength')/map_name/key
    folder=root/relative.parent;folder.mkdir(parents=True,exist_ok=True)
    def image(value,suffix):
        path=source_assets.asset_path(value).removeprefix('materials/').removesuffix('.vtf')
        data=assets.read('materials/'+path+'.vtf')
        # Decode the original highest mip, not the reduced viewport cache.
        ow,oh,w,h,pixels=source_assets.decode_vtf(data,max_dimension=None)
        result=relative.with_name(key+suffix).with_suffix('.png')
        image=bpy.data.images.new('.wavelength Source 2 conversion',width=w,height=h,alpha=True)
        try:
            image.colorspace_settings.name='Non-Color' if suffix.startswith('_normal') or suffix=='_blend' else 'sRGB'
            image.pixels.foreach_set(np.frombuffer(pixels,dtype=np.uint8).astype(np.float32)/255)
            image.update();image.filepath_raw=str(root/result);image.file_format='PNG';image.save()
        finally:bpy.data.images.remove(image)
        return result.as_posix()
    color=image(base,'_color')
    if props.get('$basetexture2'):
        # Keep native layers and paint data rather than baking away editability.
        fields={'shader':'csgo_lightmappedgeneric.vfx','F_LAYERS':1,'F_FANCY_BLENDING':2 if props.get('$blendmodulatetexture') else 0,
                'TextureLayer1Color':color,'TextureLayer2Color':image(props['$basetexture2'],'_color2'),
                'TextureLayer1Roughness':'[0.7 0.7 0.7 0]','TextureLayer2Roughness':'[0.7 0.7 0.7 0]',
                'g_vColorTint':'[1 1 1 0]','g_vLayer1Tint':'[1 1 1 0]','g_vLayer2Tint':'[1 1 1 0]'}
        for source,target,suffix in (('$bumpmap','TextureLayer1Normal','_normal'),('$bumpmap2','TextureLayer2Normal','_normal2'),('$blendmodulatetexture','TextureBlendModulation','_blend')):
            if props.get(source):fields[target]=image(props[source],suffix)
        text='Layer0\n{\n'+''.join(' '+key+' '+(str(value) if isinstance(value,int) else json.dumps(value))+'\n' for key,value in fields.items())+'}\n'
        path=relative.with_suffix('.vmat');(root/path).write_text(text,encoding='utf-8')
        warnings.append(str(material['wl_texture'])+': converted to editable CS2 layers; review modulation, detail, roughness and surface-property parity in Hammer')
        return path.as_posix()
    text=mesh_assets.vmat(color,.7)
    if props.get('$bumpmap'):
        normal=image(props['$bumpmap'],'_normal')
        text=text.rsplit('}',1)[0]+' TextureNormal '+json.dumps(normal)+'\n}\n'
    if props.get('$translucent')=='1' or props.get('$alphatest')=='1':
        text=text.rsplit('}',1)[0]+(' F_ALPHA_TEST 1\n' if props.get('$alphatest')=='1' else ' F_TRANSLUCENT 1\n')+'}\n'
    path=relative.with_suffix('.vmat');(root/path).write_text(text,encoding='utf-8')
    warnings.append(material.name+': converted Source base color and bump texture; Source-specific shader effects need review in CS2 Hammer')
    return path.as_posix()


def convert_scene(context,root,selected=False,assign=True,source_directory='',use_loaded_textures=False):
    """Create new material datablocks; retain originals for undo/manual recovery."""
    import bpy
    root=Path(root).resolve();root.mkdir(parents=True,exist_ok=True)
    objects=[o for o in (context.selected_objects if selected else context.scene.objects) if o.type=='MESH']
    originals=list(dict.fromkeys(m for o in objects for m in o.data.materials if m and m.get('wl_texture') and not m.get('wl_source2_material')))
    converted={};warnings=[];failures=[]
    settings=SimpleNamespace(game_dir=source_directory or bpy.path.abspath(context.scene.wavelength.game_dir),source_override=bool(source_directory))
    wm=context.window_manager;wm.progress_begin(0,max(1,len(originals)))
    try:
        for i,original in enumerate(originals):
            try:
                path=deploy(original,settings,root,mesh_assets.slug(context.scene.wavelength.map_name),warnings,use_loaded_textures=use_loaded_textures)
                # Read generated images directly; no dependency on a switched
                # active CS2 profile or its private material-library cache.
                mat=bpy.data.materials.new(original.name+' · CS2');mat.use_nodes=True
                nodes=mat.node_tree.nodes;nodes.clear()
                shader=nodes.new('ShaderNodeBsdfPrincipled');output=nodes.new('ShaderNodeOutputMaterial')
                mat.node_tree.links.new(shader.outputs['BSDF'],output.inputs['Surface']);shader.inputs['Roughness'].default_value=.7
                for suffix in ('_color','_normal'):
                    image_path=(root/path).with_name(Path(path).stem+suffix+'.png')
                    if not image_path.is_file():continue
                    image=bpy.data.images.load(str(image_path),check_existing=True)
                    tex=nodes.new('ShaderNodeTexImage');tex.image=image
                    if suffix=='_normal':
                        image.colorspace_settings.name='Non-Color';normal=nodes.new('ShaderNodeNormalMap')
                        mat.node_tree.links.new(tex.outputs['Color'],normal.inputs['Color']);mat.node_tree.links.new(normal.outputs['Normal'],shader.inputs['Normal'])
                    else:mat.node_tree.links.new(tex.outputs['Color'],shader.inputs['Base Color'])
                mat['wl_source2_material']=path;mat['wl_source2_content_root']=str(root)
                mat['wl_texture']=path.removeprefix('materials/').removesuffix('.vmat');mat['wl_asset_profile']='source2_cs2_windows'
                mat['wl_source1_original']=original.name;mat.use_fake_user=True
                # Brush projection uses the original VTF pixel dimensions as
                # its unit basis, even if an exported image is a smaller preview.
                # Losing these makes the live UV handler fall back to 64x64.
                mat['wl_width']=original.get('wl_width',next((n.image.size[0] for n in nodes if n.type=='TEX_IMAGE' and n.image),64))
                mat['wl_height']=original.get('wl_height',next((n.image.size[1] for n in nodes if n.type=='TEX_IMAGE' and n.image),64))
                converted[original]=mat
            except (ValueError,OSError) as exc:failures.append(str(exc))
            wm.progress_update(i+1)
        if assign:
            for original in converted:original.use_fake_user=True
            for obj in objects:
                # A selection-only conversion must not rewrite shared mesh slots
                # on unselected objects.
                if selected and obj.data.users>1:obj.data=obj.data.copy()
                for slot in obj.material_slots:
                    if slot.material in converted:slot.material=converted[slot.material]
    finally:wm.progress_end()
    report=bpy.data.texts.get('wavelength CS2 Material Conversion') or bpy.data.texts.new('wavelength CS2 Material Conversion')
    report.clear();report.write('\n'.join([f'Converted {len(converted)} of {len(originals)} materials',f'Content root: {root}',*warnings,*failures]))
    return converted,failures


def repair_projection(context):
    """Recover dimensions from retained originals and refresh brush UVs."""
    import bpy
    from . import editor
    repaired=set()
    for obj in context.scene.objects:
        if obj.type!='MESH':continue
        changed=False
        for mat in obj.data.materials:
            if not mat or not mat.get('wl_source1_original'):continue
            original=bpy.data.materials.get(mat['wl_source1_original'])
            if original and original.get('wl_width') and original.get('wl_height'):
                mat['wl_width']=original['wl_width'];mat['wl_height']=original['wl_height']
                repaired.add(mat.name);changed=True
        if changed and obj.data.get('wl_faces') and obj.data.attributes.get('wl_face_id'):
            editor.apply_uv(obj,context.scene.wavelength.engine)
    return len(repaired)


def export_brush_projections(obj,mesh):
    """Keep Hammer's editable face projection consistent with world-inch UVs.

    UV corner streams alone do not describe the texture axes shown/used by
    Hammer's face tools. Source brush scales are in the authoring profile's
    units, while the VMAP mesh has already been converted to Source 2 inches.
    """
    records=json.loads(obj.data.get('wl_faces','{}'));ids=mesh.attributes.get('wl_face_id')
    if not records or ids is None:return None
    unit=float(obj.get('wl_unit_meters',.0254));result=[]
    for face in mesh.polygons:
        record=records.get(str(ids.data[face.index].value),{});axes=record.get('axes')
        if not axes:return None
        projection=record.get('projection',[0,0,0,1,1])
        result.append((tuple(projection[i]*unit/.0254 for i in (3,4)),tuple(axes[0]),tuple(axes[1])))
    return result


def recover_export_projection(obj,mesh,corners):
    """Repair legacy converted brush UVs in export memory, not the source scene."""
    import bpy
    records=json.loads(obj.data.get('wl_faces','{}'));ids=mesh.attributes.get('wl_face_id')
    if not records or ids is None:return
    for face in mesh.polygons:
        if face.material_index>=len(mesh.materials):continue
        material=mesh.materials[face.material_index]
        if not material or not material.get('wl_source1_original'):continue
        original=bpy.data.materials.get(material['wl_source1_original'])
        if not original or not original.get('wl_width') or not original.get('wl_height'):continue
        record=records.get(str(ids.data[face.index].value));axes=record.get('axes') if record else None
        if not axes:continue
        projection=record.get('projection',[0,0,0,1,1]);unit=float(obj.get('wl_unit_meters',.0254))
        dims=(original['wl_width'],original['wl_height'])
        values=[]
        for vertex in face.vertices:
            # mesh positions have already been baked into Source 2 inches.
            point=mesh.vertices[vertex].co*(.0254/unit)
            values.append(tuple((sum(axes[a][j]*point[j] for j in range(3))/projection[a+3]+axes[a][3])/dims[a] for a in range(2)))
        corners[face.index]=values
