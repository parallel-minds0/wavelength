"""Asset Browser surface editing and a shared scene asset eyedropper."""
import json
import math
from contextlib import contextmanager
import bpy
from bpy_extras import view3d_utils
from . import workspace,profiles,scene,formats,textures,editor
_temp_override=None

def face_axes(face,projection):
    from mathutils import Vector
    normal=Vector(face.plane()[0]);u=(Vector(face.points[1])-Vector(face.points[0])).normalized();v=normal.cross(u).normalized()
    angle=math.radians(projection[2]);c=math.cos(angle);s=math.sin(angle)
    a=u*c-v*s;b=u*s+v*c
    return [[*a,projection[0]],[*b,projection[1]]]

@contextmanager
def viewport(context):
    global _temp_override
    if _temp_override is None:_temp_override=bpy.context.temp_override
    screen=getattr(context,'screen',None) or bpy.context.screen
    area=next((a for a in screen.areas if a.type=='VIEW_3D'),None)
    if not area:raise ValueError('Open a 3D Viewport to edit scene surfaces')
    region=next(r for r in area.regions if r.type=='WINDOW')
    with _temp_override(area=area,region=region):yield bpy.context

def assign_brushes(context,material):
    from . import asset_browser
    with viewport(context):
        busy=asset_browser._BUSY;asset_browser._BUSY=True
        try:result=bpy.ops.wavelength.apply_texture(material_only=True)
        finally:asset_browser._BUSY=busy
        if result!={'FINISHED'}:raise ValueError('Texture assignment did not finish')

def assign_material(context,material):
    from . import primitive_ui,asset_browser
    with viewport(context):
        ctx=bpy.context;edit=ctx.mode=='EDIT_MESH'
        objects=list(ctx.objects_in_mode_unique_data) if edit else list(ctx.selected_objects)
        if not objects:raise ValueError('Select mesh objects or faces in the viewport')
        if any(o.get('wl_role')=='BRUSH' or primitive_ui.root_for(o) for o in objects):assign_brushes(ctx,material)
        for obj in objects:
            if obj.type!='MESH' or obj.get('wl_role')=='BRUSH' or primitive_ui.root_for(obj):continue
            slot=next((i for i,m in enumerate(obj.data.materials) if m==material),None)
            if slot is None:slot=len(obj.data.materials);obj.data.materials.append(material)
            if edit:
                import bmesh
                bm=bmesh.from_edit_mesh(obj.data)
                for face in bm.faces:
                    if face.select:face.material_index=slot
                bmesh.update_edit_mesh(obj.data)
            else:
                for face in obj.data.polygons:face.material_index=slot
            if obj.get('wl_terrain'):
                from . import terrain
                terrain.sync_material(obj,force=True)
            else:asset_browser._ensure_mesh_uv(obj)

def sample(context,obj,index,kind='AUTO'):
    s=context.scene.wavelength;owner=obj
    while owner and owner.get('wl_role')!='ENTITY':owner=owner.parent
    if kind!='TEXTURE' and owner:
        pairs=dict(json.loads(owner.get('wl_pairs','[]')));name=pairs.get('classname','')
        if not name:raise ValueError('Entity has no class')
        context.scene['_wl_asset_clipboard']=json.dumps(dict(engine=s.engine,category='ENTITY',path=name))
        s.entity_class=name;s.asset_browser_section='ENTITIES';s.status='Holding entity class: '+name
        return
    if kind=='ENTITY':raise ValueError('Point at an entity model or icon')
    if obj.type!='MESH' or not 0<=index<len(obj.data.polygons):raise ValueError('Point at a textured mesh face')
    fid=None
    if obj.mode=='EDIT':
        import bmesh
        bm=bmesh.from_edit_mesh(obj.data);bm.faces.ensure_lookup_table();polygon=bm.faces[index]
        layer=bm.faces.layers.int.get('wl_face_id')
        if layer:fid=polygon[layer]
    else:
        polygon=obj.data.polygons[index];attr=obj.data.attributes.get('wl_face_id')
        if attr:fid=attr.data[index].value
    mat=obj.data.materials[polygon.material_index] if polygon.material_index<len(obj.data.materials) else None
    name=mat.get('wl_texture','') if mat else ''
    record={}
    if fid is not None:
        record=json.loads(obj.data.get('wl_faces','{}')).get(str(fid),{})
        name=record.get('texture') or name
    if not name:raise ValueError('This face has no engine texture')
    projection=record.get('projection',[0,0,0,1,1])
    s.texture=name;s.shift_u=projection[0];s.shift_v=projection[1];s.texture_rotation=projection[2];s.texture_scale_u=projection[3];s.texture_scale_v=projection[4]
    context.scene['_wl_asset_clipboard']=json.dumps(dict(engine=s.engine,category='MATERIAL',path=name))
    s.asset_browser_section='TEXTURES';s.status='Holding texture: '+name

class WL_OT_pick(bpy.types.Operator):
    bl_idname='wavelength.pick_asset';bl_label='Pick Texture or Entity';bl_description='Click a face or entity in the viewport to hold its texture or entity class; Esc cancels'
    kind:bpy.props.EnumProperty(items=[('AUTO','Automatic','Entity models/icons pick the entity class; brushes pick a texture'),('TEXTURE','Texture','Pick a face texture'),('ENTITY','Entity','Pick an entity class')],default='AUTO')
    @classmethod
    def poll(cls,context):return workspace.active(context)
    def invoke(self,context,event):
        context.window.cursor_modal_set('EYEDROPPER');context.window_manager.modal_handler_add(self)
        context.workspace.status_text_set('Pick a texture or entity in the viewport · Shift-click: texture only · Esc: cancel')
        return {'RUNNING_MODAL'}
    def finish(self,context):context.window.cursor_modal_restore();context.workspace.status_text_set(None)
    def modal(self,context,event):
        if event.type in {'ESC','RIGHTMOUSE'} or not workspace.active(context):self.finish(context);return {'CANCELLED'}
        if event.type!='LEFTMOUSE' or event.value!='PRESS':return {'RUNNING_MODAL'}
        area=next((a for a in context.screen.areas if a.type=='VIEW_3D' and a.x<=event.mouse_x<a.x+a.width and a.y<=event.mouse_y<a.y+a.height),None)
        if not area:return {'RUNNING_MODAL'}
        region=next(r for r in area.regions if r.type=='WINDOW');xy=(event.mouse_x-region.x,event.mouse_y-region.y);rv=area.spaces.active.region_3d
        origin=view3d_utils.region_2d_to_origin_3d(region,rv,xy);direction=view3d_utils.region_2d_to_vector_3d(region,rv,xy)
        hit,location,normal,index,obj,matrix=context.scene.ray_cast(context.evaluated_depsgraph_get(),origin,direction)
        try:
            kind='TEXTURE' if event.shift else self.kind
            if not hit and kind!='TEXTURE':
                candidates=[]
                for candidate in context.scene.objects:
                    if candidate.get('wl_role')!='ENTITY' or not candidate.visible_get():continue
                    pos=view3d_utils.location_3d_to_region_2d(region,rv,candidate.matrix_world.translation)
                    if pos is not None and (pos-__import__('mathutils').Vector(xy)).length<18:candidates.append(((pos-__import__('mathutils').Vector(xy)).length,candidate))
                if candidates:obj=min(candidates,key=lambda p:p[0])[1];index=-1
            if obj is None:raise ValueError('No surface or entity under the pointer')
            sample(context,obj,index,kind)
        except (ValueError,RuntimeError,IndexError) as exc:self.report({'WARNING'},str(exc));return {'RUNNING_MODAL'}
        self.finish(context);return {'FINISHED'}

class WL_OT_held(bpy.types.Operator):
    bl_idname='wavelength.use_held_asset';bl_label='Use Held Asset';bl_options={'UNDO'}
    @classmethod
    def poll(cls,context):return workspace.active(context) and bool(context.scene.get('_wl_asset_clipboard'))
    def execute(self,context):
        try:
            row=json.loads(context.scene['_wl_asset_clipboard'])
            if row['engine']!=context.scene.wavelength.engine:raise ValueError('Held asset belongs to a different profile; pick again')
            with viewport(context):
                if row['category']=='MATERIAL':
                    context.scene.wavelength.texture=row['path'];return bpy.ops.wavelength.apply_texture()
                if bpy.context.mode!='OBJECT':raise ValueError('Switch to Object Mode to place an entity')
                from .ui import _spawn_point_entity
                _spawn_point_entity(bpy.context,row['path'])
            return {'FINISHED'}
        except (ValueError,RuntimeError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}

class WL_PT_surface(bpy.types.Panel):
    bl_label='Texture Settings';bl_space_type='FILE_BROWSER';bl_region_type='HEADER'
    bl_ui_units_x=24
    def draw(self,context):
        l=self.layout;s=context.scene.wavelength
        l.label(text='Edit Mode: selected faces')
        l.label(text='Object Mode: whole selected objects')
        for name in ('texture','shift_u','shift_v','texture_rotation','texture_scale_u','texture_scale_v'):l.prop(s,name)
        if profiles.uses_valve_axes(s.engine):l.prop(s,'texture_alignment')
        if profiles.is_source(s.engine):l.prop(s,'texture_lightmap')
        row=l.row(align=True);row.operator('wavelength.read_face_texture',text='Read Face');row.operator('wavelength.apply_texture',text='Apply Mapping')
        from .ui import _draw_face_actions
        _draw_face_actions(l);l.prop(s,'live_texture_reproject')
        for actions in [[('FIT','Fit'),('CENTER','Center')],[('LEFT','Left'),('RIGHT','Right'),('TOP','Top'),('BOTTOM','Bottom')]]:
            row=l.row(align=True)
            for action,label in actions:row.operator('wavelength.surface_align',text=label).action=action

class WL_OT_align(bpy.types.Operator):
    bl_idname='wavelength.surface_align';bl_label='Align Face Texture';bl_options={'UNDO'}
    action:bpy.props.StringProperty(default='FIT')
    @classmethod
    def poll(cls,context):return workspace.active(context) and context.scene.wavelength.engine!='blender'
    def execute(self,context):
        try:
            with viewport(context):
                active=bpy.context.object;edit=bool(active and active.mode=='EDIT')
                objects=list(bpy.context.objects_in_mode_unique_data) if edit else list(bpy.context.selected_objects)
                if edit:bpy.ops.object.mode_set(mode='OBJECT')
                try:
                    for obj in objects:
                        if obj.get('wl_role')!='BRUSH':continue
                        faces=scene.brush_from_object(obj,context.scene.wavelength.engine);attr=obj.data.attributes['wl_face_id'];by_id=dict(zip(sorted(d.value for d in attr.data),faces));records=json.loads(obj.data.get('wl_faces','{}'))
                        for poly in obj.data.polygons:
                            if edit and not poly.select:continue
                            fid=attr.data[poly.index].value;face=by_id[fid];axes=face.axes or formats.quake_axes(face.plane()[0],face.projection)
                            mat=obj.data.materials[poly.material_index] if poly.material_index<len(obj.data.materials) else None
                            size=[mat.get('wl_width',64),mat.get('wl_height',64)] if mat else [64,64]
                            points=[obj.matrix_world@obj.data.vertices[v].co/obj.get('wl_unit_meters',1.) for v in poly.vertices]
                            for axis in range(2):
                                values=[sum(axes[axis][j]*p[j] for j in range(3)) for p in points];lo,hi=min(values),max(values);scale=face.projection[3+axis]
                                if self.action=='FIT':scale=max(hi-lo,1e-6)/size[axis];face.projection[3+axis]=scale
                                mapped=sorted([lo/scale,hi/scale]);shift=None
                                if self.action=='FIT' or (axis==0 and self.action=='LEFT') or (axis==1 and self.action=='TOP'):shift=-mapped[0]
                                elif (axis==0 and self.action=='RIGHT') or (axis==1 and self.action=='BOTTOM'):shift=size[axis]-mapped[1]
                                elif self.action=='CENTER':shift=(size[axis]-sum(mapped))/2
                                if shift is not None:face.projection[axis]=shift;axes[axis][3]=shift
                            if profiles.uses_valve_axes(context.scene.wavelength.engine):face.axes=axes
                            from dataclasses import asdict
                            records[str(fid)]=asdict(face)
                        obj.data['wl_faces']=json.dumps(records);editor.apply_uv(obj,context.scene.wavelength.engine)
                finally:
                    if edit:bpy.ops.object.mode_set(mode='EDIT')
            return {'FINISHED'}
        except (ValueError,RuntimeError,ZeroDivisionError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}

CLASSES=(WL_OT_pick,WL_OT_held,WL_PT_surface,WL_OT_align)
def register():
    for cls in CLASSES:bpy.utils.register_class(cls)
def unregister():
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)
