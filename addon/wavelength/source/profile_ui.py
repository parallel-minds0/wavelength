import json
from pathlib import Path
import bpy
from bpy_extras.io_utils import ImportHelper,ExportHelper
from .profile_store import Store,validate
from . import workspace,profiles

_ITEMS=[]
def store():return Store(Path(bpy.utils.user_resource('CONFIG'))/'wavelength'/'profiles')
def items(self,context):
    global _ITEMS
    _ITEMS=[(p['id'],profiles.get(p['settings']['engine'])['label']+' / '+p['name'],'User profile') for p in store().all()]
    return _ITEMS or [('NONE','No saved profiles','')]

def snapshot(context,name,identity=None):
    from .ui import _PROJECT_FIELDS
    s=context.scene.wavelength
    fields=(*_PROJECT_FIELDS,'asset_paths','unit_scale','grid_step')
    value={'schema':1,'name':name,'settings':{k:getattr(s,k) for k in fields}}
    if identity:value['id']=identity
    return validate(value)


def apply(context,value):
    value=validate(value);s=context.scene.wavelength
    s.engine=value['settings']['engine']
    for key,val in value['settings'].items():
        if hasattr(s,key):setattr(s,key,val)
    s.profile_id=value['id'];s.profile_name=value['name']


class WL_OT_profile(bpy.types.Operator):
    bl_idname='wavelength.profile';bl_label='User Profile'
    action:bpy.props.EnumProperty(items=[(x,x.title(),'') for x in ('CREATE','SAVE','DUPLICATE','RENAME','DELETE','LOAD')])
    name:bpy.props.StringProperty(name='Name',default='My project')
    def invoke(self,context,event):
        self.name=context.scene.wavelength.profile_name or 'My project'
        if self.action in {'LOAD','SAVE'}:return self.execute(context)
        if self.action=='DELETE':return context.window_manager.invoke_confirm(self,event)
        return context.window_manager.invoke_props_dialog(self)
    def execute(self,context):
        s=context.scene.wavelength
        try:
            if self.action=='LOAD':apply(context,store().get(s.saved_profile))
            elif self.action=='DELETE':store().remove(s.saved_profile);s.profile_id=''
            else:
                identity=s.profile_id if self.action=='SAVE' else s.saved_profile if self.action=='RENAME' else None
                if self.action=='RENAME':value=store().get(identity);value['name']=self.name
                else:value=snapshot(context,self.name,identity)
                value=store().save(value);s.profile_id=value['id'];s.profile_name=value['name']
            return {'FINISHED'}
        except (ValueError,OSError,TypeError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}


class WL_OT_profile_import(bpy.types.Operator,ImportHelper):
    bl_idname='wavelength.profile_import';bl_label='Import Profile';filename_ext='.json'
    def execute(self,context):
        try:apply(context,store().save(json.loads(Path(self.filepath).read_text())));return {'FINISHED'}
        except (ValueError,OSError,TypeError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
class WL_OT_profile_export(bpy.types.Operator,ExportHelper):
    bl_idname='wavelength.profile_export';bl_label='Export Profile';filename_ext='.json'
    def execute(self,context):
        try:Path(self.filepath).write_text(json.dumps(snapshot(context,context.scene.wavelength.profile_name or 'My project',context.scene.wavelength.profile_id or None),indent=2));return {'FINISHED'}
        except (ValueError,OSError,TypeError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}


class WL_PT_profiles(bpy.types.Panel):
    bl_label='User Profiles';bl_idname='WL_PT_profiles';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='wavelength'
    @classmethod
    def poll(cls,context):return workspace.active(context)
    def draw(self,context):
        s=context.scene.wavelength;l=self.layout;l.prop(s,'saved_profile')
        row=l.row(align=True)
        for action in ('LOAD','CREATE','SAVE','DUPLICATE'):row.operator('wavelength.profile',text=action.title()).action=action
        row=l.row(align=True)
        for action in ('RENAME','DELETE'):row.operator('wavelength.profile',text=action.title()).action=action
        row.operator('wavelength.profile_import',text='Import');row.operator('wavelength.profile_export',text='Export')
        l.prop(s,'profile_name');l.prop(s,'unit_scale');l.prop(s,'asset_paths')
        l.label(text='Z-up, engine units; settings stored outside the add-on')

CLASSES=(WL_OT_profile,WL_OT_profile_import,WL_OT_profile_export,WL_PT_profiles)
def register():
    for cls in CLASSES:bpy.utils.register_class(cls)
def unregister():
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)
