"""Viewport mesh diagnostics: explicit scans, automatic failure capture and live repair feedback."""
import json,math,textwrap
import bpy,bmesh,gpu,blf
from mathutils import Vector
from bpy_extras import view3d_utils
from gpu_extras.batch import batch_for_shader
from bpy.app.handlers import persistent
from . import workspace,profiles,geometry_diagnostics

_handles=[];_pending=set();_dirty=set();_busy=False;_cache={}

class WLGeometryIssue(bpy.types.PropertyGroup):
    target:bpy.props.PointerProperty(type=bpy.types.Object)
    code:bpy.props.StringProperty()
    message:bpy.props.StringProperty()
    hint:bpy.props.StringProperty()
    details:bpy.props.StringProperty()
    evaluated:bpy.props.BoolProperty()

class WLGeometryDebug(bpy.types.PropertyGroup):
    issues:bpy.props.CollectionProperty(type=WLGeometryIssue)
    active:bpy.props.IntProperty(default=0,min=0)
    overlay:bpy.props.BoolProperty(name='Show Geometry Problems',default=True)
    live:bpy.props.BoolProperty(name='Refresh After Edits',default=True)
    engine:bpy.props.StringProperty()


def inspect(obj,scene):
    if obj.get('wl_csg'):return None  # Convexity belongs to the pending conversion, not the live preview.
    if obj.type!='MESH' or obj.get('wl_exclude') or obj.get('wl_role')!='BRUSH':return None
    if not profiles.requires_convex_brushes(scene.wavelength.engine):return None
    evaluated=bool(obj.modifiers);owner=None;mesh=None
    try:
        if obj.mode=='EDIT' and not evaluated:
            bm=bmesh.from_edit_mesh(obj.data);bm.verts.ensure_lookup_table();bm.verts.index_update()
            local=[tuple(v.co) for v in bm.verts];faces=[[v.index for v in f.verts] for f in bm.faces]
        else:
            owner=obj.evaluated_get(bpy.context.evaluated_depsgraph_get()) if evaluated else None
            mesh=owner.to_mesh() if owner else obj.data
            local=[tuple(v.co) for v in mesh.vertices];faces=[list(f.vertices) for f in mesh.polygons]
        unit=obj.get('wl_unit_meters',profiles.unit_meters(scene.wavelength))
        world=[tuple(c/unit for c in obj.matrix_world@Vector(v)) for v in local]
        result=geometry_diagnostics.problem(world,faces)
        if result:
            result['positions']=local;result['polygons']=faces;result['evaluated']=evaluated
        return result
    finally:
        if owner and mesh:owner.to_mesh_clear()


def redraw():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type in {'VIEW_3D','PROPERTIES'}:area.tag_redraw()


def scan(scene,targets=None):
    global _busy
    if _busy:return
    _busy=True
    try:
        state=scene.wavelength_geometry_debug
        active=state.issues[min(state.active,len(state.issues)-1)] if state.issues else None
        active_key=(active.target.as_pointer(),active.code) if active and active.target else None
        targets=list(scene.objects) if targets is None else list(targets)
        pointers={obj.as_pointer() for obj in targets}
        for i in reversed(range(len(state.issues))):
            obj=state.issues[i].target
            if obj is None or obj.as_pointer() in pointers:state.issues.remove(i)
        for obj in targets:
            result=inspect(obj,scene)
            if not result:continue
            issue=state.issues.add();issue.target=obj
            for key in ('code','message','hint','evaluated'):setattr(issue,key,result[key])
            issue.details=json.dumps(result)
        state.engine=scene.wavelength.engine;state.active=next((i for i,item in enumerate(state.issues) if item.target and (item.target.as_pointer(),item.code)==active_key),min(state.active,max(0,len(state.issues)-1)))
        _cache.clear();redraw()
    finally:_busy=False


def capture(exception):
    """Queue names only: logging may originate outside the main Blender thread."""
    name=getattr(exception,'object_name',None)
    if isinstance(name,str) and name:_pending.add(name)

@persistent
def changed(scene,depsgraph):
    if _busy or not hasattr(scene,'wavelength_geometry_debug'):return
    state=scene.wavelength_geometry_debug
    if not state.live or not state.issues:return
    watched={block.as_pointer() for i in state.issues if i.target for block in (i.target,getattr(i.target,'data',None)) if block}
    if any(update.id.original.as_pointer() in watched for update in depsgraph.updates):
        _dirty.add(scene.as_pointer());_cache.clear()


@persistent
def reset(_unused=None):
    _pending.clear();_dirty.clear();_cache.clear()


def tick():
    pending=set(_pending);_pending.difference_update(pending)
    for scene in bpy.data.scenes:
        if not hasattr(scene,'wavelength_geometry_debug') or not hasattr(scene,'wavelength'):continue
        state=scene.wavelength_geometry_debug
        if any(i.target is None for i in state.issues):scan(scene,[])
        targets={i.target for i in state.issues if i.target} if state.live and (scene.as_pointer() in _dirty or state.engine!=scene.wavelength.engine) else set()
        targets.update(obj for obj in scene.objects if obj.name in pending)
        if targets:
            try:scan(scene,targets)
            except (ReferenceError,RuntimeError,ValueError):pass
        _dirty.discard(scene.as_pointer())
    return .4


def _details(issue):
    key=issue.as_pointer()
    if key not in _cache:_cache[key]=json.loads(issue.details)
    return _cache[key]


def draw_geometry():
    context=bpy.context
    if not context.region_data or not workspace.active(context,'gizmos') or not context.space_data.overlay.show_overlays:return
    state=getattr(context.scene,'wavelength_geometry_debug',None)
    if not state or not state.issues or not state.overlay or state.engine!=context.scene.wavelength.engine:return
    shader=gpu.shader.from_builtin('UNIFORM_COLOR')
    depth=gpu.state.depth_test_get();blend=gpu.state.blend_get()
    try:
        gpu.state.depth_test_set('NONE');gpu.state.blend_set('ALPHA')
        for issue in state.issues:
            obj=issue.target
            if not obj or obj.name not in context.view_layer.objects or not obj.visible_get():continue
            data=_details(issue)
            required=set(data['vertices'])|{i for edge in data['edges'] for i in edge}|{i for f in data['faces'] for i in data['polygons'][f]}
            positions={i:obj.matrix_world@Vector(data['positions'][i]) for i in required if i<len(data['positions'])}
            points=[positions[i] for i in data['vertices'] if i in positions and all(math.isfinite(c) for c in positions[i])]
            edges=list(data['edges'])
            for f in data['faces']:
                polygon=data['polygons'][f];edges.extend(zip(polygon,polygon[1:]+polygon[:1]))
            lines=[positions[i] for edge in edges for i in edge if i in positions]
            lines=[v for v in lines if all(math.isfinite(c) for c in v)]
            color=(1,.12,.48,1) if issue.code=='DUPLICATE_VERTEX' else (1,.23,.06,1)
            shader.bind();shader.uniform_float('color',color)
            if lines and len(lines)%2==0:batch_for_shader(shader,'LINES',{'pos':lines}).draw(shader)
            if points:
                gpu.state.point_size_set(12);batch_for_shader(shader,'POINTS',{'pos':points}).draw(shader)
    finally:gpu.state.point_size_set(1);gpu.state.depth_test_set(depth);gpu.state.blend_set(blend)


def draw_labels():
    context=bpy.context
    if not context.region_data or not workspace.active(context,'gizmos') or not context.space_data.overlay.show_overlays:return
    state=getattr(context.scene,'wavelength_geometry_debug',None)
    if not state or not state.issues or not state.overlay or state.engine!=context.scene.wavelength.engine:return
    for issue in state.issues:
        obj=issue.target
        if not obj or obj.name not in context.view_layer.objects or not obj.visible_get():continue
        data=_details(issue);points=[Vector(data['positions'][i]) for i in data['vertices'] if i<len(data['positions']) and all(math.isfinite(c) for c in data['positions'][i])]
        center=obj.matrix_world@(sum(points,Vector())/len(points)) if points else obj.matrix_world.translation
        xy=view3d_utils.location_3d_to_region_2d(context.region,context.region_data,center)
        if xy is None:continue
        label=f'{obj.name}: '+(f'Coincident vertices ({len(data["vertices"])})' if issue.code=='DUPLICATE_VERTEX' else issue.message)
        blf.size(0,13);width=blf.dimensions(0,label)[0]
        sidebar=next((r.width for r in context.area.regions if r.type=='UI'),0) if context.space_data.show_region_ui else 0
        right=context.region.width-sidebar-8
        x=xy.x+14 if xy.x+14+width<right else xy.x-width-14
        blf.position(0,max(8,min(x,right-width)),xy.y+14,0);blf.color(0,1,.35,.35,1)
        blf.enable(0,blf.SHADOW);blf.shadow(0,5,0,0,0,1)
        blf.draw(0,label)
        blf.disable(0,blf.SHADOW)

class WL_UL_geometry_issues(bpy.types.UIList):
    def draw_item(self,context,layout,data,item,icon,active_data,active_propname,index):
        layout.label(text=item.target.name if item.target else 'Deleted object',icon='ERROR')

class WL_OT_check_geometry(bpy.types.Operator):
    bl_idname='wavelength.check_geometry';bl_label='Check Geometry';bl_description='Locate invalid brush geometry without modifying meshes'
    def execute(self,context):
        scan(context.scene);self.report({'INFO'},f'{len(context.scene.wavelength_geometry_debug.issues)} geometry problem(s)');return {'FINISHED'}

class WL_OT_clear_geometry_problems(bpy.types.Operator):
    bl_idname='wavelength.clear_geometry_problems';bl_label='Clear Geometry Problems'
    def execute(self,context):context.scene.wavelength_geometry_debug.issues.clear();redraw();return {'FINISHED'}

class WL_OT_select_geometry_problem(bpy.types.Operator):
    bl_idname='wavelength.select_geometry_problem';bl_label='Select Problem Geometry';bl_options={'REGISTER','UNDO'}
    frame:bpy.props.BoolProperty(default=False)
    def execute(self,context):
        state=context.scene.wavelength_geometry_debug
        if not state.issues:return {'CANCELLED'}
        issue=state.issues[min(state.active,len(state.issues)-1)];obj=issue.target
        if not obj or obj.name not in context.view_layer.objects:return {'CANCELLED'}
        code=issue.code;scan(context.scene,[obj])
        issue=next((i for i in state.issues if i.target==obj and i.code==code),None)
        if issue is None:self.report({'INFO'},'This problem is already fixed; diagnostics refreshed');return {'CANCELLED'}
        if context.object and context.object.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);context.view_layer.objects.active=obj
        if not issue.evaluated and not obj.library and not obj.data.library:
            details=json.loads(issue.details);bpy.ops.object.mode_set(mode='EDIT');context.tool_settings.mesh_select_mode=(True,False,False)
            bm=bmesh.from_edit_mesh(obj.data);bm.verts.ensure_lookup_table();bm.faces.ensure_lookup_table()
            for face in bm.faces:face.select_set(False)
            for edge in bm.edges:edge.select_set(False)
            for vertex in bm.verts:vertex.select_set(False)
            for index in details['vertices']:
                if index<len(bm.verts):bm.verts[index].hide_set(False);bm.verts[index].select_set(True)
            bm.select_flush_mode();bmesh.update_edit_mesh(obj.data,loop_triangles=False,destructive=False)
        else:self.report({'INFO'},'Evaluated geometry: Finalize Geometry before selecting individual elements')
        if self.frame:
            area=context.area if context.area and context.area.type=='VIEW_3D' else next((a for a in context.screen.areas if a.type=='VIEW_3D'),None)
            if area:
                region=next(r for r in area.regions if r.type=='WINDOW')
                with context.temp_override(area=area,region=region):bpy.ops.view3d.view_selected(use_all_regions=False)
        return {'FINISHED'}

class WL_PT_geometry_problems(bpy.types.Panel):
    bl_order=-100
    bl_label='Geometry Problems';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='wavelength'
    @classmethod
    def poll(cls,context):return workspace.active(context)
    def draw(self,context):
        layout=self.layout;state=context.scene.wavelength_geometry_debug
        row=layout.row(align=True);row.operator('wavelength.check_geometry',icon='VIEWZOOM');row.operator('wavelength.clear_geometry_problems',text='',icon='X')
        layout.prop(state,'overlay');layout.prop(state,'live')
        if not profiles.requires_convex_brushes(context.scene.wavelength.engine):layout.label(text='This profile does not require BSP brush geometry');return
        layout.template_list('WL_UL_geometry_issues','',state,'issues',state,'active',rows=3)
        if state.issues:
            issue=state.issues[min(state.active,len(state.issues)-1)]
            for line in textwrap.wrap(issue.message+' '+issue.hint,width=max(20,int((context.region.width-40)/9))):layout.label(text=line)
            details=json.loads(issue.details);layout.label(text=f'{len(details["vertices"])} vertices · {len(details["edges"])} edges · {len(details["faces"])} faces')
            row=layout.row(align=True);row.operator('wavelength.select_geometry_problem',text='Select Geometry',icon='VERTEXSEL')
            row.operator('wavelength.select_geometry_problem',text='Frame',icon='ZOOM_SELECTED').frame=True
            if issue.evaluated:layout.label(text='Evaluated result: finalize before editing',icon='MOD_NODES')

CLASSES=(WLGeometryIssue,WLGeometryDebug,WL_UL_geometry_issues,WL_OT_check_geometry,WL_OT_clear_geometry_problems,WL_OT_select_geometry_problem,WL_PT_geometry_problems)
def register():
    for cls in CLASSES:bpy.utils.register_class(cls)
    bpy.types.Scene.wavelength_geometry_debug=bpy.props.PointerProperty(type=WLGeometryDebug)
    _handles.extend([bpy.types.SpaceView3D.draw_handler_add(draw_geometry,(),'WINDOW','POST_VIEW'),bpy.types.SpaceView3D.draw_handler_add(draw_labels,(),'WINDOW','POST_PIXEL')])
    bpy.app.handlers.depsgraph_update_post.append(changed)
    bpy.app.handlers.load_post.append(reset)
    bpy.app.timers.register(tick,first_interval=.4,persistent=True)
def unregister():
    if bpy.app.timers.is_registered(tick):bpy.app.timers.unregister(tick)
    if changed in bpy.app.handlers.depsgraph_update_post:bpy.app.handlers.depsgraph_update_post.remove(changed)
    if reset in bpy.app.handlers.load_post:bpy.app.handlers.load_post.remove(reset)
    for handle in _handles:bpy.types.SpaceView3D.draw_handler_remove(handle,'WINDOW')
    _handles.clear();_pending.clear();_dirty.clear();_cache.clear()
    del bpy.types.Scene.wavelength_geometry_debug
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)
