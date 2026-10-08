"""High-level engine authoring workflows for Wavelength 0.10 pre-alpha.

These operators deliberately compose the existing brush/entity/texture/export systems.
They do not replace the canonical geometry, grid, transform or MAP paths.
"""
import json, os, uuid
from pathlib import Path
import bpy
from bpy.props import StringProperty, EnumProperty, BoolProperty
from . import scene, system_tree,profiles


def _pairs(obj):
    key='wl_pairs' if obj and obj.get('wl_role')=='ENTITY' else 'wl_entity_pairs'
    try:return key, list(json.loads(obj.get(key,'[]')))
    except Exception:return key, []

def _set(obj,key,value):
    store,pairs=_pairs(obj); found=False; out=[]
    for k,v in pairs:
        if k==key and not found: out.append((k,str(value)));found=True
        else: out.append((k,v))
    if not found:out.append((key,str(value)))
    obj[store]=json.dumps(out)

def _new_entity(context, classname, extra=()):
    s=context.scene.wavelength
    old=s.entity_class;s.entity_class=classname
    try:bpy.ops.wavelength.add_entity()
    finally:s.entity_class=old
    obj=context.active_object
    if not obj or obj.get('wl_role')!='ENTITY':raise RuntimeError('Entity creation failed')
    for k,v in extra:_set(obj,k,v)
    return obj

def _brushes(context):return [o for o in context.selected_objects if o.get('wl_role')=='BRUSH']

class WL_OT_asset_entity(bpy.types.Operator):
    bl_idname='wavelength.asset_entity';bl_label='Add Engine Asset';bl_options={'REGISTER','UNDO'}
    kind:EnumProperty(items=[('MODEL','Model (.mdl)','Generic HL1 studio model'),('SPRITE','Sprite (.spr)','Animated sprite'),('DECAL','Decal','infodecal'),('SOUND','Ambient Sound','ambient_generic')])
    path:StringProperty(name='Asset path')
    def invoke(self,context,event):return context.window_manager.invoke_props_dialog(self,width=520)
    def draw(self,context):self.layout.prop(self,'path')
    def execute(self,context):
        if not profiles.is_goldsrc(context.scene.wavelength.engine):self.report({'ERROR'},'Asset helpers currently target Half-Life 1');return {'CANCELLED'}
        value=self.path.replace('\\','/').strip()
        if not value:self.report({'ERROR'},'Enter an engine-relative asset path');return {'CANCELLED'}
        spec={'MODEL':('cycler','model'),'SPRITE':('env_sprite','model'),'DECAL':('infodecal','texture'),'SOUND':('ambient_generic','message')}[self.kind]
        obj=_new_entity(context,spec[0],[(spec[1],value)])
        context.scene.wavelength.status=f'Created {spec[0]} using {value}'
        return {'FINISHED'}

class WL_OT_special_brush(bpy.types.Operator):
    bl_idname='wavelength.special_brush';bl_label='Make Special Brush Entity';bl_options={'REGISTER','UNDO'}
    classname:EnumProperty(items=[
      ('func_detail','func_detail','Non-structural detail'),('func_wall','func_wall','Static brush entity'),('func_illusionary','func_illusionary','Non-solid visual brush'),('func_water','func_water','Water volume'),('func_ladder','func_ladder','Ladder'),('func_breakable','func_breakable','Breakable'),('func_pushable','func_pushable','Pushable'),('func_button','func_button','Button'),('func_door','func_door','Sliding door'),('func_door_rotating','func_door_rotating','Rotating door'),('func_rotating','func_rotating','Rotating brush'),('func_train','func_train','Train'),('trigger_once','trigger_once','One-shot trigger'),('trigger_multiple','trigger_multiple','Repeat trigger'),('trigger_hurt','trigger_hurt','Damage trigger'),('trigger_push','trigger_push','Push trigger'),('trigger_teleport','trigger_teleport','Teleport trigger'),('trigger_changelevel','trigger_changelevel','Change-level trigger')])
    def execute(self,context):
        if not _brushes(context):self.report({'ERROR'},'Select one or more Wavelength brushes');return {'CANCELLED'}
        s=context.scene.wavelength;old=s.entity_class;s.entity_class=self.classname
        try:bpy.ops.wavelength.brush_entity()
        finally:s.entity_class=old
        if self.classname.startswith('trigger_'):
            for obj in _brushes(context):
                try:
                    records=json.loads(obj.data.get('wl_faces','{}'))
                    for rec in records.values():rec['texture']='AAATRIGGER'
                    obj.data['wl_faces']=json.dumps(records)
                except Exception:pass
        return {'FINISHED'}

class WL_OT_origin_brush(bpy.types.Operator):
    bl_idname='wavelength.origin_brush';bl_label='Mark Origin Brush';bl_options={'REGISTER','UNDO'}
    def execute(self,context):
        changed=0
        for obj in _brushes(context):
            try:
                records=json.loads(obj.data.get('wl_faces','{}'))
                for rec in records.values():rec['texture']='origin'
                obj.data['wl_faces']=json.dumps(records);obj['wl_special']='ORIGIN';changed+=1
            except Exception:pass
        self.report({'INFO'},f'Marked {changed} origin brush(es)');return {'FINISHED'}

class WL_OT_path_chain(bpy.types.Operator):
    bl_idname='wavelength.path_chain';bl_label='Create path_corner Chain';bl_options={'REGISTER','UNDO'}
    prefix:StringProperty(name='Targetname prefix',default='path')
    loop:BoolProperty(name='Loop',default=False)
    def invoke(self,context,event):return context.window_manager.invoke_props_dialog(self)
    def execute(self,context):
        # Selected objects act as ordered waypoint positions; names give deterministic ordering.
        refs=sorted(context.selected_objects,key=lambda o:o.name.casefold())
        if len(refs)<2:self.report({'ERROR'},'Select at least two objects as waypoint positions');return {'CANCELLED'}
        created=[]
        for i,ref in enumerate(refs):
            obj=_new_entity(context,'path_corner',[('targetname',f'{self.prefix}_{i+1:02d}')]);obj.location=ref.matrix_world.translation;created.append(obj)
        for i,obj in enumerate(created):
            if i+1<len(created):_set(obj,'target',f'{self.prefix}_{i+2:02d}')
            elif self.loop:_set(obj,'target',f'{self.prefix}_01')
        return {'FINISHED'}

class WL_OT_select_class(bpy.types.Operator):
    bl_idname='wavelength.select_class';bl_label='Select Same Class'
    def execute(self,context):
        active=context.active_object
        if not active:return {'CANCELLED'}
        classname=dict(_pairs(active)[1]).get('classname','')
        if not classname:return {'CANCELLED'}
        bpy.ops.object.select_all(action='DESELECT')
        for obj in context.scene.objects:
            if dict(_pairs(obj)[1]).get('classname')==classname:
                try:obj.select_set(True)
                except RuntimeError:pass
        return {'FINISHED'}

class WL_OT_asset_report(bpy.types.Operator):
    bl_idname='wavelength.asset_report';bl_label='Asset Dependency Report'
    def execute(self,context):
        deps={'models':set(),'sprites':set(),'sounds':set(),'textures':set(),'wads':set()}
        for obj in context.scene.objects:
            for k,v in _pairs(obj)[1]:
                low=v.casefold()
                if low.endswith('.mdl'):deps['models'].add(v)
                elif low.endswith('.spr'):deps['sprites'].add(v)
                elif low.endswith('.wav'):deps['sounds'].add(v)
            if obj.get('wl_role')=='BRUSH':deps['textures'].update(system_tree.brush_textures(obj))
        s=context.scene.wavelength
        try:deps['wads'].update(json.loads(s.texture_wads or '[]'))
        except Exception:pass
        text=bpy.data.texts.get('Wavelength Asset Report') or bpy.data.texts.new('Wavelength Asset Report');text.clear()
        for group in ('wads','models','sprites','sounds','textures'):
            text.write(f'[{group.upper()}] {len(deps[group])}\n')
            for value in sorted(deps[group],key=str.casefold):text.write(f'{value}\n')
            text.write('\n')
        context.scene.wavelength.status='Asset report written to Text Editor: Wavelength Asset Report'
        return {'FINISHED'}

class WL_OT_texture_copy(bpy.types.Operator):
    bl_idname='wavelength.texture_copy';bl_label='Copy Face Mapping'
    def execute(self,context):
        s=context.scene.wavelength
        context.scene['_wl_texture_clipboard']=json.dumps({'texture':s.texture,'shift_u':s.shift_u,'shift_v':s.shift_v,'rotation':s.texture_rotation,'scale_u':s.texture_scale_u,'scale_v':s.texture_scale_v})
        return {'FINISHED'}
class WL_OT_texture_paste(bpy.types.Operator):
    bl_idname='wavelength.texture_paste';bl_label='Paste Face Mapping';bl_options={'UNDO'}
    def execute(self,context):
        try:d=json.loads(context.scene.get('_wl_texture_clipboard','{}'))
        except Exception:d={}
        if not d:self.report({'ERROR'},'No copied face mapping');return {'CANCELLED'}
        s=context.scene.wavelength;s.texture=d['texture'];s.shift_u=d['shift_u'];s.shift_v=d['shift_v'];s.texture_rotation=d['rotation'];s.texture_scale_u=d['scale_u'];s.texture_scale_v=d['scale_v']
        bpy.ops.wavelength.apply_texture();return {'FINISHED'}


class WL_OT_flag_toggle(bpy.types.Operator):
    bl_idname='wavelength.flag_toggle';bl_label='Toggle Spawn Flag';bl_options={'UNDO'}
    field_index:bpy.props.IntProperty();mask:bpy.props.IntProperty()
    def execute(self,context):
        fields=context.scene.wavelength.fields
        if self.field_index<0 or self.field_index>=len(fields):return {'CANCELLED'}
        item=fields[self.field_index];item.integer=int(item.integer)^int(self.mask);return {'FINISHED'}

class WL_OT_choice_set(bpy.types.Operator):
    bl_idname='wavelength.choice_set';bl_label='Set Entity Choice';bl_options={'UNDO'}
    field_index:bpy.props.IntProperty();value:StringProperty()
    def execute(self,context):
        fields=context.scene.wavelength.fields
        if self.field_index<0 or self.field_index>=len(fields):return {'CANCELLED'}
        item=fields[self.field_index]
        if item.kind in {'integer','flags'}:
            try:item.integer=int(self.value)
            except ValueError:item.value=self.value;item.kind='string'
        else:item.value=self.value
        return {'FINISHED'}

class WL_PT_authoring(bpy.types.Panel):
    bl_label='HL1 Authoring';bl_idname='WL_PT_authoring';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='wavelength';bl_parent_id='WL_PT_main';bl_options={'DEFAULT_CLOSED'}
    def draw(self,context):
        l=self.layout;s=context.scene.wavelength
        if s.engine=='blender':l.label(text='Choose GoldSrc or Quake',icon='INFO');return
        if profiles.is_goldsrc(s.engine):
            box=l.box();box.label(text='Assets',icon='ASSET_MANAGER')
            row=box.row(align=True)
            for kind,label in [('MODEL','Model'),('SPRITE','Sprite'),('DECAL','Decal'),('SOUND','Sound')]:op=row.operator('wavelength.asset_entity',text=label);op.kind=kind
            box.operator('wavelength.asset_report',icon='TEXT')
            box=l.box();box.label(text='Special Brushes',icon='MODIFIER');box.operator('wavelength.special_brush');box.operator('wavelength.origin_brush')
            box=l.box();box.label(text='Paths & Relationships',icon='TRACKING');box.operator('wavelength.path_chain');box.operator('wavelength.select_class')
        box=l.box();box.label(text='Face Mapping',icon='UV');row=box.row(align=True);row.operator('wavelength.texture_copy');row.operator('wavelength.texture_paste')

CLASSES=(WL_OT_asset_entity,WL_OT_special_brush,WL_OT_origin_brush,WL_OT_path_chain,WL_OT_select_class,WL_OT_asset_report,WL_OT_texture_copy,WL_OT_texture_paste,WL_OT_flag_toggle,WL_OT_choice_set,WL_PT_authoring)
def register():
    for cls in CLASSES:bpy.utils.register_class(cls)
def unregister():
    for cls in reversed(CLASSES):
        try:bpy.utils.unregister_class(cls)
        except Exception:pass
