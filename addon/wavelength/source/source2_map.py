"""Static editable Source 2 VMAP meshes with CS2 material references.

Transforms are baked in Source inches, Z-up. Entity metadata and model instances
are excluded. Binary DMX conversion is delegated to the installed CS2 tools.
"""
import math,os,tempfile
from pathlib import Path
from array import array
import bpy
from mathutils import Matrix,Euler,Vector
from . import source2_dmx as dmx,source2_assets,mesh_assets

def converter(settings):
    path=Path(bpy.path.abspath(settings.compiler_dir))/'dmxconvert.exe'
    if not path.is_file():raise ValueError('Configure the CS2 compiler directory containing dmxconvert.exe to read binary VMAP files')
    return path

def load(path,settings):
    data=Path(path).read_bytes()
    if len(data)>256*1024*1024:raise ValueError('VMAP exceeds 256 MiB')
    if b'encoding keyvalues2 ' in data[:100]:return dmx.loads(data.decode('utf-8-sig'))
    if b'encoding binary ' not in data[:100]:raise ValueError('Choose an editable .vmap, not compiled .vmap_c or a map VPK')
    with tempfile.TemporaryDirectory(prefix='wavelength-vmap-') as folder:
        output=Path(folder)/'map.vmap'
        source2_assets.run([converter(settings),'-i',Path(path).resolve(),'-o',output,'-oe','keyvalues2'])
        if not output.is_file():raise ValueError('CS2 DMX conversion did not produce a map')
        return dmx.loads(output.read_text(encoding='utf-8-sig'))

def node(kind,name,index,children=None):
    return dmx.element(kind,name=('string',name),nodeID=('int',index),referenceID=('uint64',0),children=('element_array',children or []),origin=('vector3',(0,0,0)),angles=('qangle',(0,0,0)),scales=('vector3',(1,1,1)))

def content_root(filepath):
    """Maps under a maps/ directory reference sibling content materials/."""
    path=Path(filepath).resolve()
    return next((p.parent for p in path.parents if p.name.lower()=='maps'),path.parent)

def export(context,filepath,selected=False):
    if context.mode!='OBJECT':raise ValueError('Leave Edit Mode before exporting VMAP')
    objects=mesh_assets.candidates(context,selected)
    if not objects:raise ValueError('No visible map meshes to export')
    path=Path(filepath).resolve();path.parent.mkdir(parents=True,exist_ok=True)
    assets_root=content_root(path)
    name=mesh_assets.slug(path.stem);materials={};warnings=[];children=[]
    def material(original):
        if original in materials:return materials[original]
        if original and original.get('wl_source2_material'):
            value=source2_assets.asset_path(original['wl_source2_material'])
            materials[original]=value;return value
        key=mesh_assets.token(original.name if original else 'default')
        relative='materials/wavelength/'+name+'/'+key+'.vmat';folder=assets_root/'materials/wavelength'/name;folder.mkdir(parents=True,exist_ok=True)
        image=mesh_assets._base_image(original) if original else None
        shader=mesh_assets._shader(original) if original else None
        color=tuple(shader.inputs['Base Color'].default_value) if shader else tuple(original.diffuse_color) if original else (.5,.5,.5,1)
        texture=folder/(key+'.png')
        copy=bpy.data.images.new('.wavelength VMAP texture',image.size[0] if image else 1,image.size[1] if image else 1,alpha=True,float_buffer=image.is_float if image else False)
        try:
            copy.colorspace_settings.name=image.colorspace_settings.name if image else 'sRGB'
            if image:
                pixels=array('f',[0])*(len(image.pixels));image.pixels.foreach_get(pixels);copy.pixels.foreach_set(pixels)
            else:copy.pixels[:]=color
            copy.filepath_raw=str(texture);copy.file_format='PNG';copy.update();copy.save()
        finally:bpy.data.images.remove(copy)
        (assets_root/relative).write_text(mesh_assets.vmat(texture.relative_to(assets_root).as_posix(),shader.inputs['Roughness'].default_value if shader else .5),encoding='utf-8')
        if shader and any(shader.inputs[k].is_linked for k in ('Normal','Metallic','Roughness','Alpha')):warnings.append((original.name if original else 'default')+': custom material exports base color and scalar roughness; native CS2 materials retain their complete engine shader')
        materials[original]=relative;return relative
    depsgraph=context.evaluated_depsgraph_get()
    for index,obj in enumerate(objects,2):
        if obj.get('wl_csg'):raise ValueError('Finalize or cancel live CSG before VMAP export')
        mesh=bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph),preserve_all_data_layers=True,depsgraph=depsgraph)
        try:
            matrix=Matrix.Scale(1/.0254,4)@obj.matrix_world;mesh.transform(matrix)
            if matrix.determinant()<0:mesh.flip_normals()
            verts=[tuple(v.co) for v in mesh.vertices]
            if any(not math.isfinite(c) for v in verts for c in v):raise ValueError('Nonfinite VMAP vertex')
            faces=[list(p.vertices) for p in mesh.polygons]
            if not faces:continue
            uv=mesh.uv_layers.active
            corners=[[(uv.data[i].uv.x,1-uv.data[i].uv.y) if uv else (0,0) for i in p.loop_indices] for p in mesh.polygons]
            slots=[material(m) for m in mesh.materials] or [material(None)]
            indices=[min(p.material_index,len(slots)-1) for p in mesh.polygons]
            child=node('CMapMesh',obj.name,index)
            child.put('meshData','CDmePolygonMesh',dmx.polygon_mesh(verts,faces,corners,slots,indices))
            for key in ('bakelighting','precomputelightprobes','renderToCubemaps'):child.put(key,'bool',True)
            child.put('tintColor','color',(255,255,255,255)).put('renderAmt','int',255).put('physicsType','string','default')
            children.append(child)
        finally:bpy.data.meshes.remove(mesh)
    world=node('CMapWorld','world',1,children)
    world.put('entity_properties','EditGameClassProps',dmx.element('EditGameClassProps',classname=('string','worldspawn')))
    world.put('nextDecalID','int',0).put('mapUsageType','string','standard').put('fixupEntityNames','bool',True)
    root=dmx.element('CMapRootElement',isprefab=('bool',False),editorbuild=('int',10000),editorversion=('int',400),showgrid=('bool',True),show3dgrid=('bool',True),gridspacing=('float',float(context.scene.wavelength.grid_step)),world=('CMapWorld',world))
    root.put('defaultcamera','CStoredCamera',dmx.element('CStoredCamera',position=('vector3',(128,-128,128)),lookat=('vector3',(0,0,0))))
    # Use the installed editor's versioned empty-map metadata when available.
    # This is not bundled game content: no meshes, entities or asset references
    # from the template survive in the exported world.
    game=Path(bpy.path.abspath(context.scene.wavelength.game_dir))
    template=game.parents[1]/'content/csgo/maps/editor/toolscene_default.vmap' if len(game.parents)>1 else None
    if template and template.is_file():
        scaffold=load(template,context.scene.wavelength)
        scaffold.put('world','CMapWorld',world).put('nodeInstanceData','element_array',[])
        scaffold.put('gridspacing','float',float(context.scene.wavelength.grid_step))
        visibility=scaffold.get('visbility')
        if visibility:
            visibility.put('nodes','element_array',[]).put('hiddenFlags','int_array',[])
        selection=scaffold.get('rootSelectionSet')
        if selection:
            for key,(typ,value) in list(selection.attrs.items()):
                if typ.endswith('_array'):selection.put(key,typ,[])
        root=scaffold
    else:raise ValueError('CS2 map export requires the installed content/csgo/maps/editor/toolscene_default.vmap scaffold and DMX tools; configure the CS2 Game Directory')
    temporary=path.with_suffix('.vmap.partial');temporary.write_text(dmx.dumps(root),encoding='utf-8');os.replace(temporary,path)
    return len(children),warnings

def import_map(context,filepath):
    root=load(filepath,context.scene.wavelength);world=root.get('world')
    if not isinstance(world,dmx.Element):raise ValueError('VMAP has no world')
    prepared=[];warnings=[];seen=set()
    def walk(obj,parent):
        if not isinstance(obj,dmx.Element) or id(obj) in seen:return
        seen.add(id(obj))
        origin=obj.get('origin',(0,0,0));angles=obj.get('angles',(0,0,0));scales=obj.get('scales',(1,1,1))
        # Source QAngle = pitch about Y, yaw about Z, roll about X.
        rotation=Euler(tuple(math.radians(v) for v in (angles[2],angles[0],angles[1])),'XYZ').to_matrix().to_4x4()
        transform=parent@Matrix.Translation(Vector(origin))@rotation@Matrix.Diagonal((*scales,1))
        if obj.kind=='CMapMesh':
            if not isinstance(obj.get('meshData'),dmx.Element):raise ValueError('VMAP mesh is missing meshData')
            geometry=dmx.read_mesh(obj.get('meshData'));prepared.append((obj,transform,geometry))
        elif obj.kind in {'CMapInstance','CMapPrefab'}:warnings.append('Prefab/instance references are not imported; resolve them to meshes in Hammer first')
        for child in obj.get('children',[]):walk(child,transform)
    walk(world,Matrix.Identity(4))
    if not prepared:raise ValueError('VMAP contains no editable map meshes; model instances and entities are outside this import scope')
    collection=bpy.data.collections.new(Path(filepath).stem);context.scene.collection.children.link(collection)
    created=[];cache={}
    try:
        for source,transform,(vertices,faces,uvs,names,indices) in prepared:
            if transform.determinant()<0:
                faces=[list(reversed(f)) for f in faces];uvs=[list(reversed(uv)) for uv in uvs]
            mesh=bpy.data.meshes.new(source.get('name','VMAP mesh'));created.append(mesh)
            mesh.from_pydata([tuple((transform@Vector(v))*.0254) for v in vertices],[],faces);mesh.update()
            obj=bpy.data.objects.new(source.get('name','VMAP mesh'),mesh);collection.objects.link(obj);obj['wl_role']='BRUSH';obj['wl_profile']='source2_cs2_windows'
            for name in names:
                canonical=source2_assets.asset_path(name).removesuffix('_c')
                if canonical not in cache:
                    try:cache[canonical]=source2_assets.material(context.scene.wavelength,canonical,content_root=content_root(filepath))
                    except (ValueError,OSError,RuntimeError) as exc:
                        mat=bpy.data.materials.new(canonical);mat['wl_source2_material']=canonical;mat['wl_texture']=canonical.removeprefix('materials/').removesuffix('.vmat');mat['wl_asset_profile']='source2_cs2_windows';cache[canonical]=mat
                        warnings.append(canonical+': '+str(exc))
                mesh.materials.append(cache[canonical])
            layer=mesh.uv_layers.new(name='wavelength')
            for face,coords,material_id in zip(mesh.polygons,uvs,indices):
                if material_id<0 or material_id>=len(names):raise ValueError('VMAP face has an invalid material index')
                face.material_index=material_id
                for loop,uv in zip(face.loop_indices,coords):layer.data[loop].uv=(uv[0],1-uv[1])
        return len(prepared),warnings
    except Exception:
        for obj in list(collection.objects):bpy.data.objects.remove(obj,do_unlink=True)
        bpy.data.collections.remove(collection)
        for mesh in created:
            if mesh.users==0:bpy.data.meshes.remove(mesh)
        raise
