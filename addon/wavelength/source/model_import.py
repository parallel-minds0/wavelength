"""Source render meshes for imported models and engine prop previews."""
import hashlib,json
from pathlib import Path
import bpy
from bpy.props import StringProperty,IntProperty,EnumProperty
from bpy_extras.io_utils import ImportHelper
from . import profiles,source_assets,studio_model

_MODEL_ITEMS=[]


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


def mesh(settings,path,skin=0,body=0,reader=None):
    assets=reader or source_assets.library(bpy.path.abspath(settings.game_dir))
    data=studio_model.load(assets,path,skin,body)
    unit=profiles.unit_meters(settings)
    key=hashlib.sha256((str(bpy.path.abspath(settings.game_dir))+path+str((skin,body,unit,data['checksum']))).encode()).hexdigest()
    cached=next((m for m in bpy.data.meshes if m.get('wl_source_model_key')==key),None)
    if cached:return cached,data
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
                    assets.material(candidate)
                    material=source_assets.material(settings,candidate);break
                except (ValueError,OSError) as exc:last=str(exc)
            if material is None:
                material=bpy.data.materials.new(name+' (unresolved)');material.diffuse_color=(.8,.1,.8,1)
                material['wl_model_material_error']=last;warnings.append(name+': '+last)
            result.materials.append(material)
        result['wl_source_model_key']=key;result['wl_model_warnings']=json.dumps(warnings)
        return result,data
    except Exception:
        bpy.data.meshes.remove(result);raise


def attach(context,entity,mesh,path):
    child=bpy.data.objects.new(Path(path).stem+' · Model',mesh)
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
        try:
            path=Path(self.filepath).resolve();game=source_assets.library(bpy.path.abspath(context.scene.wavelength.game_dir))
            # Resolve peers beside the chosen file; materials still use the
            # active game's ordered mounts and VPKs.
            class Local:
                def read(self,name):
                    peer=path.with_name(Path(name).name)
                    if peer.stat().st_size>source_assets.LIMIT:raise ValueError('Model companion exceeds size limit')
                    return peer.read_bytes()
                def material(self,name):return game.material(name)
            marker='/models/';normalized=path.as_posix();at=normalized.lower().rfind(marker)
            modelpath=normalized[at+1:] if at>=0 else 'models/'+path.name
            data,_=mesh(context.scene.wavelength,modelpath,self.skin,self.body,Local())
            obj=bpy.data.objects.new(path.stem,data);context.collection.objects.link(obj);obj.location=context.scene.cursor.location
            obj['wl_source_model']=modelpath;obj['wl_exclude']=True;obj['wl_role']='MODEL_REFERENCE'
            obj['wl_owner_profile']=context.scene.wavelength.engine;obj['wl_unit_meters']=profiles.unit_meters(context.scene.wavelength)
            for selected in context.selected_objects:selected.select_set(False)
            obj.select_set(True);context.view_layer.objects.active=obj
        except (ValueError,OSError,RuntimeError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        self.report({'INFO'},'Imported reference-pose mesh; Source export still uses the original compiled model')
        return {'FINISHED'}


def menu(self,context):
    if WL_OT_import_source_model.poll(context):self.layout.operator(WL_OT_import_source_model.bl_idname)


def add_menu(self,context):
    if WL_OT_add_source_model.poll(context):self.layout.operator(WL_OT_add_source_model.bl_idname,icon='MESH_MONKEY')


def register():
    from . import custom_models
    custom_models.register()
    bpy.utils.register_class(WL_OT_add_source_model);bpy.utils.register_class(WL_OT_import_source_model);bpy.types.TOPBAR_MT_file_import.append(menu);bpy.types.VIEW3D_MT_add.append(add_menu)


def unregister():
    bpy.types.VIEW3D_MT_add.remove(add_menu);bpy.types.TOPBAR_MT_file_import.remove(menu);bpy.utils.unregister_class(WL_OT_import_source_model);bpy.utils.unregister_class(WL_OT_add_source_model)
    from . import custom_models
    custom_models.unregister()
