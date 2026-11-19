"""Asset Browser surface editing and a shared scene asset eyedropper."""
import json
import math
from contextlib import contextmanager
import bpy
from bpy_extras import view3d_utils
from . import workspace,profiles,scene,formats,textures,editor
_temp_override=None
MAPPING_FIELDS=('shift_u','shift_v','texture_rotation','texture_scale_u','texture_scale_v')


def mapping_field(name, label, **options):
    """UI-only setters keep face sampling and profile changes free of edits."""
    def get(settings):
        return getattr(settings,name)

    def set_value(settings,value):
        if settings.live_mapping_adjustment and workspace.active(bpy.context,'textures'):
            try:
                with viewport(bpy.context) as context:
                    adjust_mapping(context,MAPPING_FIELDS.index(name),getattr(settings,name),value)
            except (ValueError,RuntimeError) as exc:
                settings.status=str(exc)
                return
        setattr(settings,name,value)

    return bpy.props.FloatProperty(name=label,get=get,set=set_value,**options)


def adjust_mapping(context, field, old, value):
    """Apply the drag delta without replacing individual face mappings."""
    from . import primitive_ui
    from .edit_safety import topology_modal_active
    import bmesh

    if field>=3 and abs(value)<1e-6:
        raise ValueError('Texture scales must be nonzero')
    if value==old:return
    if topology_modal_active(context):
        raise ValueError('Finish the current mesh operation before adjusting mapping')
    settings=context.scene.wavelength
    edit=context.mode=='EDIT_MESH'
    objects=context.objects_in_mode_unique_data if edit else context.selected_objects
    targets={}
    generated=False
    for obj in objects:
        root=primitive_ui.root_for(obj)
        parts=primitive_ui.parts_for(root) if root and root.get('wl_assembly_locked',True) and not edit else [obj]
        for part in parts:
            if (part.type=='MESH' and (part.get('wl_role')=='BRUSH' or profiles.is_mesh_export(settings.engine))
                    and not part.get('wl_source_displacement')
                    and not part.get('wl_custom_model_owner') and part.get('wl_role')!='MODEL_SOURCE'
                    and not part.get('wl_model_reference') and not part.get('wl_editor_helper')):
                if any(modifier.show_viewport for modifier in part.modifiers):
                    generated=True
                else:
                    targets.setdefault(part.data,part)
    if generated and not targets:
        raise ValueError('Finalize generated geometry before adjusting its mapping')

    delta=value-old
    ratio=value/old if field>=3 and abs(old)>=1e-6 else 1.
    angle=math.radians(delta) if field==2 else 0.
    c,s=math.cos(angle),math.sin(angle)
    for mesh,obj in targets.items():
        if profiles.is_mesh_export(settings.engine):
            adjust_native_uv(obj,field,delta,ratio,c,s)
            continue
        records=json.loads(mesh.get('wl_faces','{}'))
        if edit:
            bm=bmesh.from_edit_mesh(mesh)
            layer=bm.faces.layers.int.get('wl_face_id')
            if layer is None:continue
            faces=[(face[layer],face) for face in bm.faces if face.select and not face.hide]
        else:
            layer=mesh.attributes.get('wl_face_id')
            if layer is None:continue
            faces=[(layer.data[face.index].value,face) for face in mesh.polygons]
        changed=set()
        for fid,face in faces:
            key=str(fid)
            record=records.get(key)
            material=mesh.materials[face.material_index] if face.material_index<len(mesh.materials) else None
            texture=material.get('wl_texture') if material else None
            if not texture and not (record and record.get('texture')):continue
            if record is None:
                from dataclasses import asdict
                from itertools import combinations
                vertices=face.verts if edit else (mesh.vertices[i] for i in face.vertices)
                points=[scene.world_point(obj,v.co,obj.get('wl_unit_meters',1.)) for v in vertices]
                for triple in combinations(points,3):
                    if editor.length(editor.cross(editor.sub(triple[1],triple[0]),editor.sub(triple[2],triple[0])))>1e-8:
                        record=asdict(formats.Face(list(triple[::-1]),texture,[0.,0.,0.,1.,1.]))
                        records[key]=record
                        break
                if record is None:continue
            if texture:record['texture']=texture
            projection=record['projection']
            axes=record.get('axes')
            if axes and field<2:
                axes[field][3]+=delta
                projection[field]=axes[field][3]
            elif axes and field==2:
                u,v=[axis[:3] for axis in axes]
                axes[0][:3]=[a*c-b*s for a,b in zip(u,v)]
                axes[1][:3]=[a*s+b*c for a,b in zip(u,v)]
                projection[field]+=delta
            elif field>=3:
                projection[field]*=ratio
            else:
                projection[field]+=delta
            changed.add(fid)
        if not changed:continue
        previous=mesh.get('wl_faces','{}')
        mesh['wl_faces']=json.dumps(records)
        try:
            if edit:editor.apply_edit_uv(obj,face_ids=changed)
            else:editor.apply_uv(obj,settings.engine,face_ids=changed)
        except (ValueError,RuntimeError):
            mesh['wl_faces']=previous
            raise
    if context.screen:
        for area in context.screen.areas:
            if area.type=='VIEW_3D':area.tag_redraw()


def adjust_native_uv(obj,field,delta,ratio,c,s):
    """Transform the active UV map without discarding imported face coordinates."""
    import bmesh

    def transform(uv, material_index):
        slots=obj.data.materials
        mat=slots[material_index] if material_index<len(slots) else None
        width=(mat.get('wl_width',64) or 64) if mat else 64
        height=(mat.get('wl_height',64) or 64) if mat else 64
        u,v=uv.x*width,(1-uv.y)*height
        if field==0:u+=delta
        elif field==1:v+=delta
        elif field==2:u,v=u*c-v*s,u*s+v*c
        elif field==3:u/=ratio
        else:v/=ratio
        return u/width,1-v/height

    if obj.mode=='EDIT':
        bm=bmesh.from_edit_mesh(obj.data)
        layers=bm.loops.layers.uv
        layer=layers.get('wavelength') or layers.active
        if layer is None:return
        for face in bm.faces:
            if face.select and not face.hide:
                for loop in face.loops:loop[layer].uv=transform(loop[layer].uv,face.material_index)
        bmesh.update_edit_mesh(obj.data,loop_triangles=False,destructive=False)
    else:
        layer=obj.data.uv_layers.get('wavelength') or obj.data.uv_layers.active
        if layer is None:return
        for face in obj.data.polygons:
            for index in face.loop_indices:
                layer.data[index].uv=transform(layer.data[index].uv,face.material_index)
        obj.data.update()
    editor.activate_mapping_uv(obj.data)


def draw_mapping(layout,settings):
    layout.prop(settings,'live_mapping_adjustment')
    for name in MAPPING_FIELDS:
        layout.prop(settings,'adjust_'+name)
    if settings.status=='Finalize generated geometry before adjusting its mapping':
        layout.label(text=settings.status,icon='INFO')

def face_axes(face,projection):
    from mathutils import Vector
    normal=Vector(face.plane()[0]);u=(Vector(face.points[1])-Vector(face.points[0])).normalized();v=normal.cross(u).normalized()
    angle=math.radians(projection[2]);c=math.cos(angle);s=math.sin(angle)
    a=u*c-v*s;b=u*s+v*c
    return [[*a,projection[0]],[*b,projection[1]]]


def project_mesh_uv(context,obj,material):
    """Project selected native mesh faces without a BSP face/convexity contract."""
    settings=context.scene.wavelength
    projection=[settings.shift_u,settings.shift_v,settings.texture_rotation,settings.texture_scale_u,settings.texture_scale_v]
    if abs(projection[3])<1e-6 or abs(projection[4])<1e-6:raise ValueError('Texture scales must be nonzero')
    unit=obj.get('wl_unit_meters',profiles.unit_meters(settings))
    normal_matrix=obj.matrix_world.to_3x3().inverted().transposed()
    def coordinates(point,normal,index):
        slot=material or (obj.data.materials[index] if index<len(obj.data.materials) else None)
        width=(slot.get('wl_width',64) or 64) if slot else 64
        height=(slot.get('wl_height',64) or 64) if slot else 64
        axes=formats.quake_axes(normal,projection);point=obj.matrix_world@point/unit
        return ((sum(axes[0][j]*point[j] for j in range(3))/projection[3]+axes[0][3])/width,
                1-(sum(axes[1][j]*point[j] for j in range(3))/projection[4]+axes[1][3])/height)
    if obj.mode=='EDIT':
        import bmesh
        bm=bmesh.from_edit_mesh(obj.data);layer=bm.loops.layers.uv.get('wavelength') or bm.loops.layers.uv.new('wavelength')
        for face in bm.faces:
            if not face.select or face.hide:continue
            normal=(normal_matrix@face.normal).normalized()
            for loop in face.loops:loop[layer].uv=coordinates(loop.vert.co,normal,face.material_index)
        bmesh.update_edit_mesh(obj.data,loop_triangles=False,destructive=False)
    else:
        layer=obj.data.uv_layers.get('wavelength') or obj.data.uv_layers.new(name='wavelength')
        for face in obj.data.polygons:
            normal=(normal_matrix@face.normal).normalized()
            for index in face.loop_indices:layer.data[index].uv=coordinates(obj.data.vertices[obj.data.loops[index].vertex_index].co,normal,face.material_index)
        obj.data.update()
    editor.activate_mapping_uv(obj.data)

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
    """Browser Apply uses the same assignment path as viewport stamps/drops."""
    from . import primitive_ui,asset_placement
    with viewport(context):
        ctx=bpy.context;edit=ctx.mode=='EDIT_MESH'
        scope=asset_placement.resolved_scope(ctx)
        objects=list(ctx.objects_in_mode_unique_data) if edit else list(ctx.selected_objects)
        targets=[];seen=set()
        for obj in objects:
            root=primitive_ui.root_for(obj)
            candidates=primitive_ui.parts_for(root) if root and root.get('wl_assembly_locked',True) and not edit else [obj]
            for target in candidates:
                if target.type=='MESH' and target.as_pointer() not in seen:
                    seen.add(target.as_pointer());targets.append(target)
        if not targets:raise ValueError('Select mesh objects or faces in the viewport')
        if not edit and scope=='SURFACE':
            raise ValueError('Enter Edit Mode and select faces, or click a surface in the viewport')
        if edit and scope!='OBJECT':
            import bmesh
            targets=[o for o in targets if any(f.select and not f.hide for f in bmesh.from_edit_mesh(o.data).faces)]
            if not targets:raise ValueError('Select at least one visible face')
        for target in targets:
            asset_placement.paint(ctx,target,-1,material,'SELECTED' if edit and scope!='OBJECT' else 'OBJECT')

def read_source_face_settings(settings, metadata):
    if not profiles.is_source(settings.engine):
        return
    metadata=metadata or {}
    try:
        lightmap=int(metadata.get('lightmapscale','16'))
    except (ValueError,TypeError):
        lightmap=16
    settings.texture_lightmap=lightmap
    settings.texture_smoothing_groups=str(metadata.get('smoothing_groups','0'))
    settings.texture_contents=str(metadata.get('contents',''))
    settings.texture_surface_flags=str(metadata.get('flags',''))


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
    read_source_face_settings(s, record.get('vmf'))
    context.scene['_wl_asset_clipboard']=json.dumps(dict(engine=s.engine,category='MATERIAL',path=name))
    s.asset_browser_section='TEXTURES';s.status='Holding texture: '+name
    from . import asset_browser
    asset_browser.reveal_texture(context,name,mat)

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

def source_mask(text, label):
    try:
        value = int(text, 10)
    except ValueError:
        raise ValueError(f'Enter a decimal {label} mask') from None
    if not -(1 << 31) <= value < (1 << 32):
        raise ValueError(f'The {label} mask must fit in 32 bits')
    # VBSP parses the decimal value as a signed integer.
    return str(value - (1 << 32) if value >= (1 << 31) else value)


def source_face_settings(settings, fields):
    values={}
    for field in fields:
        if field=='lightmapscale':
            values[field]=str(settings.texture_lightmap)
        elif field=='smoothing_groups':
            values[field]=source_mask(settings.texture_smoothing_groups, 'smoothing group')
        else:
            mask=settings.texture_contents if field=='contents' else settings.texture_surface_flags
            values[field]=source_mask(mask, field) if mask.strip() else None
    return values


def apply_source_face_setting(context, objects, edit, values):
    """Write a Source face setting independently of material and projection."""
    from dataclasses import asdict
    from .edit_safety import topology_modal_active

    settings=context.scene.wavelength
    if not profiles.is_source(settings.engine):
        raise ValueError('Source face settings require a Source 1 profile')
    if topology_modal_active(context):
        raise ValueError('Finish the current mesh operation before changing Source face settings')
    if any(any(mod.show_viewport for mod in obj.modifiers) for obj in objects):
        raise ValueError('Finalize generated geometry before changing Source face settings')

    if edit:bpy.ops.object.mode_set(mode='OBJECT')
    try:
        updates={}
        for obj in objects:
            mesh=obj.data
            if mesh in updates:continue
            indices=[p.index for p in mesh.polygons if not edit or (p.select and not p.hide)]
            if not indices:continue
            faces=scene.brush_from_object(obj,settings.engine,require_texture=False)
            ids=[datum.value for datum in mesh.attributes['wl_face_id'].data]
            by_id=dict(zip(sorted(ids),faces))
            records=json.loads(mesh.get('wl_faces','{}'))
            for index in indices:
                fid=ids[index]
                record=records.get(str(fid))
                if record is None:record=asdict(by_id[fid])
                metadata=dict(record.get('vmf') or {})
                for key,value in values.items():
                    if value is None:
                        metadata.pop(key,None)
                    else:
                        metadata[key]=value
                record['vmf']=metadata
                records[str(fid)]=record
            updates[mesh]=records
        if not updates:raise ValueError('Select a brush face')
        for mesh,records in updates.items():
            mesh['wl_faces']=json.dumps(records)
    finally:
        if edit:bpy.ops.object.mode_set(mode='EDIT')


def draw_source_face_settings(layout,settings):
    row=layout.row(align=True)
    row.prop(settings,'texture_lightmap')
    row.operator('wavelength.apply_texture',text='Apply Scale').lightmap_only=True
    row=layout.row(align=True)
    row.prop(settings,'texture_smoothing_groups')
    row.operator('wavelength.apply_texture',text='Apply Groups').smoothing_only=True
    for field, flag in (('texture_contents','CONTENTS'), ('texture_surface_flags','FLAGS')):
        row=layout.row(align=True)
        row.prop(settings,field)
        row.operator('wavelength.apply_texture',text='Apply').face_flag=flag
    layout.operator('wavelength.apply_texture',text='Apply All Face Settings').face_flag='ALL'


class WL_PT_surface(bpy.types.Panel):
    bl_label='Texture Settings';bl_space_type='FILE_BROWSER';bl_region_type='HEADER'
    bl_ui_units_x=24
    def draw(self,context):
        l=self.layout;s=context.scene.wavelength
        from . import texture_layout
        l.label(text='Edit Mode: selected faces')
        l.label(text='Object Mode: whole selected objects')
        l.prop(s,'texture')
        draw_mapping(l,s)
        if profiles.uses_valve_axes(s.engine):l.prop(s,'texture_alignment')
        if profiles.is_source(s.engine):draw_source_face_settings(l,s)
        row=l.row(align=True);row.operator('wavelength.read_face_texture',text='Read Face');row.operator('wavelength.apply_texture',text='Apply Mapping').mapping_only=True
        from .ui import _draw_face_actions
        _draw_face_actions(l);l.prop(s,'live_texture_reproject')
        for actions in [[('FIT','Fit'),('CENTER','Center')],[('LEFT','Left'),('RIGHT','Right'),('TOP','Top'),('BOTTOM','Bottom')]]:
            row=l.row(align=True)
            for action,label in actions:row.operator('wavelength.surface_align',text=label).action=action
        texture_layout.draw(l,context)

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
    from . import texture_layout
    for cls in CLASSES:bpy.utils.register_class(cls)
    texture_layout.register()
def unregister():
    from . import texture_layout
    texture_layout.unregister()
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)
