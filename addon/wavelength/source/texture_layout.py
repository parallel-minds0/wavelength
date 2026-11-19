"""Direct face UV tools with an affine projection path for Valve brushes."""
import json
import math
from dataclasses import asdict
from itertools import count

import bmesh
import bpy
from bpy_extras.view3d_utils import location_3d_to_region_2d
from mathutils import Vector

from . import editor, formats, profiles, workspace

_UNDO_LAYER='wl_texture_layout_version'
_versions=count(1)
_undo_records={}


def remember_projection(obj,bm,faces,before):
    """Pair serialized projections with undoable per-face BMesh markers."""
    ids=bm.faces.layers.int.get('wl_face_id')
    if ids is None:return
    after=json.loads(obj.data.get('wl_faces','{}'))
    before=json.loads(before or '{}')
    keys={str(face[ids]) for face in faces}
    keys={key for key in keys if before.get(key)!=after.get(key)}
    if not keys:return
    history=_undo_records.setdefault(obj.data.name_full,{})
    markers=bm.faces.layers.int.get(_UNDO_LAYER) or bm.faces.layers.int.new(_UNDO_LAYER)
    ids=bm.faces.layers.int['wl_face_id']
    version=next(_versions)
    for face in bm.faces:
        key=str(face[ids])
        if key not in keys:continue
        old=face[markers]
        versions,_=history.get(key,({},old))
        versions[old]=before.get(key)
        versions[version]=after.get(key)
        history[key]=(versions,version)
        face[markers]=version
    bmesh.update_edit_mesh(obj.data,loop_triangles=False,destructive=False)


@bpy.app.handlers.persistent
def restore_projection(_):
    for name,history in _undo_records.items():
        mesh=bpy.data.meshes.get(name)
        if mesh is None:continue
        if mesh.is_editmode:
            bm=bmesh.from_edit_mesh(mesh)
            ids=bm.faces.layers.int.get('wl_face_id')
            marks=bm.faces.layers.int.get(_UNDO_LAYER)
            if ids is None:continue
            markers={str(face[ids]):face[marks] if marks else 0 for face in bm.faces}
        else:
            ids=mesh.attributes.get('wl_face_id')
            marks=mesh.attributes.get(_UNDO_LAYER)
            if ids is None:continue
            markers={str(entry.value):marks.data[i].value if marks else 0 for i,entry in enumerate(ids.data)}
        records=json.loads(mesh.get('wl_faces','{}'))
        changed=False
        for key,(versions,previous) in history.items():
            marker=markers.get(key)
            if marker==previous or marker not in versions:continue
            if versions[marker] is None:records.pop(key,None)
            else:records[key]=versions[marker]
            history[key]=(versions,marker)
            changed=True
        if changed:mesh['wl_faces']=json.dumps(records)


@bpy.app.handlers.persistent
def clear_projection_history(_):
    _undo_records.clear()


def target(context):
    from .edit_safety import topology_modal_active

    obj=context.edit_object or context.view_layer.objects.active
    engine=context.scene.wavelength.engine
    if (not obj or obj.type!='MESH' or obj.mode!='EDIT' or not workspace.active(context,'textures')
            or any(mod.show_viewport for mod in obj.modifiers)
            or obj.get('wl_source_displacement') or obj.get('wl_custom_model_owner')
            or obj.get('wl_role')=='MODEL_SOURCE' or topology_modal_active(context)):
        return None
    if profiles.is_mesh_export(engine) or (profiles.uses_valve_axes(engine) and obj.get('wl_role')=='BRUSH'):
        return obj
    return None


def selection(obj):
    bm=bmesh.from_edit_mesh(obj.data)
    faces=[face for face in bm.faces if face.select and not face.hide]
    layers=bm.loops.layers.uv
    layer=layers.get('wavelength') or layers.active
    if not faces or layer is None:
        raise ValueError('Select textured faces with an existing UV map')
    return bm,faces,layer


def material(obj,face):
    slots=obj.data.materials
    return slots[face.material_index] if face.material_index<len(slots) else None


def active_material(obj):
    face=bmesh.from_edit_mesh(obj.data).faces.active
    return material(obj,face) if face else obj.active_material


def dimensions(mat):
    return ((mat.get('wl_width',64) or 64,mat.get('wl_height',64) or 64)
            if mat else (64,64))


def affine(points,uvs):
    """Fit world-space UV gradients on a nondegenerate planar face."""
    origin=points[0]
    a=max((point-origin for point in points[1:]),key=lambda v:v.length_squared)
    if a.length<1e-8:raise ValueError('Face has no measurable edge')
    i=next(i for i,point in enumerate(points) if point-origin==a)
    j=max(range(1,len(points)),key=lambda k:a.cross(points[k]-origin).length_squared)
    b=points[j]-origin
    normal=a.cross(b)
    if normal.length<1e-8:raise ValueError('Face is degenerate')
    ga=b.cross(normal)/normal.length_squared
    gb=normal.cross(a)/normal.length_squared
    gradients=[ga*(uvs[i][k]-uvs[0][k])+gb*(uvs[j][k]-uvs[0][k]) for k in range(2)]
    offsets=[uvs[0][k]-gradients[k].dot(origin) for k in range(2)]
    if any(abs(gradient.dot(point)+offset-uv[k])>1e-4 for point,uv in zip(points,uvs)
           for k,(gradient,offset) in enumerate(zip(gradients,offsets))):
        raise ValueError('Mapping is not affine on this face')
    return gradients,offsets


def apply(context,obj,bm,layer,updates):
    """Validate every brush projection before changing any selected face."""
    native=profiles.is_mesh_export(context.scene.wavelength.engine)
    if not native:
        ids=bm.faces.layers.int.get('wl_face_id')
        if ids is None:raise ValueError('Brush has no face IDs')
        records=json.loads(obj.data.get('wl_faces','{}'))
        unit=obj.get('wl_unit_meters',1.)
        for face,uvs in updates:
            points=[obj.matrix_world@loop.vert.co/unit for loop in face.loops]
            gradients,offsets=affine(points,uvs)
            width,height=dimensions(material(obj,face))
            gradients=[gradients[0]*width,-gradients[1]*height]
            shifts=[offsets[0]*width,(1-offsets[1])*height]
            if min(gradient.length for gradient in gradients)<1e-8:
                raise ValueError('Mapping collapses a texture axis')
            key=str(face[ids])
            record=records.get(key)
            if record is None:
                mat=material(obj,face)
                name=mat.get('wl_texture','') if mat else ''
                if not name:raise ValueError('Assign an engine texture first')
                record=asdict(formats.Face([list(p) for p in points[:3][::-1]],name,[0,0,0,1,1]))
                records[key]=record
            record['projection']=[*shifts,0.,*(1/gradient.length for gradient in gradients)]
            record['axes']=[[*gradient.normalized(),shift] for gradient,shift in zip(gradients,shifts)]
        obj.data['wl_faces']=json.dumps(records)
    for face,uvs in updates:
        for loop,uv in zip(face.loops,uvs,strict=True):loop[layer].uv=uv
    bmesh.update_edit_mesh(obj.data,loop_triangles=False,destructive=False)
    editor.activate_mapping_uv(obj.data)


def continue_edge(obj,source,destination,layer):
    common=set(source.edges).intersection(destination.edges)
    if len(common)!=1:raise ValueError('Faces must share exactly one edge')
    if material(obj,source)!=material(obj,destination):raise ValueError('Faces must use the same material')
    edge=next(iter(common))
    world=obj.matrix_world
    pivot=world@edge.verts[0].co
    axis=((world@edge.verts[1].co)-pivot).normalized()
    normals=world.to_3x3().inverted().transposed()
    a,b=(normals@destination.normal).normalized(),(normals@source.normal).normalized()
    angle=math.atan2(axis.dot(a.cross(b)),a.dot(b))
    from mathutils import Quaternion
    fold=Quaternion(axis,angle)
    gradients,offsets=affine([world@loop.vert.co for loop in source.loops],[loop[layer].uv for loop in source.loops])
    return [tuple(g.dot(pivot+fold@((world@loop.vert.co)-pivot))+o for g,o in zip(gradients,offsets))
            for loop in destination.loops]


def screen_axes(context,obj,face,layer):
    points=[obj.matrix_world@loop.vert.co for loop in face.loops]
    center=sum(points,Vector((0.,0.,0.)))/len(points)
    def project(point):
        return location_3d_to_region_2d(context.region,context.region_data,point)
    screen=project(center)
    if screen is None:raise ValueError('The active face is outside the view')
    gu,gv=affine(points,[loop[layer].uv for loop in face.loops])[0]
    normal=gu.cross(gv)
    if normal.length<1e-8:raise ValueError('Mapping collapses a texture axis')
    axes=[]
    for direction in (gv.cross(normal),gu.cross(normal)):
        end=project(center+direction.normalized()*.25)
        if end is None or (end-screen).length<.001:
            raise ValueError('Face is edge-on to the view')
        axes.append((end-screen).normalized())
    return screen,axes


def hotspot_uv(obj,face,regions):
    loops=list(face.loops)
    points=[obj.matrix_world@loop.vert.co for loop in loops]
    longest=max((b-a for a,b in zip(points,points[1:]+points[:1])),key=lambda v:v.length_squared)
    u=longest.normalized()
    normal=(obj.matrix_world.to_3x3().inverted().transposed()@face.normal).normalized()
    v=normal.cross(u).normalized()
    xy=[(p.dot(u),p.dot(v)) for p in points]
    left,bottom=map(min,zip(*xy))
    width=max(x for x,y in xy)-left
    height=max(y for x,y in xy)-bottom
    if min(width,height)<1e-8:raise ValueError('Hotspot needs a face with measurable width and height')
    tex_width,tex_height=dimensions(material(obj,face))
    candidates=[]
    for rect in regions:
        x0,y0,x1,y1=rect.minimum[0],rect.minimum[1],rect.maximum[0],rect.maximum[1]
        if x1<=x0 or y1<=y0:continue
        aspect=(x1-x0)*tex_width/((y1-y0)*tex_height)
        for rotated in (False,True):
            error=abs(math.log((width/height)*(aspect if rotated else 1/aspect)))
            candidates.append((error,rotated,x0,y0,x1,y1))
    if not candidates:raise ValueError('Add a valid hotspot rectangle to this material')
    _,rotated,x0,y0,x1,y1=min(candidates)
    result=[]
    for x,y in xy:
        a,b=(x-left)/width,(y-bottom)/height
        if rotated:a,b=1-b,a
        result.append((x0+a*(x1-x0),y0+b*(y1-y0)))
    return result


class WL_PG_hotspot(bpy.types.PropertyGroup):
    label:bpy.props.StringProperty(name='Name',default='Trim')
    minimum:bpy.props.FloatVectorProperty(name='Min UV',size=2,min=0,max=1)
    maximum:bpy.props.FloatVectorProperty(name='Max UV',size=2,min=0,max=1,default=(1,1))


class WL_OT_hotspot_region(bpy.types.Operator):
    bl_idname='wavelength.hotspot_region';bl_label='Edit Hotspot Regions';bl_options={'UNDO'}
    index:bpy.props.IntProperty(default=-1)
    def execute(self,context):
        obj=target(context)
        mat=active_material(obj) if obj else None
        if not mat or mat.library:return {'CANCELLED'}
        regions=mat.wl_hotspots
        if self.index<0:regions.add()
        elif self.index<len(regions):regions.remove(self.index)
        return {'FINISHED'}


class WL_OT_face_layout(bpy.types.Operator):
    bl_idname='wavelength.face_texture_layout';bl_label='Face Texture Layout';bl_options={'UNDO'}
    action:bpy.props.EnumProperty(items=[('EDGE','Continue Across Edge',''),('HOTSPOT','Apply Best Hotspot','')])
    @classmethod
    def poll(cls,context):return target(context) is not None
    def execute(self,context):
        obj=target(context)
        try:
            bm,faces,layer=selection(obj)
            bm.normal_update()
            if self.action=='EDGE':
                source=bm.faces.active
                if len(faces)!=2 or source not in faces:
                    raise ValueError('Select two adjoining faces, with the reference face active')
                destination=next(face for face in faces if face!=source)
                updates=[(destination,continue_edge(obj,source,destination,layer))]
            else:
                updates=[]
                for face in faces:
                    mat=material(obj,face)
                    updates.append((face,hotspot_uv(obj,face,mat.wl_hotspots if mat else ())))
            before=obj.data.get('wl_faces')
            apply(context,obj,bm,layer,updates)
            if not profiles.is_mesh_export(context.scene.wavelength.engine):
                remember_projection(obj,bm,[face for face,_ in updates],before)
        except (ValueError,RuntimeError) as exc:
            self.report({'ERROR'},str(exc))
            return {'CANCELLED'}
        return {'FINISHED'}


class WL_OT_texture_handle(bpy.types.Operator):
    bl_idname='wavelength.texture_handle';bl_label='Drag Texture Handle';bl_options={'UNDO'}
    action:bpy.props.EnumProperty(items=[(key,key,'') for key in ('U','V','SCALE','ROTATE')])
    def invoke(self,context,event):
        self.obj=target(context)
        if not self.obj:return {'CANCELLED'}
        try:
            self.bm,faces,self.layer=selection(self.obj)
            active=self.bm.faces.active
            self.center,self.axes=screen_axes(context,self.obj,active if active in faces else faces[0],self.layer)
        except ValueError as exc:
            self.report({'ERROR'},str(exc))
            return {'CANCELLED'}
        self.original=[(face,[loop[self.layer].uv.copy() for loop in face.loops]) for face in faces]
        self.records=self.obj.data.get('wl_faces')
        layers=self.obj.data.uv_layers
        self.active_uv=layers.active.name if layers.active else ''
        self.render_uv=next((layer.name for layer in layers if layer.active_render),'')
        self.mouse=Vector((event.mouse_region_x,event.mouse_region_y))
        context.window_manager.modal_handler_add(self)
        context.workspace.status_text_set('Drag to adjust texture · Ctrl snaps · Esc cancels')
        return {'RUNNING_MODAL'}
    def modal(self,context,event):
        if event.type in {'ESC','RIGHTMOUSE'} or target(context)!=self.obj:
            self.cancel(context)
            return {'CANCELLED'}
        if ((event.type in {'RET','NUMPAD_ENTER'} and event.value=='PRESS')
                or (event.type=='LEFTMOUSE' and event.value=='RELEASE')):
            if not profiles.is_mesh_export(context.scene.wavelength.engine):
                remember_projection(self.obj,self.bm,[face for face,_ in self.original],self.records)
            context.workspace.status_text_set(None)
            return {'FINISHED'}
        if event.type=='MOUSEMOVE':
            position=Vector((event.mouse_region_x,event.mouse_region_y))
            motion=position-self.mouse
            angle=(position-self.center).angle_signed(self.mouse-self.center,0.)
            if event.ctrl:angle=round(angle/math.radians(15))*math.radians(15)
            scale_direction=(self.mouse-self.center).normalized()
            distance=motion.dot(scale_direction)
            scale=2**max(-12,min(12,round(distance/32)/4 if event.ctrl else distance/128))
            c,s=math.cos(angle),math.sin(angle)
            updates=[]
            for face,values in self.original:
                width,height=dimensions(material(self.obj,face))
                pivot=sum(values,Vector((0.,0.)))/len(values)
                texels=motion.dot(self.axes[0 if self.action=='U' else 1])
                if event.ctrl:texels=round(texels)
                result=[]
                for uv in values:
                    x,y=(uv-pivot)
                    if self.action=='U':x+=texels/width
                    elif self.action=='V':y-=texels/height
                    elif self.action=='SCALE':x,y=x*scale,y*scale
                    else:
                        x,y=x*c-y*s*height/width,x*s*width/height+y*c
                    result.append(pivot+Vector((x,y)))
                updates.append((face,result))
            try:apply(context,self.obj,self.bm,self.layer,updates)
            except (ValueError,RuntimeError) as exc:
                self.report({'WARNING'},str(exc))
                self.cancel(context)
                return {'CANCELLED'}
        return {'RUNNING_MODAL'}
    def cancel(self,context):
        context.workspace.status_text_set(None)
        if not self.bm.is_valid:return
        for face,values in self.original:
            if face.is_valid:
                for loop,uv in zip(face.loops,values):loop[self.layer].uv=uv
        if self.records is not None:self.obj.data['wl_faces']=self.records
        else:self.obj.data.pop('wl_faces',None)
        bmesh.update_edit_mesh(self.obj.data,loop_triangles=False,destructive=False)
        layers=self.obj.data.uv_layers
        if self.active_uv in layers:layers.active=layers[self.active_uv]
        if self.render_uv in layers:layers[self.render_uv].active_render=True


class WL_GGT_texture_handles(bpy.types.GizmoGroup):
    bl_idname='WL_GGT_texture_handles';bl_label='Face Texture Handles'
    bl_space_type='VIEW_3D';bl_region_type='WINDOW';bl_options={'PERSISTENT'}
    @classmethod
    def poll(cls,context):
        return context.scene.wl_show_texture_handles and target(context) is not None
    def setup(self,context):
        for action,icon,color in [('U','TRIA_RIGHT',(1,.25,.2)),('V','TRIA_UP',(.3,1,.3)),
                                  ('SCALE','FULLSCREEN_ENTER',(.35,.65,1)),('ROTATE','DRIVER_ROTATIONAL_DIFFERENCE',(1,.75,.3))]:
            gizmo=self.gizmos.new('GIZMO_GT_button_2d')
            gizmo.icon=icon;gizmo.scale_basis=12
            gizmo.color=color;gizmo.color_highlight=color;gizmo.alpha=.8;gizmo.alpha_highlight=1
            gizmo.target_set_operator(WL_OT_texture_handle.bl_idname).action=action
    def draw_prepare(self,context):
        obj=target(context)
        if obj is None:return
        try:
            bm=bmesh.from_edit_mesh(obj.data)
            face=bm.faces.active
            layers=bm.loops.layers.uv
            layer=layers.get('wavelength') or layers.active
            if not face or not face.select or face.hide or layer is None:
                raise ValueError('No active mapped face')
            point,(u,v)=screen_axes(context,obj,face,layer)
        except ValueError:
            for gizmo in self.gizmos:gizmo.hide=True
            return
        for gizmo,direction in zip(self.gizmos,(u,v,(u+v).normalized(),-u)):
            gizmo.hide=False
            position=point+direction*38
            gizmo.matrix_basis.translation=(*position,0)


def draw(layout,context):
    obj=target(context)
    if not obj:return
    box=layout.box()
    box.prop(context.scene,'wl_show_texture_handles',text='Viewport Texture Handles')
    box.operator(WL_OT_face_layout.bl_idname,text='Continue Across Edge').action='EDGE'
    box.operator(WL_OT_face_layout.bl_idname,text='Apply Best Hotspot').action='HOTSPOT'
    mat=active_material(obj)
    if mat and not mat.library:
        for index,region in enumerate(mat.wl_hotspots):
            row=box.row(align=True)
            row.prop(region,'label',text='')
            row.operator(WL_OT_hotspot_region.bl_idname,text='',icon='X').index=index
            box.prop(region,'minimum')
            box.prop(region,'maximum')
        box.operator(WL_OT_hotspot_region.bl_idname,text='Add Hotspot Region',icon='ADD')


class WL_PT_texture_layout(bpy.types.Panel):
    bl_label='Texture Layout';bl_idname='WL_PT_texture_layout'
    bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='Item'
    @classmethod
    def poll(cls,context):return target(context) is not None
    def draw(self,context):draw(self.layout,context)


CLASSES=(WL_PG_hotspot,WL_OT_hotspot_region,WL_OT_face_layout,WL_OT_texture_handle,
         WL_GGT_texture_handles,WL_PT_texture_layout)


def register():
    for cls in CLASSES:bpy.utils.register_class(cls)
    bpy.types.Material.wl_hotspots=bpy.props.CollectionProperty(type=WL_PG_hotspot)
    bpy.types.Scene.wl_show_texture_handles=bpy.props.BoolProperty(default=False)
    bpy.app.handlers.undo_post.append(restore_projection)
    bpy.app.handlers.redo_post.append(restore_projection)
    bpy.app.handlers.load_post.append(clear_projection_history)


def unregister():
    bpy.app.handlers.load_post.remove(clear_projection_history)
    bpy.app.handlers.redo_post.remove(restore_projection)
    bpy.app.handlers.undo_post.remove(restore_projection)
    clear_projection_history(None)
    del bpy.types.Scene.wl_show_texture_handles
    del bpy.types.Material.wl_hotspots
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)
