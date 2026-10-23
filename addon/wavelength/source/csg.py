"""Editable node Booleans and transactional, profile-owned BSP finalization."""
import json
import bpy,bmesh
from bpy.props import EnumProperty
from mathutils import Vector
from . import profiles,scene,node_pencil,bsp_decompose,context_policy

KEY='wl_csg'

def _solid(mesh):
    bm=bmesh.new()
    try:
        bm.from_mesh(mesh)
        if not bm.faces or any(not e.is_manifold or not e.is_contiguous for e in bm.edges):raise ValueError('CSG requires closed manifold meshes with consistent face winding')
        if abs(bm.calc_volume())<1e-12:raise ValueError('CSG requires nonzero volume')
    finally:bm.free()

def _editable(obj):
    if obj.type!='MESH' or obj.library or obj.data.library or obj.override_library:raise ValueError('Use editable local mesh objects')
    if obj.get('wl_procedural_state')=='PROCEDURAL' or obj.modifiers:raise ValueError('Finalize Geometry and apply other modifiers before starting CSG')
    if obj.get('wl_terrain') or obj.get('wl_displacement') or obj.get('wl_custom_model_owner'):raise ValueError('Use ordinary solid meshes for CSG')
    if obj.get('wl_csg_target'):raise ValueError('This object is already a live CSG cutter')
    if abs(obj.matrix_world.determinant())<1e-12:raise ValueError('Apply a nonzero scale before CSG')
    _solid(obj.data)

def start(context,target,cutter,operation):
    _editable(target);_editable(cutter)
    engine=context.scene.wavelength.engine
    for obj in (target,cutter):
        owner=obj.get('wl_owner_profile',obj.get('wl_engine',engine))
        if owner!=engine:raise ValueError('CSG operands must belong to the active profile; convert ownership explicitly first')
    modifier=node_pencil.boolean(target,cutter,operation)
    modifier.name='wavelength · CSG Preview'
    snapshot={key:target.get(key) for key in ('wl_procedural_state','wl_owner_profile','wl_unit_meters')}
    target[KEY]=json.dumps({'operation':operation,'modifier':modifier.name,'engine':engine,'target':snapshot,
                          'display':cutter.display_type,'render':cutter.hide_render,'exclude':cutter.get('wl_exclude')})
    target['wl_csg_cutter']=cutter;cutter['wl_csg_target']=target
    target['wl_procedural_state']='PROCEDURAL';target['wl_owner_profile']=engine
    target['wl_unit_meters']=target.get('wl_unit_meters',profiles.unit_meters(context.scene.wavelength))
    cutter.display_type='WIRE';cutter.hide_render=True;cutter['wl_exclude']=True
    context.view_layer.update()

def _restore(obj,key,value):
    if value is None:
        if key in obj:del obj[key]
    else:obj[key]=value

def inherit_caps(mesh,target):
    """An untextured cutter inherits a used target material, never an empty slot."""
    fallback=next((target.data.materials[p.material_index] for p in target.data.polygons
                   if p.material_index<len(target.data.materials) and target.data.materials[p.material_index]),None)
    if fallback is None:return
    index=next((i for i,m in enumerate(mesh.materials) if m==fallback),None)
    if index is None:index=len(mesh.materials);mesh.materials.append(fallback)
    caps=[p for p in mesh.polygons if p.material_index>=len(mesh.materials) or mesh.materials[p.material_index] is None]
    if not caps:return
    from . import formats
    from .geometry import face_plane,dot
    unit=target.get('wl_unit_meters',1.)
    positions=[tuple(c/unit for c in target.matrix_world@v.co) for v in mesh.vertices]
    for name in [layer.name for layer in target.data.uv_layers] or ['UVMap']:
        layer=mesh.uv_layers.get(name) or mesh.uv_layers.new(name=name)
        for polygon in caps:
            _,normal,_=face_plane(positions,list(polygon.vertices));axes=formats.quake_axes(normal,(0,0,0,1,1))
            for loop in polygon.loop_indices:
                p=positions[mesh.loops[loop].vertex_index]
                layer.data[loop].uv=(dot(axes[0][:3],p)/fallback.get('wl_width',64),1-dot(axes[1][:3],p)/fallback.get('wl_height',64))
    for polygon in caps:polygon.material_index=index

def cancel(target):
    record=json.loads(target[KEY]);modifier=target.modifiers.get(record['modifier'])
    if modifier:target.modifiers.remove(modifier)
    cutter=target.get('wl_csg_cutter')
    if cutter:
        cutter.display_type=record['display'];cutter.hide_render=record['render'];_restore(cutter,'wl_exclude',record['exclude'])
        if 'wl_csg_target' in cutter:del cutter['wl_csg_target']
    for key,value in record['target'].items():_restore(target,key,value)
    del target[KEY]
    if 'wl_csg_cutter' in target:del target['wl_csg_cutter']

def _bsp_meshes(mesh,target,engine):
    """Preserve boundary planes/materials; project UVs for newly created caps."""
    unit=target.get('wl_unit_meters',profiles.unit_meters(bpy.context.scene.wavelength))
    # Partition in the target's own frame. A world-aligned bounding box would
    # introduce six unrelated planes around every rotated solid and explode the
    # exterior arrangement. Affine transforms preserve convexity; final export
    # validation below checks every part in world/engine coordinates as well.
    vertices=[tuple(c/unit for c in v.co) for v in mesh.vertices]
    mesh.calc_loop_triangles()
    faces=[list(t.vertices) for t in mesh.loop_triangles]
    triangles=[[vertices[i] for i in f] for f in faces]
    parts=bsp_decompose.decompose(vertices,faces,triangles)
    sources=[]
    from .geometry import face_plane,dot
    for polygon in mesh.polygons:
        _,n,d=face_plane(vertices,list(polygon.vertices));sources.append((n,d,polygon.material_index))
    used=next((p.material_index for p in mesh.polygons if p.material_index<len(mesh.materials) and mesh.materials[p.material_index]),0)
    outputs=[]
    try:
        for vs,fs in parts:
            data=bpy.data.meshes.new(target.name+' CSG brush');outputs.append(data)
            data.from_pydata([Vector(p)*unit for p in vs],[],fs);data.update()
            for material in mesh.materials:data.materials.append(material)
            for polygon,face in zip(data.polygons,fs):
                points=[vs[i] for i in face]
                polygon.material_index=next((index for n,d,index in sources if all(abs(dot(n,p)-d)<1e-5 for p in points)),used)
        return outputs
    except Exception:
        for data in outputs:bpy.data.meshes.remove(data)
        raise

def finalize(context,target):
    if context.mode!='OBJECT':raise ValueError('Leave Edit Mode before finalizing CSG')
    record=json.loads(target[KEY]);engine=record['engine'];cutter=target.get('wl_csg_cutter')
    if not cutter or cutter.name not in context.scene.objects:raise ValueError('The CSG cutter is missing; cancel the preview or restore the cutter')
    if context.scene.wavelength.engine!=engine:raise ValueError('Return to the owning profile before finalizing CSG')
    if len(target.modifiers)!=1 or target.modifiers[0].name!=record['modifier']:raise ValueError('Remove additional modifiers before finalizing CSG')
    context.view_layer.update();depsgraph=context.evaluated_depsgraph_get()
    mesh=bpy.data.meshes.new_from_object(target.evaluated_get(depsgraph),preserve_all_data_layers=True,depsgraph=depsgraph)
    outputs=[];created=[]
    try:
        _solid(mesh)
        inherit_caps(mesh,target)
        outputs=_bsp_meshes(mesh,target,engine) if profiles.requires_convex_brushes(engine) else [mesh]
        # Prepare copies and validate all export metadata before touching the target.
        from . import editor
        for index,data in enumerate(outputs):
            obj=target.copy();obj.data=data;obj.modifiers.clear();created.append(obj)
            for key in (KEY,'wl_csg_cutter','wl_primitive','wl_definition','wl_pencil_geometry','wl_source_guide'):
                if key in obj:del obj[key]
            obj['wl_procedural_state']='FINALIZED';obj['wl_owner_profile']=engine
            obj['wl_id']=scene.uid()
            if profiles.requires_convex_brushes(engine):
                scene.mark_brush(obj);editor.apply_uv(obj,engine)
                scene.brush_from_object(obj,engine)
        # Everything above is reversible without changing the original operands.
        old=target.data;target.data=outputs[0];target.modifiers.clear()
        for key in (KEY,'wl_csg_cutter'):del target[key]
        target['wl_procedural_state']='FINALIZED'
        if profiles.requires_convex_brushes(engine):scene.mark_brush(target)
        for obj in created[1:]:
            obj.name=target.name+' CSG Part'
            for collection in target.users_collection:collection.objects.link(obj)
        bpy.data.objects.remove(created[0]);created=created[1:]
        # The operand remains available as an excluded, hidden construction mesh.
        del cutter['wl_csg_target'];cutter.hide_set(True)
        cutter.select_set(False)
        for obj in [target]+created:obj.select_set(True)
        context.view_layer.objects.active=target
        if old.users==0:bpy.data.meshes.remove(old)
        return [target]+created
    except Exception:
        for obj in created:bpy.data.objects.remove(obj,do_unlink=True)
        raise
    finally:
        for data in set(outputs+[mesh]):
            if data.users==0:bpy.data.meshes.remove(data)

def mesh_operand(obj):
    """A finalized basic brush still has an assembly Empty around its mesh.

    Assembly selection includes both wrapper and child; resolve and deduplicate
    those IDs instead of treating them as extra CSG operands.
    """
    if obj is None:raise ValueError('Choose an active target mesh')
    if obj.type=='MESH':return obj
    from . import primitive_ui
    if primitive_ui.is_assembly_root(obj):
        if obj.get('wl_procedural_state')!='FINALIZED':raise ValueError(f'{obj.name}: Finalize Geometry before starting CSG')
        meshes=[part for part in primitive_ui.parts_for(obj) if part.type=='MESH']
        if len(meshes)==1:return meshes[0]
        raise ValueError(f'{obj.name} contains {len(meshes)} meshes; select an individual mesh for CSG')
    raise ValueError(f'{obj.name} is not a mesh or a single-mesh brush assembly')

def operands(context):
    target=mesh_operand(context.view_layer.objects.active)
    selected=list(dict.fromkeys(mesh_operand(obj) for obj in context.selected_objects))
    others=[obj for obj in selected if obj!=target]
    if target not in selected or len(others)!=1:
        raise ValueError(f'CSG needs two meshes; resolved {len(selected)}. Select a cutter, then the target last')
    return target,others[0]

def _target(context):
    obj=context.object
    try:obj=mesh_operand(obj)
    except ValueError:pass
    return obj.get('wl_csg_target') or obj if obj else None

class WL_OT_csg(bpy.types.Operator):
    bl_idname='wavelength.csg';bl_label='CSG Boolean';bl_options={'REGISTER','UNDO'}
    operation:EnumProperty(name='Operation',items=[('DIFFERENCE','Subtract','Remove the other selected mesh from the active mesh'),('UNION','Union','Combine the selected solids'),('INTERSECT','Intersect','Keep their shared volume')])
    @classmethod
    def poll(cls,context):return context.mode=='OBJECT' and context_policy.allows(context,'editing') and context.object is not None
    def execute(self,context):
        try:
            target,cutter=operands(context)
            start(context,target,cutter,self.operation)
            context.view_layer.objects.active=target
        except (ValueError,RuntimeError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        return {'FINISHED'}

class WL_OT_csg_finish(bpy.types.Operator):
    bl_idname='wavelength.csg_finish';bl_label='Finalize CSG';bl_options={'REGISTER','UNDO'}
    cancel: bpy.props.BoolProperty(default=False,options={'HIDDEN'})
    @classmethod
    def poll(cls,context):return context.mode=='OBJECT' and context_policy.allows(context,'editing') and bool(_target(context) and _target(context).get(KEY))
    def execute(self,context):
        try:
            if self.cancel:cancel(_target(context))
            else:
                parts=finalize(context,_target(context));self.report({'INFO'},f'Finalized {len(parts)} solid(s)')
        except (ValueError,RuntimeError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        return {'FINISHED'}

class WL_PT_csg(bpy.types.Panel):
    bl_label='CSG';bl_space_type='VIEW_3D';bl_region_type='UI';bl_category='wavelength'
    @classmethod
    def poll(cls,context):return context_policy.allows(context,'editing')
    def draw(self,context):
        layout=self.layout;target=_target(context)
        if target and target.get(KEY):
            layout.label(text='Target: '+target.name)
            layout.label(text='Move or edit the wire cutter to update')
            layout.operator('wavelength.csg_finish',text='Finalize Geometry',icon='CHECKMARK')
            layout.operator('wavelength.csg_finish',text='Cancel CSG',icon='X').cancel=True
        else:
            from . import primitive_ui
            if primitive_ui.WL_OT_finalize_primitive.poll(context):
                layout.label(text='Active brush is procedural')
                layout.operator('wavelength.finalize_primitive',text='Finalize Active Brush',icon='CHECKMARK')
            layout.label(text='Select cutter, then target last')
            row=layout.row(align=True)
            for operation,label in [('DIFFERENCE','Subtract'),('UNION','Union'),('INTERSECT','Intersect')]:row.operator('wavelength.csg',text=label).operation=operation

CLASSES=(WL_OT_csg,WL_OT_csg_finish,WL_PT_csg)
def register():
    for cls in CLASSES:bpy.utils.register_class(cls)
def unregister():
    for cls in reversed(CLASSES):bpy.utils.unregister_class(cls)
