"""Common model asset lifecycle and UI; engines supply import/build adapters."""
import json,subprocess,tempfile
from pathlib import Path
import bpy
from bpy.props import StringProperty,IntProperty
from bpy_extras.io_utils import ImportHelper
from . import model_pipeline


def import_asset(context,filename,skin=0,body=0):
    settings=context.scene.wavelength;backend=model_pipeline.backend_for(settings.engine,filename)
    result=backend.import_model(context,filename,skin,body)
    asset=bpy.data.collections.new(Path(filename).stem+' · Model Asset')
    context.scene.collection.children.link(asset)
    asset['wl_model_backend']=backend.id;asset['wl_model_profile']=settings.engine
    asset['wl_model_game']=bpy.path.abspath(settings.game_dir);asset['wl_model_source']=str(Path(filename).resolve())
    asset['wl_model_warnings']=json.dumps(result.warnings);asset['wl_model_status']='Editable'
    for selected in context.selected_objects:selected.select_set(False)
    for obj in result.objects:
        for collection in list(obj.users_collection):collection.objects.unlink(obj)
        asset.objects.link(obj);obj['wl_exclude']=True;obj['wl_role']='MODEL_SOURCE'
        obj['wl_model_asset']=asset
        obj.select_set(True)
    if result.objects:context.view_layer.objects.active=result.objects[0]
    return asset


def asset_for_object(obj):
    if not obj:return None
    owner=obj.get('wl_custom_model_owner') or obj
    for asset in bpy.data.collections:
        if asset.get('wl_model_backend') and (obj.name in asset.objects or asset.get('wl_model_build_owner')==owner):return asset

def active_asset(context):return asset_for_object(context.object)

class WL_OT_import_model_asset(bpy.types.Operator,ImportHelper):
    bl_idname='wavelength.import_model_asset';bl_label='wavelength Model IO';bl_options={'REGISTER','UNDO'}
    filename_ext=''
    filter_glob:StringProperty(default='*',options={'HIDDEN'})
    skin:IntProperty(name='Skin',default=0,min=0)
    body:IntProperty(name='Body',default=0,min=0)
    @classmethod
    def poll(cls,context):return context.mode=='OBJECT' and bool(model_pipeline.extensions(context.scene.wavelength.engine))
    def invoke(self,context,event):
        if self.filepath:return self.execute(context)
        self.filter_glob=';'.join('*'+ext for ext in model_pipeline.extensions(context.scene.wavelength.engine))
        return ImportHelper.invoke(self,context,event)
    def execute(self,context):
        try:asset=import_asset(context,self.filepath,self.skin,self.body)
        except (ValueError,OSError,RuntimeError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        warnings=json.loads(asset['wl_model_warnings'])
        self.report({'WARNING'} if warnings else {'INFO'},'; '.join(warnings) if warnings else 'Editable model imported')
        return {'FINISHED'}

class _ModelBuildJob:
    _process=None;_timer=None;_log=None
    @classmethod
    def poll(cls,context):return context.mode=='OBJECT' and active_asset(context) is not None
    def execute(self,context):
        self._asset=asset_for_object(bpy.data.objects.get(self.source_name)) if self.source_name else active_asset(context)
        try:
            if self._asset is None:raise ValueError('Drop an editable model asset, not a prop instance')
            settings=context.scene.wavelength
            if settings.engine!=self._asset['wl_model_profile']:raise ValueError('Activate the model asset’s owning profile first')
            work=Path(bpy.path.abspath(settings.project_dir)) / '.wavelength' / 'model-builds'
            work.mkdir(parents=True,exist_ok=True)
            self._work=Path(tempfile.mkdtemp(prefix='build-',dir=work))
            self._job=model_pipeline.get(self._asset['wl_model_backend']).prepare(context,self._asset,self._work)
            self._commands=list(self._job.commands);self._index=0;self._process=None
            self._log=(self._work/'compiler.log').open('w',encoding='utf-8')
            self._asset['wl_model_status']='Compiling';self._asset['wl_model_log']=str(self._work/'compiler.log')
            self._timer=context.window_manager.event_timer_add(.1,window=context.window)
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        except (ValueError,OSError,RuntimeError) as exc:
            if self._log:self._log.close()
            self.report({'ERROR'},str(exc));return {'CANCELLED'}
    def _close(self,context):
        if self._timer:context.window_manager.event_timer_remove(self._timer);self._timer=None
        if self._log:self._log.close();self._log=None
    def modal(self,context,event):
        if event.type=='ESC':
            if self._process and self._process.poll() is None:self._process.kill();self._process.wait()
            self._asset['wl_model_status']='Cancelled';self._close(context);return {'CANCELLED'}
        if event.type!='TIMER':return {'PASS_THROUGH'}
        try:
            if self._process:
                code=self._process.poll()
                if code is None:return {'PASS_THROUGH'}
                self._process=None
                if code:raise ValueError('Model compiler failed; see '+self._asset['wl_model_log'])
            if self._index<len(self._commands):
                command=self._commands[self._index];self._index+=1
                self._process=subprocess.Popen(command,cwd=self._work,stdout=self._log,stderr=subprocess.STDOUT,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                return {'PASS_THROUGH'}
            output=self._job.finish();self._asset['wl_model_status']='Built: '+output
            self._close(context);self.report({'INFO'},'Model ready: '+output);return {'FINISHED'}
        except (ValueError,OSError,RuntimeError) as exc:
            self._asset['wl_model_status']='Failed: '+str(exc);self._close(context)
            self.report({'ERROR'},str(exc));return {'CANCELLED'}

class WL_OT_build_model_asset(_ModelBuildJob,bpy.types.Operator):
    bl_idname='wavelength.build_model_asset';bl_label='Compile Model to Game'
    bl_description='Compile this editable model and deploy to a new managed path in the active game'
    source_name:StringProperty(options={'HIDDEN'})

class WL_OT_publish_model_drop(_ModelBuildJob,bpy.types.Operator):
    bl_idname='wavelength.publish_model_drop';bl_label='Publish Edited Model to Game'
    source_name:StringProperty(options={'HIDDEN'})
    @classmethod
    def poll(cls,context):
        return (context.mode=='OBJECT' and context.area and context.area.type=='FILE_BROWSER'
                and context.area.ui_type=='ASSETS' and context.scene.wavelength.asset_browser_section=='MODELS')

class WL_FH_model_asset(bpy.types.FileHandler):
    bl_idname='WL_FH_model_asset';bl_label='Editable Game Model'
    bl_import_operator='wavelength.import_model_asset';bl_file_extensions=''
    @classmethod
    def poll_drop(cls,context):
        return (context.area and context.area.type=='VIEW_3D'
                and WL_OT_import_model_asset.poll(context))

class WL_PT_model_asset(bpy.types.Panel):
    bl_label='Model Asset';bl_space_type='PROPERTIES';bl_region_type='WINDOW';bl_context='object'
    @classmethod
    def poll(cls,context):return active_asset(context) is not None
    def draw(self,context):
        asset=active_asset(context);layout=self.layout
        layout.label(text='Backend: '+asset['wl_model_backend'])
        layout.label(text=Path(asset.get('wl_model_source',asset.name)).name)
        layout.label(text=asset.get('wl_model_status','Editable'))
        layout.operator('wavelength.build_model_asset',icon='EXPORT')
        if asset.get('wl_model_log'):layout.label(text='Compiler log: '+asset['wl_model_log'])

CLASSES=(WL_OT_import_model_asset,WL_OT_build_model_asset,WL_OT_publish_model_drop,WL_FH_model_asset,WL_PT_model_asset)
def menu(self,context):
    if WL_OT_import_model_asset.poll(context):self.layout.operator(WL_OT_import_model_asset.bl_idname)
def register():
    from .model_backend_source1 import Source1
    model_pipeline.register(Source1())
    WL_FH_model_asset.bl_file_extensions=';'.join(model_pipeline.all_extensions())
    for cls in CLASSES:bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_import.append(menu)
def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu)
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)
    model_pipeline.unregister('source1')
