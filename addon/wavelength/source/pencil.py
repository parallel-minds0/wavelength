"""Editable line/curve guides with explicit knife projection and mesh creation."""
import bpy
import bmesh
import gpu
from mathutils import Vector
from bpy_extras import view3d_utils
from gpu_extras.batch import batch_for_shader
from . import workspace, profiles, tool_snap, brush_create, draw_geometry as geo, cutter_snap, cutter_solid

_drawing=[]


def target_hit(context,target,origin,direction):
    """Hit the chosen mesh even when another object occludes it."""
    if target is None:return None
    evaluated=target.evaluated_get(context.evaluated_depsgraph_get())
    matrix=evaluated.matrix_world;inverse=matrix.inverted()
    # Orthographic rays start at the far clip plane; shorten them for float precision.
    bounds=[matrix@Vector(p) for p in evaluated.bound_box]
    center=sum(bounds,Vector())/8
    radius=max((p-center).length for p in bounds)+1
    advance=(center-origin).dot(direction)-radius
    if advance>0:origin=origin+direction*advance
    hit,location,n,_=evaluated.ray_cast(inverse@origin,(inverse.to_3x3()@direction).normalized())
    if not hit:return None
    return matrix@location,(inverse.transposed().to_3x3()@n).normalized()


def point(co):return dict(co=list(co),left=list(co),right=list(co))
def is_guide(obj):return bool(obj and obj.type=='CURVE' and obj.get('wl_cutter_guide'))


def guide(context):
    if is_guide(context.object):return context.object
    obj=context.scene.wavelength_draw.guide
    return obj if is_guide(obj) and obj.name in context.scene.objects else None


class WLCutterGuide(bpy.types.PropertyGroup):
    target:bpy.props.PointerProperty(name='Target Mesh',type=bpy.types.Object,poll=lambda self,obj:obj.type=='MESH' and not obj.library)
    operation:bpy.props.EnumProperty(name='Operation',items=[('FACE','Faces','Split surface topology'),('SPLIT','Split Solid','Separate capped solid pieces'),('SUBTRACT','Subtract','Remove a closed cutting volume')],default='FACE')
    direction:bpy.props.EnumProperty(name='Cut Direction',items=[('NORMAL','Surface','Along the initial surface normal'),('X','X','Along world X'),('Y','Y','Along world Y'),('Z','Z','Along world Z')],default='NORMAL')
    keep:bpy.props.EnumProperty(name='Keep',items=[('BOTH','Both','Keep both capped sides'),('OUTSIDE','Outside','Discard the cutting side'),('INSIDE','Inside','Keep only the cutting side')],default='BOTH')
    through:bpy.props.BoolProperty(name='Through All',default=True)
    separate_objects:bpy.props.BoolProperty(name='Separate Objects',default=True,description='Keep Both creates two separate objects; disable to retain both capped pieces in one mesh')
    depth:bpy.props.FloatProperty(name='Depth',default=16,min=.001,description='Cut inward in profile units')
    cut_through:bpy.props.BoolProperty(name='Cut Through',default=False,description='Also cut faces occluded along the guide normal')
    geometry:bpy.props.EnumProperty(name='Geometry',items=[('EDGES','Edges','Mesh path'),('FACE','Face','Fill a closed planar outline'),('EXTRUDE','Extrusion','Extrude a closed face or open path')])
    height:bpy.props.FloatProperty(name='Height',default=16,description='Height in active profile units')


class WLDrawSettings(bpy.types.PropertyGroup):
    guide:bpy.props.PointerProperty(name='Guide',type=bpy.types.Object,poll=lambda self,obj:is_guide(obj))
    operation:bpy.props.EnumProperty(name='Operation',items=[('FACE','Faces','Split surface topology'),('SPLIT','Split Solid','Separate capped solid pieces'),('SUBTRACT','Subtract','Remove a closed cutting volume')],default='FACE')
    direction:bpy.props.EnumProperty(name='Cut Direction',items=[('NORMAL','Surface','Along the initial surface normal'),('X','X','Along world X'),('Y','Y','Along world Y'),('Z','Z','Along world Z')],default='NORMAL')
    keep:bpy.props.EnumProperty(name='Keep',items=[('BOTH','Both','Keep both capped sides'),('OUTSIDE','Outside','Discard the cutting side'),('INSIDE','Inside','Keep only the cutting side')],default='BOTH')
    through:bpy.props.BoolProperty(name='Through All',default=True)
    separate_objects:bpy.props.BoolProperty(name='Separate Objects',default=True,description='Keep Both creates two separate objects')
    depth:bpy.props.FloatProperty(name='Depth',default=16,min=.001,description='Cut inward in profile units')
    auto_extrude:bpy.props.BoolProperty(name='Auto Extrude',default=True,description='Closing the outline starts mouse-driven extrusion')
    resolution:bpy.props.IntProperty(name='Curve Resolution',default=12,min=2,max=64)


def records(obj):
    if obj.mode=='EDIT':obj.update_from_editmode()
    if len(obj.data.splines)!=1 or obj.data.splines[0].type!='BEZIER':raise ValueError('Use one Bezier spline for the cutter guide')
    points=[dict(co=list(p.co),left=list(p.handle_left),right=list(p.handle_right)) for p in obj.data.splines[0].bezier_points]
    if len(points)<2:raise ValueError('The guide needs at least two points')
    return points,obj.data.splines[0].use_cyclic_u


def sampled(obj):
    points,closed=records(obj);pairs=list(zip(points,points[1:]))
    if closed:pairs.append((points[-1],points[0]))
    result=[]
    for a,b in pairs:
        straight=(Vector(a['right'])-Vector(a['co'])).length<1e-7 and (Vector(b['left'])-Vector(b['co'])).length<1e-7
        result.extend(obj.matrix_world@Vector(p) for p in geo.sample(a,b,1 if straight else obj.data.resolution_u)[:-1])
    if not closed:result.append(obj.matrix_world@Vector(points[-1]['co']))
    clean=[]
    for p in result:
        if not clean or (p-clean[-1]).length>1e-7:clean.append(p)
    if closed and len(clean)>1 and (clean[-1]-clean[0]).length<1e-7:clean.pop()
    if len(clean)<(3 if closed else 2):raise ValueError('Guide has too few distinct points')
    return clean,closed


def cut_direction(obj):
    axis=obj.wavelength_cutter.direction
    return normal(obj) if axis=='NORMAL' else Vector(tuple(float(a==axis) for a in 'XYZ'))


def normal(obj):
    return (obj.matrix_world.to_3x3().inverted().transposed()@Vector(obj.get('wl_cutter_normal',(0,0,1)))).normalized()


def create_guide(context,points,plane_normal,closed=False,target=None):
    if context.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
    data=bpy.data.curves.new('Cutter Guide','CURVE');data.dimensions='3D';data.resolution_u=context.scene.wavelength_draw.resolution
    spline=data.splines.new('BEZIER');spline.bezier_points.add(len(points)-1)
    for bp,p in zip(spline.bezier_points,points):
        bp.co=p['co'];bp.handle_left_type=bp.handle_right_type='FREE';bp.handle_left=p['left'];bp.handle_right=p['right']
    spline.use_cyclic_u=closed
    obj=bpy.data.objects.new('Cutter Guide',data);context.collection.objects.link(obj)
    obj['wl_cutter_guide']=True;obj['wl_cutter_normal']=list(plane_normal);obj['wl_exclude']=True
    for key in ('operation','through','depth','direction','keep','separate_objects'):setattr(obj.wavelength_cutter,key,getattr(context.scene.wavelength_draw,key))
    obj.wavelength_cutter.target=target;obj.wavelength_cutter.geometry='FACE' if closed else 'EDGES'
    obj.show_in_front=True;obj.hide_render=True
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);context.view_layer.objects.active=obj
    context.scene.wavelength_draw.guide=obj
    return obj


def _mesh(context,name,vertices,edges=(),faces=()):
    data=bpy.data.meshes.new(name);data.from_pydata(vertices,edges,faces);data.update()
    obj=bpy.data.objects.new(name,data);context.collection.objects.link(obj);return obj


def create_geometry(context,obj,kind,height=None):
    verts,closed=sampled(obj);n=len(verts);up=normal(obj)
    if kind in {'FACE','EXTRUDE'} and closed:
        if max(abs((p-verts[0]).dot(normal(obj))) for p in verts)>1e-5:raise ValueError('Filled outlines must be planar; flatten the guide or choose Edges')
        if not geo.simple_polygon(verts,up):raise ValueError('The outline crosses itself or has no area')
    if kind=='FACE' and not closed:raise ValueError('Close the guide before creating a face')
    height=0 if height is None and kind!='EXTRUDE' else height
    if kind=='EXTRUDE':
        height=profiles.engine_to_world(context.scene.wavelength,obj.wavelength_cutter.height) if height is None else height
        if abs(height)<1e-7:raise ValueError('Extrusion height must be nonzero')
        up=cut_direction(obj)
        if abs(up.dot(normal(obj)))<1e-5 and closed:raise ValueError('Extrusion direction lies in the outline plane')
    if context.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
    from . import node_pencil
    obj.wavelength_cutter.geometry=kind
    result=node_pencil.create(context,obj,kind,height,normal(obj),cut_direction(obj))
    bpy.ops.object.select_all(action='DESELECT');result.select_set(True);context.view_layer.objects.active=result
    return result


def _view(context):
    area=context.area if context.area and context.area.type=='VIEW_3D' else next((a for a in context.screen.areas if a.type=='VIEW_3D'),None)
    if area is None:raise ValueError('Open a 3D viewport to apply the cutter')
    region=next((r for r in area.regions if r.type=='WINDOW'),None)
    if region is None:raise ValueError('No drawable viewport region')
    return area,region


def apply_cut(context,obj):
    """Knife-project on a private mesh copy. Failure restores the original mesh."""
    target=obj.wavelength_cutter.target
    if target is None or target.name not in context.scene.objects or target.type!='MESH':raise ValueError('Choose a target mesh for this guide')
    if target.library or target.data.library or target.override_library:raise ValueError('Make the target mesh local before cutting')
    if not target.visible_get():raise ValueError('The target must be visible and selectable')
    if any(modifier.show_viewport for modifier in target.modifiers):
        raise ValueError('Finalize geometry or apply viewport modifiers before cutting; the visible mesh must match its editable geometry')
    points,closed=sampled(obj)
    if obj.wavelength_cutter.operation!='FACE':
        previous_active=context.view_layer.objects.active;previous_selection=list(context.selected_objects);previous_mode=context.mode
        try:return cutter_solid.apply(context,obj,points,closed,cut_direction(obj))
        except Exception:
            if context.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            for selected in previous_selection:selected.select_set(True)
            context.view_layer.objects.active=previous_active
            if previous_mode in {'EDIT_MESH','EDIT_CURVE'} and previous_active:bpy.ops.object.mode_set(mode='EDIT')
            raise
    area,region=_view(context);rv3d=area.spaces.active.region_3d
    previous_view=(rv3d.view_rotation.copy(),rv3d.view_location.copy(),rv3d.view_distance,rv3d.view_perspective)
    previous_active=context.view_layer.objects.active;previous_selection=list(context.selected_objects);previous_mode=context.mode
    if previous_mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
    original=target.data;working=original.copy();target.data=working
    edges=[(i,i+1) for i in range(len(points)-1)]+([(len(points)-1,0)] if closed else [])
    projector=None;success=False
    try:
        projector=_mesh(context,'.Wavelength Cut Projection',[tuple(p) for p in points],edges);projector['wl_exclude']=True
        bpy.ops.object.select_all(action='DESELECT');target.select_set(True);context.view_layer.objects.active=target
        with context.temp_override(area=area,region=region):
            bounds=points+[target.matrix_world@Vector(p) for p in target.bound_box]
            lo=Vector(tuple(min(p[i] for p in bounds) for i in range(3)));hi=Vector(tuple(max(p[i] for p in bounds) for i in range(3)))
            rv3d.view_rotation=normal(obj).to_track_quat('Z','Y');rv3d.view_location=(lo+hi)/2
            rv3d.view_perspective='ORTHO';rv3d.view_distance=max(1,(hi-lo).length*2);rv3d.update()
            bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');projector.select_set(True)
            before=(len(original.vertices),len(original.edges),len(original.polygons))
            result=bpy.ops.mesh.knife_project(cut_through=obj.wavelength_cutter.cut_through)
            bpy.ops.object.mode_set(mode='OBJECT')
            after=(len(working.vertices),len(working.edges),len(working.polygons))
            if result!={'FINISHED'} or before==after:raise ValueError('Guide did not cut the mesh; extend it across a face or close the outline')
            if target.get('wl_role')=='BRUSH':
                from . import scene
                scene.mark_brush(target)
            success=True
    finally:
        if context.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
        if projector:
            mesh=projector.data;bpy.data.objects.remove(projector,do_unlink=True)
            if mesh.users==0:bpy.data.meshes.remove(mesh)
        with context.temp_override(area=area,region=region):
            rv3d.view_rotation,rv3d.view_location,rv3d.view_distance,rv3d.view_perspective=previous_view;rv3d.update()
        if success:
            if original.users==0:bpy.data.meshes.remove(original)
            bpy.ops.object.select_all(action='DESELECT');target.select_set(True);context.view_layer.objects.active=target;bpy.ops.object.mode_set(mode='EDIT')
        else:
            target.data=original
            if working.users==0:bpy.data.meshes.remove(working)
            bpy.ops.object.select_all(action='DESELECT')
            for selected in previous_selection:
                if selected.name in context.view_layer.objects:selected.select_set(True)
            context.view_layer.objects.active=previous_active
            if previous_mode in {'EDIT_MESH','EDIT_CURVE'} and previous_active:bpy.ops.object.mode_set(mode='EDIT')


def cut_result(obj):
    st=obj.wavelength_cutter
    if st.operation=='FACE':return 'Faces cut; target topology split'
    if st.operation=='SUBTRACT':return 'Volume subtracted; remaining mesh capped'
    if st.keep=='BOTH':return 'Solid split: two separate capped objects' if st.separate_objects else 'Solid split: both capped pieces kept in one mesh; outer silhouette unchanged'
    return 'Solid clipped: '+('inside' if st.keep=='INSIDE' else 'outside')+' kept; other side removed and cut capped'

def cycle_keep(settings,step=1):
    choices=('BOTH','OUTSIDE','INSIDE')
    settings['keep']=choices[(choices.index(settings['keep'])+step)%len(choices)]
    settings['operation']='SPLIT'

class WL_OT_apply_cut(bpy.types.Operator):
    bl_idname='wavelength.apply_cut';bl_label='Apply Cut';bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context):return workspace.active(context) and guide(context) is not None
    def execute(self,context):
        obj=guide(context)
        try:apply_cut(context,obj)
        except (ValueError,RuntimeError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        message=cut_result(obj);context.scene.wavelength.status=message
        self.report({'INFO'},message);return {'FINISHED'}


class WL_OT_create_cut_geometry(bpy.types.Operator):
    bl_idname='wavelength.create_cut_geometry';bl_label='Create Geometry';bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context):return workspace.active(context) and guide(context) is not None
    def execute(self,context):
        obj=guide(context)
        try:create_geometry(context,obj,obj.wavelength_cutter.geometry)
        except ValueError as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        return {'FINISHED'}


class WL_OT_keep_cut_guide(bpy.types.Operator):
    bl_idname='wavelength.keep_cut_guide';bl_label='Keep Guide';bl_options={'REGISTER','UNDO'}
    @classmethod
    def poll(cls,context):return workspace.active(context) and guide(context) is not None
    def execute(self,context):
        obj=guide(context)
        if context.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);context.view_layer.objects.active=obj
        return {'FINISHED'}


class WL_OT_activate_cutter(bpy.types.Operator):
    bl_idname='wavelength.activate_cutter';bl_label='Line / Curve Cutter'
    bl_description='Enter mesh Edit Mode and activate the cutter'
    @classmethod
    def poll(cls,context):return workspace.active(context) and context.area and context.area.type=='VIEW_3D' and context.mode in {'OBJECT','EDIT_MESH'}
    def execute(self,context):
        if context.object and context.object.type=='MESH':
            if context.mode=='OBJECT':bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.wm.tool_set_by_id(name='wavelength.pencil_edit_tool')
        else:bpy.ops.wm.tool_set_by_id(name='wavelength.pencil_tool')
        return {'FINISHED'}


class WL_OT_draw_path(bpy.types.Operator):
    bl_idname='wavelength.draw_path';bl_label='Draw Cutter Guide';bl_options={'REGISTER','UNDO','BLOCKING'}
    @classmethod
    def poll(cls,context):return workspace.active(context) and context.area and context.area.type=='VIEW_3D' and context.mode in {'OBJECT','EDIT_MESH'}
    def _status(self,context):
        st=self._operation_settings
        if self._extruding:
            context.area.header_text_set(f"Extrude: move mouse · click/Enter confirm · XYZ direction · B / Shift+wheel keep {st['keep']} · type height · Esc cancel | Height {self._height_m:g} m")
            return
        confirm='Enter apply solid · Shift+Enter guide' if st['operation']!='FACE' else 'Enter guide'
        context.area.header_text_set(f"{st['operation']} / {st['direction']} / {('Through All' if st['through'] else str(st['depth']))} / Keep {st['keep']}: XYZ direction · V face/solid · D depth · B / Shift+wheel keep · K apply · {confirm} · C close")
    def _remove(self,context):
        if self._handle:bpy.types.SpaceView3D.draw_handler_remove(self._handle,'WINDOW');self._handle=None
        if context.area:context.area.header_text_set(None);context.area.tag_redraw()
        if context.window:context.window.cursor_modal_restore()
        if self in _drawing:_drawing.remove(self)
    def invoke(self,context,event):
        if not brush_create._event_in_window_region(context,event):return {'PASS_THROUGH'}
        current=guide(context)
        settings=current.wavelength_cutter if current else context.scene.wavelength_draw
        self._operation_settings={key:getattr(settings,key) for key in ('operation','through','depth','direction','keep','separate_objects')}
        self._target=context.object if context.object and context.object.type=='MESH' else None
        if self._target and context.mode=='EDIT_MESH':self._target.update_from_editmode()
        context.view_layer.update()
        self._plane,self._u,self._v,self._normal=brush_create._plane_from_mouse(context,event)
        if self._target is None:
            origin,direction=brush_create._ray(context,event)
            hit,_,_,_,obj,_=context.scene.ray_cast(context.evaluated_depsgraph_get(),origin,direction)
            if hit and obj and obj.type=='MESH' and not obj.get('wl_exclude'):self._target=obj
        origin,direction=brush_create._ray(context,event)
        surface=target_hit(context,self._target,origin,direction)
        if surface:
            self._plane=surface[0];self._u,self._v,self._normal=brush_create._axis_basis(surface[1])
        self._extruding=False;self._extrude_closed=False
        self._points=[];self._pending=None;self._hover=None;self._closing=False;self._axis=None;self._value=''
        self._targets=cutter_snap.Targets(context,self._target);self._snap_result=None
        self._area=context.area.as_pointer();self._handle=None;self._update(context,event)
        if self._hover is None:return {'CANCELLED'}
        self._pending=point(self._hover);self._mouse=(event.mouse_region_x,event.mouse_region_y)
        self._handle=bpy.types.SpaceView3D.draw_handler_add(self._draw,(),'WINDOW','POST_VIEW')
        _drawing.append(self);context.window.cursor_modal_set('CROSSHAIR');context.window_manager.modal_handler_add(self);self._status(context)
        return {'RUNNING_MODAL'}

    # Placement method is shared with the previously verified surface drawing controls.
    def _update(self,context,event):
        anchor=Vector(self._points[-1]['co']) if self._points else self._plane
        # A profile-grid stroke stays on the surface/grid plane selected at its
        # first point. Native free drawing keeps its existing surface following.
        self._snap_result=self._targets.resolve(context,event,self._plane,self._normal,anchor,lock_plane=tool_snap.profile_grid_active(context))
        if self._snap_result is None:return
        value=self._snap_result[0].copy()
        if self._points and self._value:
            try:
                distance=profiles.engine_to_world(context.scene.wavelength,float(self._value));delta=value-anchor
                if delta.length>1e-8:value=anchor+delta.normalized()*distance
            except ValueError:pass
        self._snap_result=(value,self._snap_result[1],self._snap_result[2],self._snap_result[3])
        self._hover=value;self._closing=False
        if len(self._points)>=3:
            screen=view3d_utils.location_3d_to_region_2d(context.region,context.region_data,Vector(self._points[0]['co']))
            if screen is not None and (screen-Vector((event.mouse_region_x,event.mouse_region_y))).length<14:self._closing=True;self._hover=Vector(self._points[0]['co'])

    def _draw(self):
        context=bpy.context
        if not context.area or context.area.as_pointer()!=self._area:return
        cutter_snap.draw(context,self._snap_result)
        pts=list(self._points)
        if self._extruding:
            if self._extrude_closed:pts.append(self._points[0])
        elif self._pending:pts.append(self._pending)
        elif self._hover is not None and pts:pts.append(self._points[0] if self._closing else point(self._hover))
        positions=[]
        st=self._operation_settings
        if (self._extruding or st['operation']!='FACE') and len(pts)>=2:
            axis=st['direction'];up=self._normal if axis=='NORMAL' else Vector(tuple(float(a==axis) for a in 'XYZ'))
            bounds=[self._target.matrix_world@Vector(p) for p in self._target.bound_box] if self._target else [Vector(p['co']) for p in pts]
            base=Vector(pts[0]['co'])
            low=min((p-base).dot(up) for p in bounds)-.1 if st['through'] else -profiles.engine_to_world(context.scene.wavelength,st['depth'])
            high=max((p-base).dot(up) for p in bounds)+.1 if st['through'] else 0
            if self._extruding:low,high=(0,self._height_m) if st['operation']=='FACE' else (-self._height_m,0)
            for a,b in zip(pts,pts[1:]):
                path=[Vector(p) for p in geo.sample(a,b,context.scene.wavelength_draw.resolution)]
                if not (self._extruding and st['operation']=='FACE'):path=[p-up*(p-base).dot(up) for p in path]
                positions.extend(p for x,y in zip(path,path[1:]) for p in (x+up*low,y+up*low,x+up*high,y+up*high))
            for p in pts:
                co=Vector(p['co'])
                if not (self._extruding and st['operation']=='FACE'):co-=up*(co-base).dot(up)
                positions.extend((co+up*low,co+up*high))
        for a,b in zip(pts,pts[1:]):
            curve=geo.sample(a,b,context.scene.wavelength_draw.resolution);positions.extend(p for edge in zip(curve,curve[1:]) for p in edge)
        shader=gpu.shader.from_builtin('UNIFORM_COLOR');gpu.state.depth_test_set('NONE')
        try:
            if positions:
                batch=batch_for_shader(shader,'LINES',{'pos':positions});shader.bind();shader.uniform_float('color',(.3,1,.5,1));batch.draw(shader)
            if self._points:
                gpu.state.point_size_set(7);batch=batch_for_shader(shader,'POINTS',{'pos':[p['co'] for p in self._points]})
                shader.bind();shader.uniform_float('color',(1,.7,.1,1) if self._closing else (.5,1,.65,1));batch.draw(shader)
            if self._pending:
                p=self._pending;batch=batch_for_shader(shader,'LINES',{'pos':[p['left'],p['co'],p['co'],p['right']]})
                shader.bind();shader.uniform_float('color',(1,.65,.2,1));batch.draw(shader)
        finally:gpu.state.point_size_set(1);gpu.state.depth_test_set('LESS_EQUAL')
    def _begin_extrude(self,context,event,closed):
        self._extruding=True;self._extrude_closed=closed;self._value=''
        self._start=Vector(self._points[0]['co']);self._height_mouse_start=(event.mouse_region_x,event.mouse_region_y)
        self._height_m=brush_create._neutral_size(context.scene.wavelength);self._height_start_m=self._height_m
        self._virt_mouse=self._height_mouse_start
        self._status(context);context.area.tag_redraw();return {'RUNNING_MODAL'}

    def _extrude_modal(self,context,event):
        if self._keep_input(context,event):return {'RUNNING_MODAL'}
        if event.type in {'MIDDLEMOUSE','WHEELUPMOUSE','WHEELDOWNMOUSE'}:return {'PASS_THROUGH'}
        if event.type in {'ESC','RIGHTMOUSE'} and event.value=='PRESS':self._remove(context);return {'CANCELLED'}
        axis=self._operation_settings['direction']
        self._n=self._normal if axis=='NORMAL' else Vector(tuple(float(a==axis) for a in 'XYZ'))
        if event.type=='MOUSEMOVE':
            self._virt_mouse=(event.mouse_region_x,event.mouse_region_y)
            self._step_value=tool_snap.step(context) if tool_snap.grid_enabled(context,event) else 0
            brush_create.WL_OT_cube_brush_create._update_height_from_mouse(self,context)
        if event.value=='PRESS':
            if event.type in {'LEFTMOUSE','RET','NUMPAD_ENTER'}:
                self._finish(context,self._extrude_closed);obj=guide(context)
                try:
                    if self._operation_settings['operation']=='FACE':
                        obj.wavelength_cutter.geometry='EXTRUDE'
                        obj.wavelength_cutter.height=self._height_m/profiles.engine_to_world(context.scene.wavelength,1)
                        create_geometry(context,obj,'EXTRUDE',self._height_m)
                    else:
                        obj.wavelength_cutter.through=False
                        obj.wavelength_cutter.depth=self._height_m/profiles.engine_to_world(context.scene.wavelength,1)
                        apply_cut(context,obj)
                except (ValueError,RuntimeError) as exc:self.report({'ERROR'},str(exc))
                return {'FINISHED'}
            if event.type in {'X','Y','Z'}:
                self._operation_settings['direction']=event.type if axis!=event.type else 'NORMAL'
                self._height_start_m=self._height_m;self._height_mouse_start=(event.mouse_region_x,event.mouse_region_y)
            elif event.type=='BACK_SPACE':self._value=self._value[:-1]
            elif event.unicode and event.unicode in '0123456789.-':self._value+=event.unicode
        if self._value:
            try:self._height_m=profiles.engine_to_world(context.scene.wavelength,float(self._value))
            except ValueError:pass
        self._status(context);context.area.tag_redraw();return {'RUNNING_MODAL'}

    def _finish(self,context,closed):
        obj=create_guide(context,self._points,self._normal,closed,self._target)
        for key,value in self._operation_settings.items():setattr(obj.wavelength_cutter,key,value)
        self._remove(context)
        bpy.ops.wm.tool_set_by_id(name='wavelength.pencil_tool')
        self.report({'INFO'},'Guide ready: edit points, Apply Cut, Create Geometry or Keep Guide');return {'FINISHED'}
    def _keep_input(self,context,event):
        if event.value=='PRESS' and event.type=='B':cycle_keep(self._operation_settings)
        elif event.shift and event.type in {'WHEELUPMOUSE','WHEELDOWNMOUSE'}:
            cycle_keep(self._operation_settings,1 if event.type=='WHEELUPMOUSE' else -1)
        else:return False
        self._status(context);context.area.tag_redraw();return True
    def modal(self,context,event):
        if not workspace.active(context):self._remove(context);return {'CANCELLED'}
        if self._extruding:return self._extrude_modal(context,event)
        if self._keep_input(context,event):return {'RUNNING_MODAL'}
        if event.type=='TAB' and event.shift:return {'PASS_THROUGH'}
        if event.type in {'WHEELUPMOUSE','WHEELDOWNMOUSE'} and not self._operation_settings['through']:
            self._operation_settings['depth']=max(.001,self._operation_settings['depth']*(1.1 if event.type=='WHEELUPMOUSE' else 1/1.1))
            self._status(context);context.area.tag_redraw();return {'RUNNING_MODAL'}
        if event.type in {'MIDDLEMOUSE','WHEELUPMOUSE','WHEELDOWNMOUSE'} or event.type.startswith('NDOF') or (event.alt and event.type in {'LEFTMOUSE','RIGHTMOUSE'}):return {'PASS_THROUGH'}
        if event.type in {'LEFTMOUSE','MOUSEMOVE'} and not brush_create._event_in_window_region(context,event):return {'PASS_THROUGH'}
        if event.type=='MOUSEMOVE':
            self._update(context,event)
            if self._pending is not None and self._hover is not None and (Vector((event.mouse_region_x,event.mouse_region_y))-Vector(self._mouse)).length>4:
                co=Vector(self._pending['co']);delta=self._hover-co;self._pending['left']=list(co-delta);self._pending['right']=list(co+delta)
            context.area.tag_redraw();return {'RUNNING_MODAL'}
        if event.type=='LEFTMOUSE' and event.value=='RELEASE' and self._pending is not None:
            self._points.append(self._pending);self._pending=None;self._value='';self._axis=None;context.area.tag_redraw();return {'RUNNING_MODAL'}
        if event.value!='PRESS':return {'RUNNING_MODAL'}
        if event.type in {'ESC','RIGHTMOUSE'}:self._remove(context);return {'CANCELLED'}
        if len(self._points)>=2 and (event.type=='K' or (event.type in {'RET','NUMPAD_ENTER'} and not event.shift and self._operation_settings['operation']!='FACE')):
            self._finish(context,False)
            # Keep drawing and cutting in this modal operator's single undo step.
            obj=guide(context)
            try:
                apply_cut(context,obj)
                message=cut_result(obj);context.scene.wavelength.status=message;self.report({'INFO'},message)
            except (ValueError,RuntimeError) as exc:self.report({'ERROR'},str(exc))
            return {'FINISHED'}
        if event.type in {'RET','NUMPAD_ENTER'} and len(self._points)>=2:return self._finish(context,False)
        if event.type=='C' and len(self._points)>=3:
            return self._begin_extrude(context,event,True) if context.scene.wavelength_draw.auto_extrude and not event.shift else self._finish(context,True)
        if event.type=='E' and len(self._points)>=2:return self._begin_extrude(context,event,False)
        if event.type=='BACK_SPACE':
            if self._value:self._value=self._value[:-1]
            elif self._points:self._points.pop()
        elif event.type in {'X','Y','Z'}:
            st=self._operation_settings;st['direction']=event.type if st['direction']!=event.type else 'NORMAL';st['operation']='SPLIT' if st['operation']=='FACE' else st['operation']
        elif event.type=='V':
            st=self._operation_settings;st['operation']='SPLIT' if st['operation']=='FACE' else 'FACE'
        elif event.type=='D':
            st=self._operation_settings;st['through']=not st['through'];st['operation']='SPLIT' if st['operation']=='FACE' else st['operation']
        elif event.type=='LEFTMOUSE':
            self._update(context,event)
            if self._closing:return self._begin_extrude(context,event,True) if context.scene.wavelength_draw.auto_extrude and not event.shift else self._finish(context,True)
            if len(self._points)>=256:self.report({'WARNING'},'Finish this guide before adding more than 256 points')
            elif self._hover is not None:self._pending=point(self._hover);self._mouse=(event.mouse_region_x,event.mouse_region_y);self._value=''
        elif event.unicode and event.unicode in '0123456789.-':self._value+=event.unicode
        self._status(context);context.area.tag_redraw();return {'RUNNING_MODAL'}


def _operation(layout,settings):
    layout.prop(settings,'operation',text='')
    if settings.operation!='FACE':
        layout.prop(settings,'direction',text='')
        if settings.operation=='SPLIT':
            layout.prop(settings,'keep',text='')
            if settings.keep=='BOTH':layout.prop(settings,'separate_objects')
        layout.prop(settings,'through')
        if not settings.through:layout.prop(settings,'depth')


def _actions(layout,context):
    if guide(context) is None:layout.label(text='Draw a guide; Enter finishes, C closes');return
    row=layout.row(align=True);row.operator('wavelength.apply_cut',icon='MOD_BOOLEAN')
    row.operator('wavelength.create_cut_geometry',icon='MESH_DATA');row.operator('wavelength.keep_cut_guide',icon='CURVE_DATA')


class WL_PT_drawing(bpy.types.Panel):
    bl_label='Wavelength Cutter';bl_space_type='PROPERTIES';bl_region_type='WINDOW';bl_context='object'
    @classmethod
    def poll(cls,context):return workspace.active(context) and (is_guide(context.object) or bool(context.object and context.object.get('wl_pencil_geometry')))
    def draw(self,context):
        output=context.object if context.object.get('wl_pencil_geometry') else None
        obj=output.get('wl_source_guide') if output else context.object
        l=self.layout
        if not obj:return
        st=obj.wavelength_cutter;l.label(text='Edit the native curve to update generated geometry')
        if output and output.get('wl_procedural_state')=='PROCEDURAL':l.operator('wavelength.finalize_primitive',text='Finalize Geometry')
        l.prop(st,'target');_operation(l,st);l.prop(st,'cut_through') if st.operation=='FACE' else None;l.operator('wavelength.apply_cut',icon='MOD_BOOLEAN')
        l.separator();l.prop(st,'geometry')
        if st.geometry=='EXTRUDE':l.prop(st,'height')
        l.operator('wavelength.create_cut_geometry',icon='MESH_DATA');l.separator()
        l.operator('wavelength.keep_cut_guide',icon='CURVE_DATA');l.prop(obj.data,'resolution_u')


class WL_Tool_pencil(bpy.types.WorkSpaceTool):
    bl_space_type='VIEW_3D';bl_context_mode='OBJECT';bl_idname='wavelength.pencil_tool'
    bl_label='Line / Curve Cutter';bl_description='Draw and edit a guide; explicitly cut a mesh or create geometry';bl_icon='ops.curve.draw'
    draw_cursor=staticmethod(cutter_snap.hover)
    bl_keymap=(('wavelength.draw_path',{'type':'LEFTMOUSE','value':'PRESS'},None),('wavelength.apply_cut',{'type':'K','value':'PRESS'},None),('wavelength.apply_cut',{'type':'RET','value':'PRESS'},None),('wavelength.apply_cut',{'type':'NUMPAD_ENTER','value':'PRESS'},None))
    @staticmethod
    def draw_settings(context,layout,tool):
        obj=guide(context)
        if obj:
            layout.prop(obj.wavelength_cutter,'target',text='')
            layout.prop(obj.wavelength_cutter,'geometry',text='')
            if obj.wavelength_cutter.geometry=='EXTRUDE':layout.prop(obj.wavelength_cutter,'height')
        _operation(layout,obj.wavelength_cutter if obj else context.scene.wavelength_draw)
        layout.prop(context.scene.wavelength_draw,'auto_extrude')
        _actions(layout,context)


class WL_Tool_pencil_edit(bpy.types.WorkSpaceTool):
    bl_space_type='VIEW_3D';bl_context_mode='EDIT_MESH';bl_idname='wavelength.pencil_edit_tool'
    bl_label='Line / Curve Cutter';bl_description='Draw an editable cutting guide on this mesh';bl_icon='ops.curve.draw'
    draw_cursor=staticmethod(cutter_snap.hover)
    bl_keymap=WL_Tool_pencil.bl_keymap
    @staticmethod
    def draw_settings(context,layout,tool):
        obj=guide(context)
        if obj:
            layout.prop(obj.wavelength_cutter,'target',text='')
            layout.prop(obj.wavelength_cutter,'geometry',text='')
            if obj.wavelength_cutter.geometry=='EXTRUDE':layout.prop(obj.wavelength_cutter,'height')
        _operation(layout,obj.wavelength_cutter if obj else context.scene.wavelength_draw)
        layout.prop(context.scene.wavelength_draw,'auto_extrude')
        _actions(layout,context)


CLASSES=(WLCutterGuide,WLDrawSettings,WL_OT_activate_cutter,WL_OT_draw_path,WL_OT_apply_cut,WL_OT_create_cut_geometry,WL_OT_keep_cut_guide,WL_PT_drawing)


def register():
    for cls in CLASSES:bpy.utils.register_class(cls)
    bpy.types.Scene.wavelength_draw=bpy.props.PointerProperty(type=WLDrawSettings)
    bpy.types.Object.wavelength_cutter=bpy.props.PointerProperty(type=WLCutterGuide)
    bpy.utils.register_tool(WL_Tool_pencil,after={'builtin.transform'},separator=True)
    bpy.utils.register_tool(WL_Tool_pencil_edit,after={'builtin.knife'},separator=True)
    from . import node_pencil
    bpy.app.timers.register(node_pencil.tick,first_interval=.1,persistent=True)


def unregister():
    from . import node_pencil
    if bpy.app.timers.is_registered(node_pencil.tick):bpy.app.timers.unregister(node_pencil.tick)
    node_pencil._state.clear()
    cutter_snap._hover_cache.clear()
    for op in list(_drawing):
        if op._handle:bpy.types.SpaceView3D.draw_handler_remove(op._handle,'WINDOW');op._handle=None
    _drawing.clear()
    for tool in (WL_Tool_pencil_edit,WL_Tool_pencil):bpy.utils.unregister_tool(tool)
    if hasattr(bpy.types.Object,'wavelength_cutter'):del bpy.types.Object.wavelength_cutter
    if hasattr(bpy.types.Scene,'wavelength_draw'):del bpy.types.Scene.wavelength_draw
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)
