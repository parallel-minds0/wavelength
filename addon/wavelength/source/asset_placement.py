"""Click-to-paint surfaces and click-to-place entities from the native browser."""
import json
from dataclasses import asdict
import bpy
from mathutils import Vector
from bpy_extras import view3d_utils
from . import workspace,profiles,textures,scene,formats,editor,tool_snap

_active=None
_dismissed=None
_keymaps=[]

def resolved_scope(context):
    scope=context.window_manager.wl_texture_apply_scope
    return ('SURFACE' if context.mode=='EDIT_MESH' else 'OBJECT') if scope=='AUTO' else scope

def auto_place():
    prune_session()
    if _active:return .15
    for window in bpy.context.window_manager.windows:
        with bpy.context.temp_override(window=window):
            if workspace.active():_auto_window(bpy.context)
        if _active:break
    return .15

# docs:begin session-recovery
def prune_session():
    """Dispose of resources if Blender invalidated the session's RNA operator."""
    if _active:
        # The plain Python session survives undo; the operator wrapper may not.
        try:_active.operator.properties
        except ReferenceError:_active.finish(bpy.context)
# docs:end session-recovery

@bpy.app.handlers.persistent
def clear_session(_unused=None):
    if _active:_active.finish(bpy.context)

def _auto_window(context):
    if not context.screen:return .15
    for area in context.screen.areas:
        if area.type!='FILE_BROWSER' or area.ui_type!='ASSETS':continue
        region=next((r for r in area.regions if r.type=='WINDOW'),None)
        if not region:continue
        with context.temp_override(area=area,region=region):
            try:row=payload(context)
            except (ValueError,AttributeError,RuntimeError):continue
            if row.get('engine')!=context.scene.wavelength.engine:continue
            if context.scene.wavelength.asset_browser_section not in {'TEXTURES','ENTITIES'}:continue
            key=(context.scene.as_pointer(),json.dumps(row,sort_keys=True))
            if key==_dismissed:continue
            bpy.ops.wavelength.click_place('INVOKE_DEFAULT')
            break
    return .15

def payload(context):
    from .asset_browser import selected_asset
    asset=selected_asset(context)
    if not asset:raise ValueError('Select a texture or point entity in the Asset Browser')
    block=asset.local_id
    if block is not None and block.get('wl_entity_browser_template'):
        return dict(category='ENTITY',path=block['wl_entity_browser_template'],engine=block.get('wl_entity_browser_profile'))
    if block is not None and block.get('wl_asset'):
        row=json.loads(block['wl_asset'])
        if row['category'] in {'ENTITY','MATERIAL','DECAL'}:
            return dict(category='MATERIAL' if isinstance(block,bpy.types.Material) else row['category'],path=block.get('wl_texture',row['path']),engine=row['engine'],material=block.name if isinstance(block,bpy.types.Material) else '')
    if asset.id_type=='MATERIAL':
        return dict(category='MATERIAL',path=block.get('wl_texture',block.name) if block else asset.name,
                    engine=context.scene.wavelength.engine,material=block.name if block else '',library=asset.full_library_path if block is None else '',asset_name=asset.name)
    raise ValueError('Click placement supports textures and point entities')

def material(context,row):
    mat=bpy.data.materials.get(row.get('material',''))
    if mat is None and row.get('library'):
        with bpy.data.libraries.load(row['library'],link=False) as (available,requested):
            if row['asset_name'] not in available.materials:raise ValueError('Selected material is missing from its library')
            requested.materials=[row['asset_name']]
        mat=requested.materials[0];row['material']=mat.name
    if mat is None:mat=textures.material(context.scene.wavelength,row['path']);row['material']=mat.name
    if mat.library:mat=mat.copy();row['material']=mat.name
    profile=mat.get('wl_asset_profile')
    if profile and profile!=context.scene.wavelength.engine:raise ValueError('Texture belongs to another engine profile')
    if mat.get('wl_texture'):textures.realize_material(context.scene.wavelength,mat)
    return mat

def paint(context,obj,index,mat,scope='SURFACE'):
    """Assign material indices, never replace a shared material slot's contents."""
    from . import asset_browser,primitive_ui
    if obj.type!='MESH':raise ValueError('Click a mesh surface')
    if obj.get('wl_asset_template') or obj.get('wl_entity_browser_template') or obj.get('wl_entity_icon_reference'):raise ValueError('Editor helpers cannot be textured')
    targets=[obj]
    root=primitive_ui.root_for(obj)
    if scope=='OBJECT' and root and root.get('wl_assembly_locked',True):targets=list(primitive_ui.parts_for(root))
    busy=asset_browser._BUSY;asset_browser._BUSY=True
    try:
        for target in targets:
            if target.type!='MESH':continue
            if scope in {'SURFACE','SELECTED'}:
                stable={'ARMATURE','CAST','CORRECTIVE_SMOOTH','DISPLACE','LAPLACIANSMOOTH','LATTICE','MESH_DEFORM','SHRINKWRAP','SIMPLE_DEFORM','SMOOTH','WARP','WAVE'}
                if any(m.show_viewport and m.type not in stable for m in target.modifiers):raise ValueError('Finalize generated geometry before painting individual surfaces')
                if target.mode=='EDIT':
                    import bmesh
                    count=len(bmesh.from_edit_mesh(target.data).faces)
                else:count=len(target.data.polygons)
                if scope=='SURFACE' and not 0<=index<count:raise ValueError('Finalize generated geometry before painting individual surfaces')
            slot=next((i for i,m in enumerate(target.data.materials) if m==mat),None)
            if slot is None:slot=len(target.data.materials);target.data.materials.append(mat)
            records=json.loads(target.data.get('wl_faces','{}'));name=mat.get('wl_texture','')
            if target.mode=='EDIT':
                import bmesh
                bm=bmesh.from_edit_mesh(target.data);bm.faces.ensure_lookup_table()
                if scope=='SURFACE' and not 0<=index<len(bm.faces):raise ValueError('Finalize generated geometry before painting individual surfaces')
                faces=[face for face in bm.faces if face.select and not face.hide] if scope=='SELECTED' else [bm.faces[index]] if scope=='SURFACE' else list(bm.faces)
                ids=bm.faces.layers.int.get('wl_face_id');uv=bm.loops.layers.uv.get('wavelength')
                if target.get('wl_role')=='BRUSH':uv=uv or bm.loops.layers.uv.new('wavelength')
                for face in faces:
                    face.material_index=slot;fid=str(face[ids]) if ids else None;record=records.get(fid)
                    if record and name:record['texture']=name
                    if uv and target.get('wl_role')=='BRUSH':
                        projection=record.get('projection',[0,0,0,1,1]) if record else [0,0,0,1,1]
                        normal=(target.matrix_world.to_3x3().inverted().transposed()@face.normal).normalized()
                        axes=(record.get('axes') if record else None) or formats.quake_axes(normal,projection)
                        for loop in face.loops:
                            p=target.matrix_world@loop.vert.co/target.get('wl_unit_meters',1.)
                            u=sum(axes[0][j]*p[j] for j in range(3))/projection[3]+axes[0][3]
                            v=sum(axes[1][j]*p[j] for j in range(3))/projection[4]+axes[1][3]
                            loop[uv].uv=(u/mat.get('wl_width',64),1-v/mat.get('wl_height',64))
                bmesh.update_edit_mesh(target.data)
                target.data['wl_faces']=json.dumps(records)
                if target.get('wl_role')!='BRUSH':asset_browser._ensure_mesh_uv(target)
            else:
                if scope=='SURFACE' and not 0<=index<len(target.data.polygons):raise ValueError('Finalize generated geometry before painting individual surfaces')
                indices=[index] if scope=='SURFACE' else list(range(len(target.data.polygons)))
                if target.get('wl_role')=='BRUSH':
                    faces=scene.brush_from_object(target,context.scene.wavelength.engine)
                    records={str(d.value):asdict(f) for d,f in zip(sorted(target.data.attributes['wl_face_id'].data,key=lambda d:d.value),faces)}
                    target.data['wl_faces']=json.dumps(records)
                textures.assign(target,indices,mat)
                if target.get('wl_role')=='BRUSH':editor.apply_uv(target,context.scene.wavelength.engine)
                else:asset_browser._ensure_mesh_uv(target)
            asset_browser._BRUSH_MAT_SIGS[target.as_pointer()]=asset_browser._brush_mat_signature(target)
            from . import node_primitives
            node_primitives.sync_materials(target)
            if target.get('wl_terrain') and scope=='OBJECT':
                target.data.materials[0]=mat
                from . import terrain
                terrain.sync_material(target,force=True)
    finally:asset_browser._BUSY=busy

# docs:begin selected-face-drop
def paint_drop(context,obj,index,mat,scope):
    """Apply a drop to selected edit faces, or fall back to the hit/object scope."""
    if context.mode=='EDIT_MESH' and scope!='OBJECT':
        import bmesh
        # Multi-object Edit Mode owns one BMesh per unique mesh datablock.
        targets=[
            target for target in context.objects_in_mode_unique_data
            if target.type=='MESH' and any(
                face.select and not face.hide
                for face in bmesh.from_edit_mesh(target.data).faces
            )
        ]
        if targets:
            for target in targets:paint(context,target,-1,mat,'SELECTED')
            return
    # No face selection: a drop still has a useful target under the pointer.
    paint(context,obj,index,mat,scope)
# docs:end selected-face-drop

class WL_OT_stamp(bpy.types.Operator):
    bl_idname='wavelength.stamp_asset';bl_label='Place Wavelength Asset';bl_options={'INTERNAL'}
    data:bpy.props.StringProperty();object_name:bpy.props.StringProperty();face:bpy.props.IntProperty(default=-1)
    location:bpy.props.FloatVectorProperty(size=3);scope:bpy.props.StringProperty(default='SURFACE')
    selected_faces:bpy.props.BoolProperty(default=False)
    @classmethod
    def poll(cls,context):return workspace.active(context)
    def execute(self,context):
        try:
            row=json.loads(self.data)
            if row.get('engine')!=context.scene.wavelength.engine:raise ValueError('Select an asset from the current profile')
            if row['category']=='ENTITY':
                if context.mode!='OBJECT':raise ValueError('Enter Object Mode to place entities')
                from .ui import _spawn_point_entity
                obj=_spawn_point_entity(context,row['path']);obj.location=self.location
            else:
                obj=context.scene.objects.get(self.object_name)
                if obj is None:raise ValueError('Click a mesh surface')
                mat=material(context,row)
                (paint_drop if self.selected_faces else paint)(context,obj,self.face,mat,self.scope)
                if mat.get('wl_texture'):context.scene.wavelength.texture=mat['wl_texture']
            context.scene.wavelength.status='Placed '+row['path']
            return {'FINISHED'}
        except (ValueError,RuntimeError,OSError,IndexError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}

class PlacementSession:
    def __init__(self):self.closed=True
    bl_idname='wavelength.click_place';bl_label='Click Place';bl_description='Select a texture/entity, then click the level repeatedly; Surface paints one face, Object paints the object; Esc stops'
    @classmethod
    def poll(cls,context):return workspace.active(context)
    def invoke(self,context,event,operator):
        global _active
        prune_session()
        if _active:
            _active.finish(context);return {'FINISHED'}
        try:self.row=payload(context)
        except ValueError as exc:operator.report({'WARNING'},str(exc));return {'CANCELLED'}
        self.operator=operator
        self.browser=context.area;self.owner=context.scene;self.engine=context.scene.wavelength.engine;self.closed=False;self.point=None
        self.window=context.window;self.work=context.workspace;self.manager=context.window_manager
        self.anchor=context.scene.cursor.location.copy();self.handler=None;self.has_undo=False
        self.drag_start=None;self.dragging=False
        self.timer=context.window_manager.event_timer_add(.2,window=context.window)
        context.window_manager.wl_click_place=True;context.window.cursor_modal_set('PAINT_BRUSH')
        self.handler=bpy.types.SpaceView3D.draw_handler_add(self.draw_cursor,(), 'WINDOW','POST_VIEW')
        context.window_manager.modal_handler_add(operator);_active=self
        self.status(context);return {'RUNNING_MODAL'}
    def status(self,context):
        context.workspace.status_text_set('Click Place: '+self.row['path']+' · '+context.window_manager.wl_texture_apply_scope.title()+' · Esc/right-click stops')
    def finish(self,context):
        global _active,_dismissed
        self.closed=True
        _active=None
        try:_dismissed=(self.owner.as_pointer(),json.dumps(self.row,sort_keys=True))
        except ReferenceError:_dismissed=None
        for action in (
            lambda:bpy.types.SpaceView3D.draw_handler_remove(self.handler,'WINDOW') if self.handler else None,
            lambda:self.manager.event_timer_remove(self.timer) if self.timer else None,
            lambda:setattr(self.manager,'wl_click_place',False),
            lambda:self.window.cursor_modal_restore() if self.window else None,
            lambda:self.work.status_text_set(None) if self.work else None,
        ):
            try:action()
            except (ReferenceError,RuntimeError,ValueError):pass
        self.handler=None;self.timer=None
        if context.screen:
            for area in context.screen.areas:area.tag_redraw()
    def draw_cursor(self):
        if self.point is None:return
        import gpu
        from gpu_extras.batch import batch_for_shader
        p=Vector(self.point);size=.08;vertices=[]
        for axis in range(3):
            delta=Vector((0,0,0));delta[axis]=size;vertices.extend([p-delta,p+delta])
        shader=gpu.shader.from_builtin('UNIFORM_COLOR');shader.bind();shader.uniform_float('color',(0.25,1,.5,1))
        batch_for_shader(shader,'LINES',{'pos':vertices}).draw(shader)
    def modal(self,context,event):
        if self.closed:return {'FINISHED'}
        if event.type in {'ESC','RIGHTMOUSE'} or context.scene!=self.owner or context.scene.wavelength.engine!=self.engine or not workspace.active(context):
            self.finish(context);return {'FINISHED'}
        if event.type=='TIMER':return {'RUNNING_MODAL'}
        in_browser=self.browser.x<=event.mouse_x<self.browser.x+self.browser.width and self.browser.y<=event.mouse_y<self.browser.y+self.browser.height
        if event.type=='LEFTMOUSE' and event.value=='PRESS' and in_browser:
            self.drag_start=(event.mouse_x,event.mouse_y);return {'PASS_THROUGH'}
        if self.drag_start and event.type=='MOUSEMOVE':
            if abs(event.mouse_x-self.drag_start[0])+abs(event.mouse_y-self.drag_start[1])>5:self.dragging=True
            if in_browser and self.dragging:return {'RUNNING_MODAL'}
        drop=event.type=='LEFTMOUSE' and event.value=='RELEASE' and self.dragging
        if event.type=='LEFTMOUSE' and event.value=='RELEASE':self.drag_start=None;self.dragging=False
        area=next((a for a in context.screen.areas if a.type=='VIEW_3D' and a.x<=event.mouse_x<a.x+a.width and a.y<=event.mouse_y<a.y+a.height),None)
        if area is None:return {'PASS_THROUGH'}
        if not drop and event.type=='LEFTMOUSE' and (event.shift or event.ctrl or event.alt):return {'PASS_THROUGH'}
        if event.type not in {'MOUSEMOVE','LEFTMOUSE'}:return {'PASS_THROUGH'}
        try:
            if self.browser in list(context.screen.areas) and self.browser.type=='FILE_BROWSER':
                with context.temp_override(area=self.browser,region=next(r for r in self.browser.regions if r.type=='WINDOW')):
                    try:self.row=payload(bpy.context)
                    except ValueError:
                        self.point=None;area.tag_redraw();return {'PASS_THROUGH'}
            region=next(r for r in area.regions if r.type=='WINDOW');xy=(event.mouse_x-region.x,event.mouse_y-region.y);rv=area.spaces.active.region_3d
            with context.temp_override(area=area,region=region):
                origin=view3d_utils.region_2d_to_origin_3d(region,rv,xy);direction=view3d_utils.region_2d_to_vector_3d(region,rv,xy)
                hit,point,normal,index,obj,matrix=context.scene.ray_cast(context.evaluated_depsgraph_get(),origin,direction)
                if not hit:
                    if self.row['category']!='ENTITY':self.point=None;area.tag_redraw();return {'RUNNING_MODAL'}
                    normal=direction;point=origin+direction*((self.anchor-origin).dot(direction))
                snapped=tool_snap.point(context,event,point,self.anchor)
                if hit:snapped-=normal*(snapped-point).dot(normal)
                self.point=snapped;self.status(context);area.tag_redraw()
                if (event.type=='LEFTMOUSE' and event.value=='PRESS') or drop:
                    if not hit and self.row['category']!='ENTITY':return {'RUNNING_MODAL'}
                    if not self.has_undo:bpy.ops.ed.undo_push(message='Begin Click Placement');self.has_undo=True
                    result=bpy.ops.wavelength.stamp_asset(data=json.dumps(self.row),object_name=obj.name if obj else '',face=index,location=snapped,scope=resolved_scope(context),selected_faces=drop)
                    if result=={'FINISHED'}:bpy.ops.ed.undo_push(message='Place Entity' if self.row['category']=='ENTITY' else 'Paint Surface')
                    if drop and getattr(self,'drop_only',False):self.finish(context);return {'FINISHED'}
            return {'RUNNING_MODAL'}
        except (ValueError,RuntimeError,ReferenceError) as exc:context.scene.wavelength.status=str(exc);return {'RUNNING_MODAL'}

class WL_OT_click_place(bpy.types.Operator):
    bl_idname='wavelength.click_place';bl_label='Click Place'
    bl_description='Select a texture or entity, then click or drag onto the level; Esc stops'
    @classmethod
    def poll(cls,context):return workspace.active(context)
    def invoke(self,context,event):
        self.session=PlacementSession()
        return self.session.invoke(context,event,self)
    def modal(self,context,event):return self.session.modal(context,event)
    def cancel(self,context):
        if hasattr(self,'session') and not self.session.closed:self.session.finish(context)

class WL_OT_drag_texture(bpy.types.Operator):
    bl_idname='wavelength.drag_texture';bl_label='Drop Texture on Faces'
    modal=WL_OT_click_place.modal
    cancel=WL_OT_click_place.cancel
    @classmethod
    def poll(cls,context):
        if not workspace.active(context):return False
        try:return payload(context)['category']=='MATERIAL'
        except (ValueError,AttributeError):return False
    def invoke(self,context,event):
        prune_session()
        if _active:return {'CANCELLED'}
        self.session=PlacementSession()
        result=self.session.invoke(context,event,self)
        if result=={'RUNNING_MODAL'}:
            self.session.drag_start=(event.mouse_x,event.mouse_y);self.session.dragging=True;self.session.drop_only=True
        return result

def register():
    bpy.types.WindowManager.wl_click_place=bpy.props.BoolProperty(default=False,options={'SKIP_SAVE'})
    bpy.types.WindowManager.wl_texture_apply_scope=bpy.props.EnumProperty(name='Apply To',items=[('AUTO','Auto','Object Mode paints the object; Edit Mode paints the hit face'),('SURFACE','Surface','Paint only the clicked mesh face, in either mode'),('OBJECT','Object','Paint the whole clicked mesh or locked brush assembly')],default='AUTO',options={'SKIP_SAVE'})
    for cls in (WL_OT_stamp,WL_OT_click_place,WL_OT_drag_texture):bpy.utils.register_class(cls)
    config=bpy.context.window_manager.keyconfigs.addon
    if config:
        keymap=config.keymaps.new(name='File Browser Main',space_type='FILE_BROWSER',region_type='WINDOW')
        item=keymap.keymap_items.new('wavelength.drag_texture','LEFTMOUSE','CLICK_DRAG')
        _keymaps.append((keymap,item))
    bpy.app.timers.register(auto_place,first_interval=1,persistent=True)
    bpy.app.handlers.load_pre.append(clear_session)
    bpy.app.handlers.undo_pre.append(clear_session)
    bpy.app.handlers.redo_pre.append(clear_session)

def unregister():
    if bpy.app.timers.is_registered(auto_place):bpy.app.timers.unregister(auto_place)
    for handlers in (bpy.app.handlers.load_pre,bpy.app.handlers.undo_pre,bpy.app.handlers.redo_pre):
        if clear_session in handlers:handlers.remove(clear_session)
    if _active:_active.finish(bpy.context)
    for keymap,item in _keymaps:keymap.keymap_items.remove(item)
    _keymaps.clear()
    for cls in (WL_OT_drag_texture,WL_OT_click_place,WL_OT_stamp):bpy.utils.unregister_class(cls)
    del bpy.types.WindowManager.wl_click_place;del bpy.types.WindowManager.wl_texture_apply_scope
