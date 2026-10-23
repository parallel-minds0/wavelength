"""Register, inherit, inspect and remove user profiles without editing templates."""
import json
from pathlib import Path
import bpy
from bpy_extras.io_utils import ImportHelper,ExportHelper
from .profile_store import Store
from .profile_registry import TEMPLATES
from . import workspace,profiles
_ITEMS=[];_PARENTS=[]
def store():return Store(Path(bpy.utils.user_resource('CONFIG'))/'wavelength'/'profiles')
def items(self,context):
    global _ITEMS
    _ITEMS=[(key,profiles.get(key)['label'],'Protected shipped template',index) for index,key in enumerate(profiles.PROFILE_ORDER)]
    _ITEMS.extend((p['id'],p['name'],'User profile; parent: '+p['parent'],p['enum_number']) for p in store().all())
    return _ITEMS
def parents(self,context):
    global _PARENTS
    _PARENTS=[]
    for key in TEMPLATES.definitions:
        try:TEMPLATES.settings(key)
        except ValueError:continue
        _PARENTS.append((key,TEMPLATES.resolve(key)['label'],'Protected template parent',len(_PARENTS)))
    _PARENTS.extend((p['id'],p['name'],'Registered user parent',p['enum_number']) for p in store().all())
    return _PARENTS

def snapshot(context,name,identity=None,parent=None):
    from .ui import _PROJECT_FIELDS
    s=context.scene.wavelength;parent=parent or s.engine;base=baseline(context,store().get(parent)['settings'])
    values={key:getattr(s,key) for key in (*_PROJECT_FIELDS,'grid_step') if key not in {'profile_id','profile_name','engine'}}
    overrides={key:value for key,value in values.items() if base.get(key)!=value} if s.engine==base['engine'] else {}
    return {'schema':2,'id':identity,'name':name,'parent':parent,'settings':overrides} if identity else {'schema':2,'name':name,'parent':parent,'settings':overrides}

def baseline(context,settings):
    """Resolve absent settings through RNA defaults and runtime path discovery."""
    from . import ui
    s=context.scene.wavelength;engine=settings['engine']
    values={key:s.bl_rna.properties[key].default for key in (*ui._PROJECT_FIELDS,'grid_step') if key not in {'profile_id','profile_name'}}
    if profiles.is_mesh_export(engine):
        from .mesh_assets import defaults
        values.update(defaults(engine))
    elif profiles.is_source(engine):
        from .source_tools import defaults
        values.update(defaults(profiles.get(engine).get('platform','windows'),engine=engine))
    elif engine=='goldsrc_windows':
        from .goldsrc_tools import defaults
        values.update(defaults())
    elif engine in {'goldsrc_linux','goldsrc_linux_steam'}:values.update(ui._hl1_linux_defaults())
    values.update(settings)
    return values

def apply(context,value):
    from . import textures,ui
    s=context.scene.wavelength
    if any(o.get('wl_csg') for o in context.scene.objects):raise ValueError('Finalize Geometry or cancel live CSG before loading a profile')
    fields=set((*ui._PROJECT_FIELDS,'grid_step','saved_profile','status','last_build','build_error'))
    before={key:getattr(s,key) for key in fields}
    old_configs=s.get('_wl_engine_configs','{}');values=baseline(context,value['settings'])
    previous=ui._IN_ENGINE_CHANGE;ui._IN_ENGINE_CHANGE=True
    try:
        s.engine=values['engine']
        # Resolve from defaults each time, including same-backend transitions.
        for key,val in values.items():
            if key in (*ui._PROJECT_FIELDS,'grid_step') and key not in {'engine','profile_id','profile_name'}:setattr(s,key,val)
        s.profile_id=value['id'];s.profile_name=value['name'];s.saved_profile=value['id']
    except Exception:
        s.engine=before['engine']
        for key,val in before.items():
            if key!='engine':setattr(s,key,val)
        s['_wl_active_engine']=before['engine'];s['_wl_engine_configs']=old_configs
        raise
    finally:ui._IN_ENGINE_CHANGE=previous
    if not previous:textures.refresh(s,context)

class WL_OT_profile(bpy.types.Operator):
    bl_idname='wavelength.profile';bl_label='Registered Profile'
    action:bpy.props.EnumProperty(items=[(x,x.title(),'') for x in ('CREATE','REGISTER','SAVE','DUPLICATE','RENAME','DELETE','REMOVE','REPARENT','LOAD')])
    name:bpy.props.StringProperty(name='Name',default='My profile')
    parent:bpy.props.EnumProperty(name='Inherit From',items=parents)
    def invoke(self,context,event):
        s=context.scene.wavelength;self.name=s.profile_name or 'My profile'
        available={item[0] for item in parents(None,context)}
        self.parent=s.profile_id if s.profile_id in available else s.engine
        if self.action in {'RENAME','DUPLICATE'}:
            try:self.name=store().get(s.saved_profile)['name']+(' Copy' if self.action=='DUPLICATE' else '')
            except ValueError:pass
        if self.action=='REPARENT':
            try:self.parent=store().raw(s.saved_profile)['parent']
            except ValueError as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        if self.action in {'LOAD','SAVE'}:return self.execute(context)
        if self.action in {'DELETE','REMOVE'}:return context.window_manager.invoke_confirm(self,event)
        return context.window_manager.invoke_props_dialog(self,width=520)
    def draw(self,context):
        self.layout.prop(self,'name')
        if self.action in {'CREATE','REGISTER','REPARENT'}:self.layout.prop(self,'parent')
        if self.action in {'CREATE','REGISTER'}:self.layout.label(text='Only differences from the parent are stored')
    def execute(self,context):
        s=context.scene.wavelength;registry=store()
        try:
            if self.action=='LOAD':apply(context,registry.get(s.saved_profile))
            elif self.action in {'DELETE','REMOVE'}:
                identity=s.saved_profile;registry.remove(identity)
                if s.profile_id==identity:s.profile_id=''
                s.saved_profile=s.engine
            elif self.action=='RENAME':
                value=registry.raw(s.saved_profile);value['name']=self.name;registry.save(value)
                if s.profile_id==value['id']:s.profile_name=self.name
            elif self.action=='REPARENT':
                value=registry.raw(s.saved_profile);current=registry.get(value['id']);base=registry.get(self.parent)
                if current['settings']['engine']!=base['settings']['engine']:raise ValueError('Register a new profile to change backend; reparenting preserves current backend')
                value['parent']=self.parent;value['settings']={k:v for k,v in current['settings'].items() if k!='engine' and base['settings'].get(k)!=v}
                registry.save(value)
            else:
                if any(o.get('wl_csg') for o in context.scene.objects):raise ValueError('Finalize or cancel live CSG before registering/loading a profile')
                if self.action=='SAVE':
                    original=registry.raw(s.profile_id)
                    if registry.get(s.profile_id)['settings']['engine']!=s.engine:raise ValueError('Register a new profile for the changed backend')
                    value=snapshot(context,s.profile_name,s.profile_id,original['parent'])
                elif self.action=='DUPLICATE':value={'schema':2,'name':self.name,'parent':s.saved_profile,'settings':{}}
                else:value=snapshot(context,self.name,parent=self.parent or s.engine)
                apply(context,registry.save(value))
            return {'FINISHED'}
        except (ValueError,OSError,TypeError,KeyError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}

class WL_OT_profile_import(bpy.types.Operator,ImportHelper):
    bl_idname='wavelength.profile_import';bl_label='Register Profile File';filename_ext='.json'
    def execute(self,context):
        try:
            if any(o.get('wl_csg') for o in context.scene.objects):raise ValueError('Finalize or cancel live CSG before loading a profile')
            value=store().register(json.loads(Path(self.filepath).read_text(encoding='utf-8-sig')));apply(context,value);return {'FINISHED'}
        except (ValueError,OSError,TypeError,KeyError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
class WL_OT_profile_export(bpy.types.Operator,ExportHelper):
    bl_idname='wavelength.profile_export';bl_label='Export Profile Bundle';filename_ext='.json'
    def execute(self,context):
        try:
            s=context.scene.wavelength;Path(self.filepath).write_text(json.dumps(store().bundle(s.saved_profile),indent=2),encoding='utf-8');return {'FINISHED'}
        except (ValueError,OSError,TypeError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}

def draw_registry(layout,context):
    s=context.scene.wavelength;layout.label(text='Active: '+s.profile_name)
    layout.prop(s,'saved_profile',text='Registered Profile')
    row=layout.row(align=True)
    for action,label in [('LOAD','Load'),('REGISTER','Register'),('DUPLICATE','Derive')]:row.operator('wavelength.profile',text=label).action=action
    builtin=s.saved_profile in TEMPLATES.definitions
    row=layout.row(align=True);row.enabled=not builtin
    for action,label in [('RENAME','Rename'),('REPARENT','Parent'),('REMOVE','Remove')]:row.operator('wavelength.profile',text=label).action=action
    row=layout.row();row.enabled=bool(s.profile_id and s.profile_id not in TEMPLATES.definitions)
    row.operator('wavelength.profile',text='Save Current Overrides').action='SAVE'
    row=layout.row(align=True);row.operator('wavelength.profile_import',text='Register File');row.operator('wavelength.profile_export',text='Export Bundle')
    layout.label(text='Protected shipped template' if builtin else 'Removable user profile',icon='LOCKED' if builtin else 'USER')
    registry=store()
    try:
        value=registry.get(s.saved_profile)
        parent=value.get('parent')
        label=TEMPLATES.resolve(parent)['label'] if parent in TEMPLATES.definitions else registry.get(parent)['name'] if parent else 'None'
        layout.label(text='Parent: '+label)
    except ValueError:pass
    for message in registry.errors[:2]:layout.label(text=message[:80],icon='ERROR')

class WL_PT_profiles(bpy.types.Panel):
    bl_label='Registered Profiles';bl_idname='WL_PT_profiles';bl_space_type='VIEW_3D';bl_region_type='HEADER'
    bl_ui_units_x=26
    @classmethod
    def poll(cls,context):return workspace.active(context)
    def draw(self,context):draw_registry(self.layout,context)

CLASSES=(WL_OT_profile,WL_OT_profile_import,WL_OT_profile_export,WL_PT_profiles)
@bpy.app.handlers.persistent
def sync_selection(*_):
    registry=store();known={p['id'] for p in registry.all()}|set(profiles.PROFILE_ORDER)
    for scene in bpy.data.scenes:
        if not hasattr(scene,'wavelength'):continue
        s=scene.wavelength;s.saved_profile=s.profile_id if s.profile_id in known else s.engine
        if not s.profile_id:s.profile_id=s.engine;s.profile_name=profiles.get(s.engine)['label']
def register():
    for cls in CLASSES:bpy.utils.register_class(cls)
    bpy.app.handlers.load_post.append(sync_selection)
    bpy.app.timers.register(sync_selection,first_interval=.1)
def unregister():
    if sync_selection in bpy.app.handlers.load_post:bpy.app.handlers.load_post.remove(sync_selection)
    if bpy.app.timers.is_registered(sync_selection):bpy.app.timers.unregister(sync_selection)
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)
