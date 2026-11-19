"""Common model asset lifecycle and UI; engines supply import/build adapters."""
import json,os,subprocess,tempfile
from pathlib import Path
import bpy
from bpy.props import StringProperty,IntProperty,BoolProperty,EnumProperty
from bpy_extras.io_utils import ImportHelper,ExportHelper
from . import model_pipeline


def import_asset(context,filename,skin=0,body=0):
    if Path(filename).suffix.lower()=='.wlmodel':
        from .model_bundle import import_asset as load_package
        return load_package(context,filename)
    settings=context.scene.wavelength;backend=model_pipeline.backend_for(settings.engine,filename)
    result=backend.import_model(context,filename,skin,body)
    from . import model_lifecycle
    asset=model_lifecycle._adopt(context,result.objects,Path(filename).stem,backend.id,str(Path(filename).resolve()),result.warnings)
    model_lifecycle.select_sources(context,asset)
    return asset


def asset_for_object(obj):
    if not obj:return None
    from . import model_lifecycle
    asset=model_lifecycle.asset_for(obj)
    if asset:return asset
    owner=obj.get('wl_custom_model_owner') or obj
    for asset in bpy.data.collections:
        if asset.get('wl_model_backend') and (obj.name in asset.objects or asset.get('wl_model_build_owner')==owner):return asset

def active_asset(context):return asset_for_object(context.object)


def selected_assets(context):
    from .model_lifecycle import entity_for
    entity=entity_for(context.object)
    result={asset_for_object(o) for o in context.selected_objects if o!=entity and not o.get('wl_model_reference')}
    result.discard(None)
    return result

class WL_OT_import_model_asset(bpy.types.Operator,ImportHelper):
    bl_idname='wavelength.import_model_asset';bl_label='wavelength Model IO';bl_options={'REGISTER','UNDO'}
    filename_ext=''
    filter_glob:StringProperty(default='*',options={'HIDDEN'})
    skin:IntProperty(name='Skin',default=0,min=0)
    body:IntProperty(name='Body',default=0,min=0)
    @classmethod
    def poll(cls,context):return context.mode=='OBJECT'
    def invoke(self,context,event):
        if self.filepath:return self.execute(context)
        self.filter_glob=';'.join('*'+ext for ext in (*model_pipeline.extensions(context.scene.wavelength.engine),'.wlmodel'))
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
            from .model_lifecycle import ensure
            ensure(context,self._asset)
            settings=context.scene.wavelength
            work=Path(bpy.path.abspath(settings.project_dir)) / '.wavelength' / 'model-builds'
            staging=Path(tempfile.gettempdir())/'wl-models' if os.name=='nt' else work
            staging.mkdir(parents=True,exist_ok=True)
            self._work=Path(tempfile.mkdtemp(prefix='build-',dir=staging))
            from . import model_transfer
            target=getattr(self,'target_profile','') or self._asset['wl_model_profile']
            output=getattr(self,'output_directory','') or str(work/self._work.name/'output')
            if self._asset['wl_model_backend']!='source1' and not getattr(self,'target_profile',''):
                self._job=model_pipeline.get(self._asset['wl_model_backend']).prepare(context,self._asset,self._work)
            else:
                self._job=model_transfer.prepare(context,self._asset,self._work,target,bpy.path.abspath(output),
                    publish=getattr(self,'deploy',True),package=getattr(self,'portable',False),allow_lossy=getattr(self,'allow_lossy',False),
                    game=getattr(self,'game_directory',''),compiler=getattr(self,'compiler_directory',''),addon=getattr(self,'target_addon',''),model_name=getattr(self,'model_name','') or 'model')
            self._commands=list(self._job.commands);self._index=0;self._process=None
            self._log=(self._work/'compiler.log').open('w',encoding='utf-8')
            self._asset['wl_model_status']='Compiling';self._asset['wl_model_log']=str(self._work/'compiler.log')
            self._timer=context.window_manager.event_timer_add(.1,window=context.window)
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        except (ValueError,OSError,RuntimeError) as exc:
            self._close(context)
            self.report({'ERROR'},str(exc));return {'CANCELLED'}
    def _close(self,context):
        if self._timer:context.window_manager.event_timer_remove(self._timer);self._timer=None
        if self._log:self._log.close();self._log=None
        if getattr(self,'_job',None) and hasattr(self._job,'close'):self._job.close();self._job=None
        context.window_manager.progress_end()
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
                context.window_manager.progress_begin(0,max(1,len(self._commands)));context.window_manager.progress_update(self._index)
                self._asset['wl_model_status']='Compiling target resources '+str(self._index+1)+'/'+str(len(self._commands))
                command=self._commands[self._index];self._index+=1
                self._process=subprocess.Popen(command,cwd=self._work,stdout=self._log,stderr=subprocess.STDOUT,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                return {'PASS_THROUGH'}
            output=self._job.finish();self._asset['wl_model_status']='Built: '+output
            if hasattr(self,'target_profile'):
                self._asset['wl_model_publish_settings']=json.dumps({
                    key:getattr(self,key) for key in PUBLISH_FIELDS})
            self._close(context);self.report({'INFO'},'Model ready: '+output);return {'FINISHED'}
        except (ValueError,OSError,RuntimeError) as exc:
            self._asset['wl_model_status']='Failed: '+str(exc);self._close(context)
            self.report({'ERROR'},str(exc));return {'CANCELLED'}

class WL_OT_build_model_asset(_ModelBuildJob,bpy.types.Operator):
    bl_idname='wavelength.build_model_asset';bl_label='Compile Model to Game'
    bl_description='Compile this editable model and deploy to a new managed path in the active game'
    source_name:StringProperty(options={'HIDDEN'})
    def invoke(self,context,event):
        return bpy.ops.wavelength.convert_model_asset('INVOKE_DEFAULT',source_name=self.source_name,deploy=True)

class WL_OT_publish_model_drop(_ModelBuildJob,bpy.types.Operator):
    bl_idname='wavelength.publish_model_drop';bl_label='Publish Edited Model to Game'
    source_name:StringProperty(options={'HIDDEN'})
    @classmethod
    def poll(cls,context):
        return (context.mode=='OBJECT' and context.area and context.area.type=='FILE_BROWSER'
                and context.area.ui_type=='ASSETS' and context.scene.wavelength.asset_browser_section=='MODELS')


def _targets(self,context):
    from .profile_ui import items
    return items(self,context)


def _default_target(context, asset):
    from . import profiles
    rows = _targets(None, context)
    choices = {row[0] for row in rows}
    source = asset.get('wl_model_profile')
    if source in choices:
        return source
    if source in profiles.PROFILES:
        label = profiles.get(source)['label']
        for identity, display, *_ in rows:
            if display == label:
                return identity
    settings = context.scene.wavelength
    return next((identity for identity in (settings.profile_id, settings.engine) if identity in choices), None)


PUBLISH_FIELDS=('model_name','target_profile','game_directory','compiler_directory',
                'output_directory','target_addon','deploy','portable','allow_lossy')


class WL_OT_convert_model_asset(_ModelBuildJob,bpy.types.Operator):
    bl_idname='wavelength.convert_model_asset';bl_label='Publish Model'
    bl_description='Build an independent target handoff without switching the authoring profile'
    source_name:StringProperty(options={'HIDDEN'})
    target_profile:EnumProperty(name='Target Profile',items=_targets)
    game_directory:StringProperty(name='Target Game Directory',subtype='DIR_PATH')
    compiler_directory:StringProperty(name='Target Compiler Directory',subtype='DIR_PATH')
    output_directory:StringProperty(name='Output Directory',subtype='DIR_PATH')
    target_addon:StringProperty(name='CS2 Target Addon')
    deploy:BoolProperty(name='Deploy to Game',default=False)
    model_name:StringProperty(name='Model Name',description='File name without extension. Up to 32 letters, digits, underscores or hyphens')
    portable:BoolProperty(name='Include Editable Package (.wlmodel)',default=False)
    allow_lossy:BoolProperty(name='Allow Static/Approximate Conversion',description='Accept only explicitly reported animation, collision or shader omissions',default=False)
    def invoke(self,context,event):
        explicit={key for key in PUBLISH_FIELDS if self.properties.is_property_set(key)}
        asset=asset_for_object(bpy.data.objects.get(self.source_name)) if self.source_name else active_asset(context)
        if asset is None:
            self.report({'ERROR'},'Select an editable model asset')
            return {'CANCELLED'}
        from .model_lifecycle import ensure
        ensure(context,asset)
        self.source_name=next((obj.name for obj in asset.objects if obj.type=='MESH'),self.source_name)
        from .mesh_assets import slug
        if 'model_name' not in explicit:self.model_name=slug(asset.name)[:32]
        target = _default_target(context, asset)
        if target is not None and 'target_profile' not in explicit:
            self.target_profile = target
        if 'output_directory' not in explicit:
            self.output_directory=str(Path(bpy.path.abspath(context.scene.wavelength.project_dir))/'model-exports'/asset['wl_model_id'])
        saved=json.loads(asset.get('wl_model_publish_settings','{}'))
        choices={row[0] for row in _targets(self,context)}
        for key in PUBLISH_FIELDS:
            if key not in saved or key=='target_profile' and saved[key] not in choices:continue
            if key not in explicit:setattr(self,key,saved[key])
        return context.window_manager.invoke_props_dialog(self,width=520)
    def draw(self,context):
        for key in ('model_name','target_profile','output_directory','deploy','target_addon','portable','allow_lossy','game_directory','compiler_directory'):self.layout.prop(self,key)
        self.layout.label(text='Blank paths use the selected profile. Unsupported routes report an error.')


class WL_OT_package_model_asset(bpy.types.Operator,ExportHelper):
    bl_idname='wavelength.package_model_asset';bl_label='Export Editable Model Package'
    filename_ext='.wlmodel';filter_glob:StringProperty(default='*.wlmodel',options={'HIDDEN'})
    @classmethod
    def poll(cls,context):return context.mode=='OBJECT' and active_asset(context) is not None
    def execute(self,context):
        from .model_transfer import export_package
        try:export_package(context,active_asset(context),self.filepath)
        except (ValueError,OSError,RuntimeError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        self.report({'INFO'},'Editable model and owned dependencies packaged');return {'FINISHED'}


class WL_OT_asset_clip(bpy.types.Operator):
    bl_idname='wavelength.model_asset_clip';bl_label='Model Animation Clip';bl_options={'REGISTER','UNDO'}
    remove:IntProperty(default=-1)
    def execute(self,context):
        asset=active_asset(context)
        if not asset:return {'CANCELLED'}
        clips=asset.wavelength_model.clips
        if self.remove>=0:clips.remove(self.remove)
        else:
            clip=clips.add();clip.name='animation_'+str(len(clips));clip.start=context.scene.frame_start;clip.end=context.scene.frame_end;clip.fps=context.scene.render.fps/context.scene.render.fps_base
        return {'FINISHED'}

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
    def poll(cls,context):
        from .model_lifecycle import entity_for
        entity=entity_for(context.object)
        return active_asset(context) is not None or bool(selected_assets(context)) or bool(entity and dict(json.loads(entity.get('wl_pairs','[]'))).get('model') and model_pipeline.extensions(context.scene.wavelength.engine))
    def draw(self,context):
        asset=active_asset(context);layout=self.layout
        selected=selected_assets(context)
        if asset is None and len(selected)==1:asset=next(iter(selected))
        if asset is None:
            layout.operator('wavelength.edit_model',text='Edit Shared Model',icon='EDITMODE_HLT');return
        from .model_lifecycle import bindings, sources
        placements=bindings(asset)
        layout.label(text=asset.name)
        layout.label(text=f'{len(placements)} linked placements')
        if len(placements)>1:
            layout.label(text='Shared edits update every linked placement',icon='LINKED')
        layout.operator('wavelength.select_model_sources',text='Select All Source Parts')
        layout.operator('wavelength.model_origin')
        from .export_scope import Scope
        scope=Scope(context.scene,context.view_layer)
        parts=layout.box()
        parts.label(text='Source Parts')
        for source in sources(asset):
            row=parts.row(align=True)
            row.operator('wavelength.select_model_sources',text=source.name,icon='OUTLINER_OB_MESH' if source.type=='MESH' else 'OBJECT_DATA').source_name=source.name
            from . import export_scope
            export_scope.draw(row,scope,[source],object_name=source.name)
            row.operator('wavelength.model_part',text='',icon='X').source_name=source.name
        parts.operator('wavelength.model_part',text='Add Selected Parts')
        layout.label(text='Backend: '+asset.get('wl_model_backend','source1'))
        layout.label(text=Path(asset.get('wl_model_source',asset.name)).name)
        layout.label(text=asset.get('wl_model_status','Editable'))
        layout.operator('wavelength.edit_model',icon='EDITMODE_HLT')
        layout.operator('wavelength.make_model_unique',icon='DUPLICATE')
        from .model_lifecycle import entity_for
        entity=entity_for(context.object)
        if entity and entity.get('wl_custom_model'):layout.operator('wavelength.detach_model_asset',icon='UNLINKED')
        layout.operator('wavelength.attach_model_asset',icon='LINKED')
        if entity:layout.label(text='Destination: '+entity.name)
        else:layout.label(text='Attach: select sources, then the destination entity')
        layout.operator('wavelength.convert_model_asset',text='Publish Model',icon='EXPORT')
        layout.operator('wavelength.package_model_asset',icon='PACKAGE')
        if not entity:
            state=asset.wavelength_model;layout.prop(state,'collision_mode')
            if state.collision_mode=='OBJECT':layout.prop(state,'collision')
            if state.collision_mode!='NONE':layout.prop(state,'mass')
            layout.prop(state,'surface_prop')
            for index,clip in enumerate(state.clips):
                box=layout.box();row=box.row();row.prop(clip,'name');row.operator('wavelength.model_asset_clip',text='',icon='X').remove=index
                row=box.row();row.prop(clip,'start');row.prop(clip,'end');box.prop(clip,'fps');box.prop(clip,'loop')
            layout.operator('wavelength.model_asset_clip',text='Add Animation Clip',icon='ADD')
        row=layout.row(align=True)
        row.operator('wavelength.model_collision_preview',text='Preview / Refresh Collision')
        row.operator('wavelength.model_collision_preview',text='Clear Preview').clear=True
        from . import model_revisions
        revisions=layout.box()
        revisions.label(text='Revisions')
        revisions.operator('wavelength.model_revision',text='Save Named Revision')
        for revision in reversed(model_revisions.records(asset)):
            row=revisions.row(align=True)
            row.label(text=revision['name'])
            row.operator('wavelength.model_revision',text='Open as Variant').revision_id=revision['id']
            if entity and entity.get('wl_custom_model')==asset:
                action=row.operator('wavelength.model_revision',text='Restore Placement')
                action.revision_id=revision['id']
                action.restore=True
        if asset.get('wl_model_log'):layout.label(text='Compiler log: '+asset['wl_model_log'])

class _ModelEditAction:
    bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context):return context.mode=='OBJECT' and context.object is not None
    def execute(self,context):
        try:self.run(context)
        except (ValueError,OSError,RuntimeError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        return {'FINISHED'}


class WL_OT_model_origin(_ModelEditAction,bpy.types.Operator):
    bl_idname='wavelength.model_origin'
    bl_label='Model Origin to 3D Cursor'
    bl_description='Move the shared model pivot to the cursor while preserving visible geometry at all placements'

    def run(self,context):
        from . import model_lifecycle
        asset=active_asset(context)
        if not asset:raise ValueError('Select an editable model asset')
        model_lifecycle.set_origin(context,asset,context.scene.cursor.location.copy())


class WL_OT_model_part(_ModelEditAction,bpy.types.Operator):
    bl_idname='wavelength.model_part'
    bl_label='Manage Model Parts'
    source_name:StringProperty(options={'HIDDEN'})

    def run(self,context):
        from . import model_lifecycle
        assets=selected_assets(context)
        asset=active_asset(context)
        if asset is None and len(assets)==1:asset=next(iter(assets))
        if asset is None:raise ValueError('Select the destination model asset together with its new parts')
        if self.source_name:
            source=asset.objects.get(self.source_name)
            model_lifecycle.remove_source(context,asset,source)
            model_lifecycle.select_sources(context,asset)
        else:
            model_lifecycle.add_sources(context,asset,context.selected_objects)


class WL_OT_model_revision(_ModelEditAction,bpy.types.Operator):
    bl_idname='wavelength.model_revision'
    bl_label='Save Model Revision'
    name:StringProperty(name='Revision Name',default='Checkpoint')
    revision_id:StringProperty(options={'HIDDEN'})
    restore:BoolProperty(default=False,options={'HIDDEN'})

    def invoke(self,context,event):
        if self.revision_id:return self.execute(context)
        return context.window_manager.invoke_props_dialog(self)

    def run(self,context):
        from . import model_revisions
        asset=active_asset(context)
        if not asset:raise ValueError('Select an editable model asset')
        if self.revision_id:
            if self.restore:model_revisions.restore_placement(context,asset,self.revision_id)
            else:model_revisions.open_variant(context,asset,self.revision_id)
        else:
            model_revisions.save(context,asset,self.name)
            self.report({'INFO'},'Revision saved to the project directory. Save the blend file to retain its revision list.')


class WL_OT_model_collision_preview(_ModelEditAction,bpy.types.Operator):
    bl_idname='wavelength.model_collision_preview'
    bl_label='Preview Model Collision'
    bl_description='Show a collision snapshot; refresh after editing geometry or collision settings'
    clear:BoolProperty(default=False,options={'HIDDEN'})

    def run(self,context):
        from . import model_collision_preview
        if self.clear:
            model_collision_preview.clear()
            return
        asset=active_asset(context)
        if not asset:raise ValueError('Select an editable model asset')
        model_collision_preview.show(context,asset)


class WL_OT_create_model_asset(_ModelEditAction,bpy.types.Operator):
    bl_idname='wavelength.create_model_asset'
    bl_label='Create Model Asset'
    bl_description='Use the selected meshes and modelling controls as an editable model asset'
    name:StringProperty(name='Asset Name',default='Model')

    @classmethod
    def poll(cls,context):
        return (context.mode=='OBJECT' and bool(model_pipeline.extensions(context.scene.wavelength.engine))
                and any(obj.type=='MESH' for obj in context.selected_objects))

    def invoke(self,context,event):
        self.name=context.object.name if context.object else 'Model'
        return context.window_manager.invoke_props_dialog(self)

    def run(self,context):
        from .model_lifecycle import create
        create(context,self.name)


class WL_OT_select_model_sources(_ModelEditAction,bpy.types.Operator):
    bl_idname='wavelength.select_model_sources'
    bl_label='Select Model Sources'
    source_name:StringProperty(options={'HIDDEN'})

    def run(self,context):
        from . import model_lifecycle as lifecycle
        asset=active_asset(context)
        if not asset:raise ValueError('Select a model asset')
        if not self.source_name:
            lifecycle.select_sources(context,asset)
            return
        source=asset.objects.get(self.source_name)
        if source not in lifecycle.sources(asset) or source.name not in context.view_layer.objects:
            raise ValueError('This source is unavailable in the active view layer')
        for obj in context.selected_objects:obj.select_set(False)
        source.hide_set(False)
        source.select_set(True)
        context.view_layer.objects.active=source


class WL_OT_edit_model(_ModelEditAction,bpy.types.Operator):
    bl_idname='wavelength.edit_model';bl_label='Edit Model'
    bl_description='Edit the source asset used by all linked placements; use Make Model Unique for an independent variant'
    def run(self,context):
        from . import model_lifecycle as lifecycle
        entity=lifecycle.entity_for(context.object);asset=active_asset(context)
        if entity:lifecycle.edit(context,entity)
        elif asset:lifecycle.ensure(context,asset);lifecycle.select_sources(context,asset)
        else:raise ValueError('Select a placed model or editable model asset')


class WL_OT_make_model_unique(_ModelEditAction,bpy.types.Operator):
    bl_idname='wavelength.make_model_unique';bl_label='Make Model Unique'
    bl_description='Create an independent model variant with its own meshes, materials, rig and actions'
    def run(self,context):
        from . import model_lifecycle as lifecycle
        asset=active_asset(context)
        entity=lifecycle.entity_for(context.object)
        if not asset:
            if not entity:raise ValueError('Select a placed model or editable model asset')
            lifecycle.edit(context,entity)
            return
        lifecycle.make_unique(context,asset,entity if entity and entity.get('wl_custom_model')==asset else None)


class WL_OT_attach_model_asset(_ModelEditAction,bpy.types.Operator):
    bl_idname='wavelength.attach_model_asset';bl_label='Attach Model to Entity'
    bl_description='Attach selected editable sources to the active entity, replacing its model; other placements stay unchanged'
    def run(self,context):
        from . import model_lifecycle as lifecycle
        entity=lifecycle.entity_for(context.object)
        assets=selected_assets(context)
        if len(assets)!=1:raise ValueError('Select one editable asset together with the destination entity, and make the entity active')
        lifecycle.attach(context,assets.pop(),entity)


class WL_OT_detach_model_asset(_ModelEditAction,bpy.types.Operator):
    bl_idname='wavelength.detach_model_asset';bl_label='Detach Model'
    bl_description='Create an independent editable copy at this placement; leave placed models and their data unchanged'
    def run(self,context):
        from . import model_lifecycle as lifecycle
        entity=lifecycle.entity_for(context.object);asset=active_asset(context)
        if not asset or not entity or entity.get('wl_custom_model')!=asset:raise ValueError('Select an attached editable model')
        lifecycle.detach(context,asset,entity)


CLASSES=(WL_OT_model_origin,WL_OT_model_part,WL_OT_model_revision,WL_OT_model_collision_preview,WL_OT_create_model_asset,WL_OT_select_model_sources,WL_OT_import_model_asset,WL_OT_build_model_asset,WL_OT_publish_model_drop,WL_OT_convert_model_asset,WL_OT_package_model_asset,WL_OT_asset_clip,WL_FH_model_asset,
         WL_OT_edit_model,WL_OT_make_model_unique,WL_OT_attach_model_asset,WL_OT_detach_model_asset,WL_PT_model_asset)


def object_menu(self,context):
    from .model_lifecycle import entity_for
    entity=entity_for(context.object)
    if WL_OT_create_model_asset.poll(context) and not active_asset(context):
        self.layout.separator()
        self.layout.operator('wavelength.create_model_asset')
    if context.mode!='OBJECT' or not (active_asset(context) or selected_assets(context) or entity and model_pipeline.extensions(context.scene.wavelength.engine)):return
    self.layout.separator();self.layout.operator('wavelength.edit_model')
    if active_asset(context):
        self.layout.operator('wavelength.make_model_unique')
        if entity and entity.get('wl_custom_model'):self.layout.operator('wavelength.detach_model_asset')
    if active_asset(context) or selected_assets(context):self.layout.operator('wavelength.attach_model_asset')
def menu(self,context):
    if WL_OT_import_model_asset.poll(context):self.layout.operator(WL_OT_import_model_asset.bl_idname)
def register():
    from .model_backend_source1 import Source1
    model_pipeline.register(Source1())
    from . import model_collision_preview
    model_collision_preview.register()
    WL_FH_model_asset.bl_file_extensions=';'.join((*model_pipeline.all_extensions(),'.wlmodel'))
    for cls in CLASSES:bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_import.append(menu)
    bpy.types.VIEW3D_MT_object.append(object_menu);bpy.types.VIEW3D_MT_object_context_menu.append(object_menu)
    from .model_lifecycle import sync_placements,save_owned_images
    bpy.app.handlers.depsgraph_update_post.append(sync_placements)
    bpy.app.handlers.save_pre.append(save_owned_images)
def unregister():
    from . import model_collision_preview
    model_collision_preview.unregister()
    from .model_lifecycle import sync_placements,save_owned_images
    if sync_placements in bpy.app.handlers.depsgraph_update_post:bpy.app.handlers.depsgraph_update_post.remove(sync_placements)
    if save_owned_images in bpy.app.handlers.save_pre:bpy.app.handlers.save_pre.remove(save_owned_images)
    bpy.types.VIEW3D_MT_object_context_menu.remove(object_menu);bpy.types.VIEW3D_MT_object.remove(object_menu)
    bpy.types.TOPBAR_MT_file_import.remove(menu)
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)
    model_pipeline.unregister('source1')
