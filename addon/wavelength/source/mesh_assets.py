"""Static mesh/texture handoff for mesh engines, isolated from BSP and entities.

Evaluate into a temporary scene, bake world transforms and normalize physical
units there. Never apply modifiers, rewrite shaders or change selection in the
authoring scene. Completed bundles contain only meshes, materials and images.
"""
import hashlib,json,math,os,re,shutil,tempfile
from array import array
from pathlib import Path
import bpy
from mathutils import Matrix
from . import profiles,context_policy

ENGINES={'godot4','source2_cs2_windows'}

def slug(name):
    return re.sub('[^a-z0-9_-]+','_',str(name).lower()).strip('_')[:64] or 'level'

def token(name):return slug(name)+'_'+hashlib.sha256(name.encode()).hexdigest()[:8]

def defaults(engine):
    if engine=='godot4':
        folder=Path.home()/'Applications/Godot'
        executable=next(iter(sorted(folder.glob('*console.exe'))),None)
        return {'game_executable':str(executable) if executable else ''}
    if engine=='source2_cs2_windows':
        root=Path(os.environ.get('PROGRAMFILES(X86)','C:/Program Files (x86)'))/'Steam/steamapps/common/Counter-Strike Global Offensive'
        game=root/'game/csgo';compiler=root/'game/bin/win64'
        return {'game_dir':str(game) if (game/'gameinfo.gi').is_file() else '',
                'compiler_dir':str(compiler) if (compiler/'resourcecompiler.exe').is_file() else ''}
    return {}

def candidates(context,selected=False):
    objects=context.selected_objects if selected else context.scene.objects
    result=[]
    for obj in objects:
        if obj.type!='MESH' or obj.get('wl_exclude') or obj.hide_render or obj.hide_get():continue
        if obj.get('wl_model_reference') or obj.get('wl_asset_template') or obj.get('wl_entity_browser_template'):continue
        if context_policy.role(obj,context.scene.wavelength.engine) in {'HELPER','LIBRARY'}:continue
        parent=obj;entity=False
        while parent:
            if parent.get('wl_role')=='ENTITY' or parent.get('wl_model_reference'):entity=True;break
            parent=parent.parent
        if entity:continue
        result.append(obj)
    return sorted(result,key=lambda o:o.name)

def _shader(material):
    if not material.use_nodes:return None
    output=next((n for n in material.node_tree.nodes if n.type=='OUTPUT_MATERIAL' and n.is_active_output),None)
    shader=output.inputs['Surface'].links[0].from_node if output and output.inputs['Surface'].is_linked else None
    if shader is None or shader.type!='BSDF_PRINCIPLED':raise ValueError(f'{material.name}: use a Principled BSDF material or bake the shader first')
    return shader

def _base_image(material):
    shader=_shader(material)
    if shader is None:return None
    socket=shader.inputs['Base Color']
    if not socket.is_linked:return None
    node=socket.links[0].from_node
    if node.type!='TEX_IMAGE' or node.image is None:raise ValueError(f'{material.name}: bake Base Color to an image before exporting')
    vector=node.inputs['Vector']
    if vector.is_linked and vector.links[0].from_node.type!='UVMAP':raise ValueError(f'{material.name}: bake texture coordinates to UVs before exporting')
    return node.image

def modeldoc(mesh_path,remaps):
    q=json.dumps
    pairs=',\n'.join('{ from = '+q(a)+' to = '+q(b)+' }' for a,b in remaps)
    return '''<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc36:version{972dada4-b828-45a4-bb93-7795cf0585da} -->
{ rootNode = { _class = "RootNode" children = [
{ _class = "RenderMeshList" children = [
{ _class = "RenderMeshFile" name = "mesh" filename = '''+q(mesh_path)+''' import_scale = 1.0
import_filter = { exclude_by_default = false exception_list = [] } }
] },
{ _class = "MaterialGroupList" children = [
{ _class = "DefaultMaterialGroup" remaps = [ '''+pairs+''' ] }
] }
] model_archetype = "" primary_associated_entity = "" anim_graph_name = "" document_sub_type = "ModelDocSubType_None" } }
'''

def vmat(color_path,roughness,color=(1,1,1,1)):
    return 'Layer0\n{\n shader "csgo_complex.vfx"\n TextureColor '+json.dumps(color_path)+'\n TextureRoughness '+json.dumps(f'[{roughness:.6f} {roughness:.6f} {roughness:.6f} 0.000000]')+'\n g_vColorTint "['+' '.join(f'{v:.6f}' for v in color[:3])+' 0.000000]"\n}\n'

def export(context,directory,selected=False,*,engine=None,name=None):
    settings=context.scene.wavelength;engine=engine or settings.engine
    if engine not in ENGINES:raise ValueError('Choose Godot 4 or Counter-Strike 2 for mesh asset export')
    if context.mode!='OBJECT':raise ValueError('Leave Edit Mode before exporting meshes')
    objects=candidates(context,selected)
    if not objects:raise ValueError('No visible mesh content to export')
    if any(o.get('wl_csg') for o in objects):raise ValueError('Finalize or cancel live CSG before exporting')
    if not str(directory).strip():raise ValueError('Choose an Export Directory')
    name=slug(name or settings.map_name);root=Path(bpy.path.abspath(directory)).resolve();destination=root/name
    root.mkdir(parents=True,exist_ok=True)
    if destination.exists() and not (destination/'wavelength-export.json').is_file():raise ValueError(f'{destination} already exists without a wavelength export manifest; choose another name or directory')
    stage=Path(tempfile.mkdtemp(prefix='.wavelength-export-',dir=str(root)))
    temporary=bpy.data.scenes.new('.wavelength mesh export');meshes=[];materials=[];images=[];clones=[];warnings=[]
    material_map={};image_map={};remaps=[];object_records=[]
    source2=engine=='source2_cs2_windows';unit=.0254 if source2 else 1.
    window=context.window;original_scene=window.scene if window else None
    textures_folder=stage/('materials/wavelength/'+name if source2 else 'textures');textures_folder.mkdir(parents=True)
    def image_copy(image):
        if image in image_map:return image_map[image]
        if image.source not in {'FILE','GENERATED'} or image.size[0]<=0:raise ValueError(f'{image.name}: load or bake the image before exporting')
        # Image.copy duplicates ID settings, not necessarily edited/generated
        # pixels. A fresh buffer also avoids sharing the source's packed data.
        width,height=image.size
        copy=bpy.data.images.new('.wavelength export '+image.name,width,height,alpha=True,float_buffer=image.is_float);images.append(copy)
        copy.colorspace_settings.name=image.colorspace_settings.name;copy.alpha_mode=image.alpha_mode
        pixels=array('f',[0.])*(width*height*4);image.pixels.foreach_get(pixels);copy.pixels.foreach_set(pixels);copy.update()
        path=textures_folder/(token(image.name)+'.png');copy.filepath_raw=str(path);copy.file_format='PNG';copy.save()
        copy.source='FILE';image_map[image]=(copy,path);return copy,path
    def material_copy(original):
        if original in material_map:return material_map[original]
        image=_base_image(original);shader=_shader(original)
        if original.get('wl_texture') and image is None:raise ValueError(f'{original.name}: load the texture pixels before exporting')
        material=original.copy();material.name='wl_'+token(original.name);materials.append(material);material_map[original]=material
        if material.use_nodes:
            for node in material.node_tree.nodes:
                if node.type=='TEX_IMAGE' and node.image:node.image=image_copy(node.image)[0]
        if source2:
            key=token(original.name);relative='materials/wavelength/'+name+'/'+key+'.vmat'
            color=tuple(shader.inputs['Base Color'].default_value) if shader else tuple(original.diffuse_color)
            if image is not None:
                path=image_copy(image)[1];color=(1,1,1,1)
            else:
                solid=bpy.data.images.new('.wavelength solid color',1,1,alpha=True);images.append(solid)
                solid.pixels[:]=color;solid.update();solid.colorspace_settings.name='sRGB'
                path=textures_folder/(key+'_color.png');solid.filepath_raw=str(path);solid.file_format='PNG';solid.save()
                color=(1,1,1,1)
            roughness=shader.inputs['Roughness'].default_value if shader else .5
            (stage/relative).write_text(vmat(path.relative_to(stage).as_posix(),roughness,color),encoding='utf-8')
            remaps.append((material.name,relative))
            if shader and (shader.inputs['Normal'].is_linked or shader.inputs['Roughness'].is_linked or shader.inputs['Metallic'].is_linked or shader.inputs['Metallic'].default_value>0 or shader.inputs['Alpha'].is_linked or shader.inputs['Alpha'].default_value<1):warnings.append(original.name+': CS2 first-pass conversion exports base color and scalar roughness only')
        return material
    try:
        depsgraph=context.evaluated_depsgraph_get()
        for obj in objects:
            mesh=bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph),preserve_all_data_layers=True,depsgraph=depsgraph);meshes.append(mesh)
            if not mesh.polygons:raise ValueError(f'{obj.name}: evaluated mesh has no faces')
            matrix=Matrix.Scale(1/unit,4)@obj.matrix_world
            mesh.transform(matrix)
            if matrix.determinant()<0:mesh.flip_normals()
            if any(not math.isfinite(c) for v in mesh.vertices for c in v.co):raise ValueError(f'{obj.name}: mesh has nonfinite coordinates')
            slots=list(mesh.materials) or [None];mesh.materials.clear()
            for original in slots:
                if original is None:
                    original=bpy.data.materials.new('.wavelength default');materials.append(original)
                mesh.materials.append(material_copy(original))
            if any(_base_image(m) is not None for m in slots if m) and not mesh.uv_layers:raise ValueError(f'{obj.name}: textured mesh requires UV coordinates')
            clone=bpy.data.objects.new(obj.name,mesh);temporary.collection.objects.link(clone);clones.append(clone)
            object_records.append({'name':obj.name,'vertices':len(mesh.vertices),'polygons':len(mesh.polygons)})
        # Exporters call frame_set and evaluate through bpy.context internally.
        # Keep the real window scene consistent with the temporary context.
        if window:window.scene=temporary
        with context.temp_override(scene=temporary,view_layer=temporary.view_layers[0]):
            if source2:
                model_folder=stage/'models/wavelength'/name;model_folder.mkdir(parents=True)
                mesh_path=model_folder/(name+'.fbx')
                result=bpy.ops.export_scene.fbx(filepath=str(mesh_path),use_selection=False,object_types={'MESH'},use_mesh_modifiers=False,
                    # Blender's FBX writer includes a centimetre conversion even
                    # with apply_unit_scale disabled. Compensate it so ModelDoc
                    # import_scale=1 produces Source units, not 100x geometry.
                    bake_anim=False,axis_forward='Y',axis_up='Z',apply_unit_scale=False,global_scale=.01,path_mode='RELATIVE',embed_textures=False,use_triangles=True)
                primary=model_folder/(name+'.vmdl');primary.write_text(modeldoc(mesh_path.relative_to(stage).as_posix(),remaps),encoding='utf-8')
            else:
                primary=stage/(name+'.glb')
                result=bpy.ops.export_scene.gltf(filepath=str(primary),export_format='GLB',use_selection=False,use_active_scene=True,export_animations=False,export_extras=False,export_cameras=False,export_lights=False,export_yup=True)
            if result!={'FINISHED'}:raise ValueError('Blender mesh exporter did not finish')
        files=sorted(p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_file())
        manifest={'schema':1,'engine':engine,'scope':'selected' if selected else 'visible_scene','entities':False,
                  'meters_per_unit':unit,'up_axis':'Z' if source2 else 'Y','primary':primary.relative_to(stage).as_posix(),
                  'objects':object_records,'files':files,'warnings':warnings}
        (stage/'wavelength-export.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        # Prepare all assets before overwriting generated files. Leave unrelated
        # files and prior unused assets intact; the manifest lists the current set.
        destination.mkdir(exist_ok=True)
        for path in stage.rglob('*'):
            if path.is_file():
                output=destination/path.relative_to(stage);output.parent.mkdir(parents=True,exist_ok=True);os.replace(path,output)
        return destination/manifest['primary'],manifest
    finally:
        if window and original_scene:window.scene=original_scene
        for clone in clones:bpy.data.objects.remove(clone,do_unlink=True)
        bpy.data.scenes.remove(temporary)
        for mesh in meshes:
            if mesh.users==0:bpy.data.meshes.remove(mesh)
        for material in reversed(materials):
            if material.users==0:bpy.data.materials.remove(material)
        for image in images:
            if image.users==0:bpy.data.images.remove(image)
        # Only remove the exact temporary directory created above.
        if stage.parent==root and stage.name.startswith('.wavelength-export-'):shutil.rmtree(stage)

class WL_OT_export_mesh_assets(bpy.types.Operator):
    bl_idname='wavelength.export_mesh_assets';bl_label='Export Meshes & Textures'
    @classmethod
    def poll(cls,context):return context_policy.allows(context,'export') and context.scene.wavelength.engine in ENGINES
    def invoke(self,context,event):return context.window_manager.invoke_props_dialog(self,width=520)
    def draw(self,context):
        layout=self.layout;settings=context.scene.wavelength
        layout.prop(settings,'mesh_export_directory');layout.prop(settings,'map_name');layout.prop(settings,'mesh_export_selected')
        layout.label(text='Static meshes and textures; no entities or collision')
    def execute(self,context):
        settings=context.scene.wavelength
        try:
            path,manifest=export(context,settings.mesh_export_directory,settings.mesh_export_selected)
            settings.status=f'Exported {len(manifest["objects"])} meshes: {path}'
            self.report({'WARNING'} if manifest['warnings'] else {'INFO'},settings.status+('; '+manifest['warnings'][0] if manifest['warnings'] else ''))
        except (ValueError,OSError,RuntimeError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        return {'FINISHED'}

class WL_OT_source2_library(bpy.types.Operator):
    bl_idname='wavelength.source2_library';bl_label='CS2 Material Preparation'
    action:bpy.props.EnumProperty(items=[('START','Start / Resume','Build cached CS2 material thumbnails in the background'),('PAUSE','Pause','Stop preparation and retain cached materials')])
    @classmethod
    def poll(cls,context):return profiles.is_source2(context.scene.wavelength.engine)
    def execute(self,context):
        from . import external_library
        key,_=external_library.cache_root(external_library.snapshot(context.scene.wavelength))
        if self.action=='PAUSE':
            external_library._paused.add(key);external_library.stop();external_library._status['state']='PAUSED'
        else:
            if not context_policy.preparation_active(context.scene):self.report({'ERROR'},'Enable Asset Preparation in the wavelength workspace');return {'CANCELLED'}
            external_library._paused.discard(key);external_library.schedule(context,force=True)
        return {'FINISHED'}

class WL_PT_mesh_assets(bpy.types.Panel):
    bl_label='Meshes & Textures';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='wavelength'
    @classmethod
    def poll(cls,context):return context_policy.allows(context,'editing') and context.scene.wavelength.engine in ENGINES
    def draw(self,context):
        settings=context.scene.wavelength;layout=self.layout
        if profiles.is_source2(settings.engine):
            layout.operator('wavelength.export_map',text='Export Source 2 Map',icon='EXPORT')
            layout.operator('wavelength.entity_browser',text='Browse CS2 Materials',icon='MATERIAL').section='TEXTURES'
            layout.label(text='Editable VMAP meshes and per-face CS2 materials')
            from . import external_library
            layout.label(text=external_library.label())
            row=layout.row(align=True)
            row.operator('wavelength.source2_library',text='Start / Resume').action='START'
            row.operator('wavelength.source2_library',text='Pause').action='PAUSE'
            return
        layout.label(text='GLB · Godot 4' if settings.engine=='godot4' else 'FBX + VMAT + ModelDoc · CS2')
        layout.prop(settings,'mesh_export_directory');layout.prop(settings,'mesh_export_selected')
        layout.operator('wavelength.export_mesh_assets',icon='EXPORT')
        layout.label(text='No entities, collision or map compilation')

CLASSES=(WL_OT_export_mesh_assets,WL_OT_source2_library,WL_PT_mesh_assets)
def register():
    for cls in CLASSES:bpy.utils.register_class(cls)
def unregister():
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)
