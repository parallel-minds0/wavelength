"""Source render meshes for imported models and engine prop previews."""
import hashlib,json,math
from collections import OrderedDict
from pathlib import Path
import bpy
from bpy.props import StringProperty,IntProperty,EnumProperty
from bpy_extras.io_utils import ImportHelper
from . import profiles,source_assets,studio_model

_MODEL_ITEMS=[]
_DECODED=OrderedDict()
_MESHES={}


class WL_OT_add_source_model(bpy.types.Operator):
    bl_idname='wavelength.add_source_model';bl_label='Add Source Model';bl_options={'REGISTER','UNDO'}
    bl_property='model'
    model:EnumProperty(name='Model',items=lambda self,context:_MODEL_ITEMS)
    @classmethod
    def poll(cls,context):return context.mode=='OBJECT' and profiles.is_source(context.scene.wavelength.engine)
    def invoke(self,context,event):
        global _MODEL_ITEMS
        try:
            assets=source_assets.library(bpy.path.abspath(context.scene.wavelength.game_dir));names=set()
            for mount in assets.mounts:
                if isinstance(mount,source_assets.VPK):names.update(n for n in mount.entries if n.startswith('models/') and n.endswith('.mdl'))
                else:names.update(p.relative_to(mount).as_posix() for p in (mount/'models').rglob('*.mdl'))
            _MODEL_ITEMS=[(name,name.removeprefix('models/'),name) for name in sorted(names)]
            if not _MODEL_ITEMS:raise ValueError('No models found in the active game mounts')
        except (ValueError,OSError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        context.window_manager.invoke_search_popup(self);return {'RUNNING_MODAL'}
    def execute(self,context):
        from . import asset_browser,asset_index
        try:obj=asset_browser.place(context,asset_index.record(context.scene.wavelength.engine,self.model),context.scene.cursor.location)
        except (ValueError,OSError,RuntimeError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        for selected in context.selected_objects:selected.select_set(False)
        obj.select_set(True);context.view_layer.objects.active=obj
        warnings=next((c.data.get('wl_model_warnings','[]') for c in obj.children if c.type=='MESH'),'[]')
        if json.loads(warnings):self.report({'WARNING'},'Model imported; some materials could not be previewed')
        return {'FINISHED'}


def _valid_decoded(data):
    if not isinstance(data,dict) or not {'vertices','normals','uvs','faces','slots','materials','directories','static','checksum'}<=data.keys():return False
    try:
        count=len(data['vertices'])
        if not 0<count<=studio_model.LIMIT or len(data['faces'])>studio_model.LIMIT:return False
        for key,width in (('vertices',3),('normals',3),('uvs',2)):
            if len(data[key])!=count:return False
            if any(len(v)!=width or any(not isinstance(x,(int,float)) or not math.isfinite(x) for x in v) for v in data[key]):return False
        if len(data['slots'])!=len(data['faces']) or not data['materials']:return False
        if any(len(f)!=3 or any(not isinstance(v,int) or not 0<=v<count for v in f) for f in data['faces']):return False
        if any(not isinstance(s,int) or not 0<=s<len(data['materials']) for s in data['slots']):return False
        if any(not isinstance(v,str) for key in ('materials','directories') for v in data[key]):return False
        return isinstance(data['checksum'],int) and isinstance(data['static'],bool)
    except (TypeError,KeyError):return False


def decoded(settings,path,skin,body,assets,reader=None):
    """Read the decoded cache before touching VVD/VTX payloads."""
    from . import runtime_cache
    path=source_assets.asset_path(path)
    identity=None
    if reader is None:
        names=[path,path[:-4]+'.vvd',*(path[:-4]+x for x in ('.dx90.vtx','.dx80.vtx','.sw.vtx','.vtx'))]
        identity=runtime_cache.key(['source-model-1',str(assets.game),path,skin,body,[(n,assets.fingerprint(n)) for n in names]])
        data=_DECODED.get(identity)
        if data is None:
            payload=runtime_cache.read(identity)
            try:data=json.loads(payload) if payload else None
            except (ValueError,UnicodeError):data=None
            if not _valid_decoded(data):data=None
            if data is None:
                data=studio_model.load(assets,path,skin,body)
                runtime_cache.write(identity,json.dumps(data,separators=(',',':')).encode())
            _DECODED[identity]=data
        _DECODED.move_to_end(identity)
        while len(_DECODED)>24:_DECODED.popitem(last=False)
    else:data=studio_model.load(assets,path,skin,body)
    return identity,data


def mesh(settings,path,skin=0,body=0,reader=None):
    assets=reader or source_assets.library(bpy.path.abspath(settings.game_dir))
    from . import runtime_cache
    identity,data=decoded(settings,path,skin,body,assets,reader)
    unit=profiles.unit_meters(settings)
    key=runtime_cache.key([identity or str(bpy.path.abspath(settings.game_dir))+path+str((skin,body,data['checksum'])),unit])
    cached=_MESHES.get(key)
    if cached is not None:
        try:
            if cached.name not in bpy.data.meshes:cached=None
        except ReferenceError:cached=None
    if cached is None:cached=next((m for m in bpy.data.meshes if m.get('wl_source_model_key')==key),None)
    if cached and reader is None:
        deps=json.loads(cached.get('wl_source_model_dependencies','{}'))
        if deps and all(json.loads(json.dumps(assets.fingerprint(n)))==stamp for n,stamp in deps.items()):
            _MESHES[key]=cached;return cached,data
    dependencies={}

    result=bpy.data.meshes.new(Path(path).stem)
    try:
        result.from_pydata([tuple(c*unit for c in p) for p in data['vertices']],[],data['faces']);result.update()
        uv=result.uv_layers.new(name='UVMap')
        for loop in result.loops:uv.data[loop.index].uv=data['uvs'][loop.vertex_index]
        alias=result.uv_layers.new(name='wavelength')
        for loop in result.loops:alias.data[loop.index].uv=data['uvs'][loop.vertex_index]
        for polygon,slot in zip(result.polygons,data['slots']):polygon.material_index=slot;polygon.use_smooth=True
        result.normals_split_custom_set_from_vertices(data['normals'])
        warnings=[]
        for name in data['materials']:
            material=None
            for directory in [*data['directories'],'']:
                candidate=(directory.replace('\\','/').rstrip('/')+'/'+name).strip('/').lower()
                try:
                    vmt='materials/'+candidate.removeprefix('materials/').removesuffix('.vmt')+'.vmt'
                    if reader is None:dependencies[vmt]=assets.fingerprint(vmt)
                    props=assets.material(candidate)
                    material=source_assets.material(settings,candidate)
                    if reader is None:
                        dependencies.update(assets._vmt_cache[vmt][1])
                        for field in ('$basetexture','$basetexture2','%tooltexture'):
                            if props.get(field):
                                texture='materials/'+source_assets.asset_path(props[field]).removeprefix('materials/').removesuffix('.vtf')+'.vtf'
                                dependencies[texture]=assets.fingerprint(texture)
                    break
                except (ValueError,OSError) as exc:last=str(exc)
            if material is None:
                material=bpy.data.materials.new(name+' (unresolved)');material.diffuse_color=(.8,.1,.8,1)
                material['wl_model_material_error']=last;warnings.append(name+': '+last)
            result.materials.append(material)
        result['wl_source_model_key']=key;result['wl_model_warnings']=json.dumps(warnings)
        result['wl_source_model_dependencies']=json.dumps(dependencies);_MESHES[key]=result
        return result,data
    except Exception:
        bpy.data.meshes.remove(result);raise


def attach(context,entity,mesh,path):
    child=bpy.data.objects.new(Path(path).stem+' Ã‚Â· Model',mesh)
    (entity.users_collection[0] if entity.users_collection else context.collection).objects.link(child)
    child.parent=entity;child['wl_model_reference']=True;child['wl_exclude']=True;child['wl_role']='MODEL_REFERENCE'
    child['wl_source_model']=path;child.hide_select=False
    return child


class WL_OT_import_source_model(bpy.types.Operator,ImportHelper):
    bl_idname='wavelength.import_source_model';bl_label='Import Source Model (.mdl)';bl_options={'REGISTER','UNDO'}
    filename_ext='.mdl'
    filter_glob:StringProperty(default='*.mdl',options={'HIDDEN'})
    skin:IntProperty(name='Skin',default=0,min=0)
    body:IntProperty(name='Body',default=0,min=0)
    @classmethod
    def poll(cls,context):return context.mode=='OBJECT' and profiles.is_source(context.scene.wavelength.engine)
    def execute(self,context):
        from . import model_io
        try:model_io.import_asset(context,self.filepath,self.skin,self.body)
        except (ValueError,OSError,RuntimeError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        self.report({'INFO'},'Editable model imported; use Model Asset > Compile Model to Game')
        return {'FINISHED'}


def menu(self,context):
    if WL_OT_import_source_model.poll(context):self.layout.operator(WL_OT_import_source_model.bl_idname)


def add_menu(self,context):
    if WL_OT_add_source_model.poll(context):self.layout.operator(WL_OT_add_source_model.bl_idname,icon='MESH_MONKEY')


def register():
    from . import custom_models
    custom_models.register()
    from . import model_io
    model_io.register()
    bpy.utils.register_class(WL_OT_add_source_model);bpy.utils.register_class(WL_OT_import_source_model);bpy.types.VIEW3D_MT_add.append(add_menu)


def unregister():
    bpy.types.VIEW3D_MT_add.remove(add_menu);bpy.utils.unregister_class(WL_OT_import_source_model);bpy.utils.unregister_class(WL_OT_add_source_model)
    from . import custom_models
    from . import model_io
    model_io.unregister()
    custom_models.unregister()
