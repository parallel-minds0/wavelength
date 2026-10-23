"""Source brush-face displacement attachments; preserve the original solid."""
import json
import bpy,bmesh
from bpy.props import BoolProperty
from mathutils import Vector,Matrix
from . import profiles,workspace

MASK='wavelength.displacement.face_mask'
WARP='wavelength.displacement.face_warp'
_SIGNATURES={}


def corners(obj):return [Vector(p) for p in json.loads(obj['wl_terrain_face_corners'])]


def position(obj,u,v,quad=None):
    a,b,c,d=quad if quad is not None else corners(obj)
    return a*((1-u)*(1-v))+b*(u*(1-v))+c*(u*v)+d*((1-u)*v)


def parameters(obj,p,quad=None):
    """Invert a convex planar bilinear quad, including its boundary."""
    a,b,c,d=quad if quad is not None else corners(obj);e=b-a;f=d-a;g=a-b+c-d;u=v=.5
    for _ in range(16):
        delta=a+e*u+f*v+g*(u*v)-Vector((p.x,p.y,0))
        du=e+g*v;dv=f+g*u;det=du.x*dv.y-du.y*dv.x
        if abs(det)<1e-14:raise ValueError('Displacement face became degenerate')
        x=(delta.x*dv.y-delta.y*dv.x)/det;y=(du.x*delta.y-du.y*delta.x)/det
        u-=x;v-=y
        if max(abs(x),abs(y))<1e-6:return u,v
    raise ValueError('Displacement no longer fits its brush face')


def mask_group():
    name='Wavelength · Displaced Brush Faces · v1';tree=bpy.data.node_groups.get(name)
    if tree:return tree
    tree=bpy.data.node_groups.new(name,'GeometryNodeTree');tree['wl_generator']=MASK
    tree.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry');tree.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    inp=tree.nodes.new('NodeGroupInput');out=tree.nodes.new('NodeGroupOutput')
    attr=tree.nodes.new('GeometryNodeInputNamedAttribute');attr.data_type='BOOLEAN';attr.inputs['Name'].default_value='wl_displacement_surface'
    delete=tree.nodes.new('GeometryNodeDeleteGeometry');delete.domain='FACE'
    tree.links.new(inp.outputs[0],delete.inputs['Geometry']);tree.links.new(attr.outputs['Attribute'],delete.inputs['Selection']);tree.links.new(delete.outputs[0],out.inputs[0])
    inp.location=(-400,100);attr.location=(-400,-100);delete.location=(-100,100);out.location=(120,100)
    return tree


def refresh(source):
    attr=source.data.attributes.get('wl_displacement_surface') or source.data.attributes.new('wl_displacement_surface','BOOLEAN','FACE')
    ids=source.data.attributes.get('wl_face_id')
    attached={o.get('wl_terrain_face_id') for o in bpy.context.scene.objects if o.get('wl_terrain_face_corners') and not o.get('wl_exclude') and o.wavelength_terrain.surface_source==source}
    for index,datum in enumerate(attr.data):datum.value=bool(ids and ids.data[index].value in attached)
    if attached and not any(m.type=='NODES' and m.node_group and m.node_group.get('wl_generator')==MASK for m in source.modifiers):
        modifier=source.modifiers.new('Wavelength · Displaced Faces','NODES');modifier.node_group=mask_group()
    source.data.update();source.update_tag()


@bpy.app.handlers.persistent
def sync_masks(scene,*args):
    sources=set();attachments={}
    for o in scene.objects:
        if o.get('wl_terrain_face_corners') and not o.get('wl_terrain_detached') and o.wavelength_terrain.surface_source is None:detach(o)
        if o.type=='MESH' and any(m.type=='NODES' and m.node_group and m.node_group.get('wl_generator')==MASK for m in o.modifiers):sources.add(o)
        if o.get('wl_terrain_face_corners') and not o.get('wl_exclude'):
            attachments.setdefault(o.wavelength_terrain.surface_source,[]).append((o.as_pointer(),o.get('wl_terrain_face_id',0)))
    for source in sources:
        if source.mode!='OBJECT':continue
        attached=tuple(sorted(attachments.get(source,[])))
        signature=(source.data.as_pointer(),len(source.data.polygons),attached)
        if _SIGNATURES.get(source.as_pointer())!=signature:
            _SIGNATURES[source.as_pointer()]=signature;refresh(source)


def warp(obj):
    """Map the generated grid onto its original four-sided brush surface in nodes."""
    tree=bpy.data.node_groups.new('Wavelength · Brush Face Surface','GeometryNodeTree');tree['wl_generator']=WARP
    tree.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry');tree.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
    nodes=tree.nodes;links=tree.links;inp=nodes.new('NodeGroupInput');out=nodes.new('NodeGroupOutput');p=nodes.new('GeometryNodeInputPosition');xyz=nodes.new('ShaderNodeSeparateXYZ');links.new(p.outputs[0],xyz.inputs[0])
    def math(op,a,b):
        n=nodes.new('ShaderNodeMath');n.operation=op
        for value,socket in ((a,n.inputs[0]),(b,n.inputs[1])):
            if isinstance(value,(int,float)):socket.default_value=value
            else:links.new(value,socket)
        return n.outputs[0]
    s=obj.wavelength_terrain;unit=obj['wl_unit_meters'];u=math('ADD',math('DIVIDE',xyz.outputs['X'],s.width*unit),.5);v=math('ADD',math('DIVIDE',xyz.outputs['Y'],s.length*unit),.5)
    a,b,c,d=corners(obj);e=b-a;f=d-a;g=a-b+c-d;uv=math('MULTIPLY',u,v)
    result=nodes.new('ShaderNodeCombineXYZ')
    for index,key in enumerate(('X','Y')):
        val=math('ADD',a[index],math('ADD',math('MULTIPLY',u,e[index]),math('ADD',math('MULTIPLY',v,f[index]),math('MULTIPLY',uv,g[index]))));links.new(val,result.inputs[key])
    links.new(xyz.outputs['Z'],result.inputs['Z'])
    setpos=nodes.new('GeometryNodeSetPosition');links.new(inp.outputs[0],setpos.inputs['Geometry']);links.new(result.outputs[0],setpos.inputs['Position']);links.new(setpos.outputs[0],out.inputs[0])
    for index,n in enumerate(nodes):n.location=((index%7)*200,-(index//7)*200)
    modifier=obj.modifiers.new('Wavelength · Brush Face Surface','NODES');modifier.node_group=tree


def detach(obj):
    """Keep the saved face domain and current world geometry, not a live brush."""
    world=obj.matrix_world.copy();source=obj.wavelength_terrain.surface_source
    obj.parent=None;obj.matrix_world=world;obj.wavelength_terrain.surface_source=None
    obj['wl_terrain_detached']=True
    if source and source.name in bpy.context.scene.objects:refresh(source)
    return obj


def consume(source):
    bpy.context.view_layer.update()
    children=[o for o in bpy.context.scene.objects if o.get('wl_terrain_face_corners') and o.wavelength_terrain.surface_source==source]
    for obj in children:detach(obj)
    mesh=source.data;bpy.data.objects.remove(source,do_unlink=True)
    if mesh.users==0:bpy.data.meshes.remove(mesh)


def validate_attachment(obj):
    if obj.get('wl_terrain_detached'):return None,obj.get('wl_terrain_face_id',0)
    source=obj.wavelength_terrain.surface_source
    if source is None or source.name not in bpy.context.scene.objects:
        # Old files already store all four base corners and their local frame.
        # Deleting the original brush need not destroy this independent domain.
        detach(obj);return None,obj.get('wl_terrain_face_id',0)
    if source.get('wl_role')!='BRUSH' or source.get('wl_entity_id'):raise ValueError('Displacement source must remain a world brush')
    if obj.parent!=source:raise ValueError('Keep the displacement parented to its source brush')
    if any(abs(obj.matrix_parent_inverse[i][j]-(1 if i==j else 0))>1e-6 for i in range(4) for j in range(4)):raise ValueError('Move the source brush to move its attached displacement')
    ids=source.data.attributes.get('wl_face_id');fid=obj['wl_terrain_face_id']
    face=next((p for p in source.data.polygons if ids and ids.data[p.index].value==fid),None)
    if face is None or len(face.vertices)!=4:raise ValueError('Displacement source face was removed or changed; recreate the displacement')
    original=[Vector(p) for p in json.loads(obj['wl_terrain_source_corners'])]
    current=[source.data.vertices[i].co for i in face.vertices]
    if any((a-b).length>1e-6 for a,b in zip(original,current)):raise ValueError('Source face geometry changed; recreate its displacement')
    expected=Matrix(json.loads(obj['wl_terrain_face_matrix']))
    if any(abs(obj.matrix_basis[i][j]-expected[i][j])>1e-5 for i in range(4) for j in range(4)):raise ValueError('Move the source brush to move its attached displacement')
    return source,fid


def create(context,independent=True,world_domain=None):
    from . import terrain,scene,primitive_ui,procedural
    source=context.object;settings=context.scene.wavelength
    if world_domain is None:world_domain=independent
    if not source or source.type!='MESH' or source.get('wl_role')!='BRUSH':raise ValueError('Select one face of a Wavelength brush in Edit Mode')
    if not profiles.is_source(settings.engine):raise ValueError('Activate a Source profile')
    if source.get('wl_entity_id'):raise ValueError('Source displacements must belong to world brushes')
    root=primitive_ui.root_for(source)
    # The assembly root owns regeneration. Mesh parts can retain copied/stale
    # state tags after joining, duplicating or older finalization workflows.
    if root and procedural.state(root)=='PROCEDURAL':raise ValueError(f'{root.name}: Finalize Geometry on the procedural assembly before creating its displacement')
    modifiers=[m for m in source.modifiers if not (m.type=='NODES' and m.node_group and m.node_group.get('wl_generator')==MASK)]
    if modifiers:
        generated=[m for m in modifiers if m.type=='NODES' and m.node_group and str(m.node_group.get('wl_generator','')).startswith('wavelength.geometry_nodes.')]
        if generated:raise ValueError(f'{source.name}: finalize its live generator ({generated[0].name}) before creating a displacement')
        raise ValueError(f'{source.name}: apply or remove modifier "{modifiers[0].name}" before creating a displacement; the selected face must match the export mesh')
    if context.mode!='EDIT_MESH':raise ValueError('Select exactly one brush face in Edit Mode')
    if len(context.objects_in_mode)!=1:raise ValueError('Edit one brush at a time when creating a displacement')
    bm=bmesh.from_edit_mesh(source.data);selected=[f for f in bm.faces if f.select and not f.hide]
    if len(selected)!=1:raise ValueError('Select exactly one brush face')
    face=selected[0]
    if len(face.verts)!=4:raise ValueError('Source displacement needs a planar convex four-sided face')
    bm.faces.index_update()
    index=face.index;points=[v.co.copy() for v in face.verts];n=face.normal.normalized();u=(points[1]-points[0]).normalized();v=n.cross(u).normalized()
    if any(abs((p-points[0]).dot(n))>1e-6 for p in points) or any((points[(i+1)%4]-points[i]).cross(points[(i+2)%4]-points[(i+1)%4]).dot(n)<=1e-10 for i in range(4)):raise ValueError('Source displacement needs a planar convex four-sided face')
    unit=profiles.unit_meters(settings)
    if abs(source.get('wl_unit_meters',unit)-unit)>1e-8:raise ValueError('Activate the brush owning unit profile first')
    owner=source.get('wl_owner_profile')
    if owner and owner!=settings.engine:raise ValueError('Activate the brush owning Source profile first')
    bpy.ops.object.mode_set(mode='OBJECT');obj=None
    try:
        scene.mark_brush(source);fid=source.data.attributes['wl_face_id'].data[index].value
        if any(o.get('wl_terrain_face_id')==fid and o.get('wl_terrain_face_corners') and o.wavelength_terrain.surface_source==source for o in context.scene.objects):raise ValueError('This face already has a displacement')
        brush=scene.brush_from_object(source,settings.engine)
        face_ids=sorted(d.value for d in source.data.attributes['wl_face_id'].data)
        outward=Vector(brush[face_ids.index(fid)].plane()[0])
        origin=sum(points,Vector())/4;frame=Matrix((u,v,n)).transposed().to_4x4();frame.translation=origin
        domain=points
        if world_domain:
            domain=[source.matrix_world@p for p in points];u=(domain[1]-domain[0]).normalized();n=(domain[1]-domain[0]).cross(domain[2]-domain[0]).normalized();v=n.cross(u).normalized()
            frame=Matrix((u,v,n)).transposed().to_4x4();frame.translation=sum(domain,Vector())/4
        local=[frame.inverted()@p for p in domain];width=max(p.x for p in local)-min(p.x for p in local);length=max(p.y for p in local)-min(p.y for p in local)
        mat=source.data.materials[source.data.polygons[index].material_index] if source.data.materials else None
        obj=terrain.create(context,paintable_surface=True);obj.name=source.name+' · Displacement'
        if world_domain:obj.matrix_world=frame;obj['wl_terrain_detached']=True
        else:obj.parent=source;obj.matrix_parent_inverse=Matrix.Identity(4);obj.matrix_basis=frame
        obj['wl_terrain_face_corners']=json.dumps([list(p) for p in local]);obj['wl_terrain_source_corners']=json.dumps([list(p) for p in points]);obj['wl_terrain_face_matrix']=json.dumps([list(row) for row in frame]);obj['wl_terrain_face_id']=fid
        s=obj.wavelength_terrain;s.surface_source=source;s.width=width/unit;s.length=length/unit;s.amplitude=0;s.elevation=0;s.tiles_x=s.tiles_y=1
        if mat:obj.data.materials.append(mat)
        # Convex brush export corrects reversed mesh winding. Terrain must use
        # that same outward front, not inherit an inward/mirrored mesh normal.
        world_frame=frame if world_domain else source.matrix_world@frame
        front=(world_frame.to_3x3().inverted().transposed()@Vector((0,0,1))).normalized()
        obj['wl_terrain_reverse_facing']=front.dot(outward)<0
        terrain.update(obj);warp(obj);terrain.update_facing(obj);refresh(source);context.view_layer.update()
        if independent:consume(source)
        return obj
    except Exception:
        if obj:
            data=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
            if data.users==0:bpy.data.meshes.remove(data)
        context.view_layer.objects.active=source;source.select_set(True);bpy.ops.object.mode_set(mode='EDIT');raise


def apply(source,brush,attachments):
    ids=sorted(d.value for d in source.data.attributes['wl_face_id'].data)
    from . import terrain
    seen=set()
    for obj in attachments:
        _,fid=validate_attachment(obj)
        if fid in seen:raise ValueError('Multiple displacement objects claim the same brush face; remove the duplicate')
        seen.add(fid);parts=terrain.brushes(obj,validate_seams=False)
        if len(parts)!=1:raise ValueError('A brush-face displacement must have exactly one patch')
        generated=parts[0][0];face=brush[ids.index(fid)]
        face.vmf=dict(face.vmf or {});face.vmf['dispinfo']=generated.vmf['dispinfo'];face.texture=generated.texture
    return brush


class WL_OT_displacement_from_face(bpy.types.Operator):
    bl_idname='wavelength.displacement_from_face';bl_label='Create Displacement from Face';bl_options={'REGISTER','UNDO'}
    bl_description='Convert selected quad faces to independent paintable surfaces and remove the backing brush; undo restores it'
    independent:BoolProperty(default=True,options={'HIDDEN','SKIP_SAVE'})
    @classmethod
    def poll(cls,context):return workspace.active(context) and context.mode=='EDIT_MESH' and context.object and context.object.get('wl_role')=='BRUSH' and profiles.is_source(context.scene.wavelength.engine)
    def execute(self,context):
        try:
            if not self.independent:create(context,independent=False)
            else:
                source=context.object;bm=bmesh.from_edit_mesh(source.data);bm.faces.index_update()
                selected=[f.index for f in bm.faces if f.select and not f.hide]
                if not selected:raise ValueError('Select at least one quad face')
                if any(len(f.verts)!=4 for f in bm.faces if f.select and not f.hide):raise ValueError('Every selected displacement face must be a quad')
                created=[]
                try:
                    for index in selected:
                        if context.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
                        bpy.ops.object.select_all(action='DESELECT');source.select_set(True);context.view_layer.objects.active=source;bpy.ops.object.mode_set(mode='EDIT')
                        bm=bmesh.from_edit_mesh(source.data);bm.faces.ensure_lookup_table()
                        for f in bm.faces:f.select_set(False)
                        bm.faces[index].select_set(True);bmesh.update_edit_mesh(source.data)
                        created.append(create(context,independent=False,world_domain=True))
                    consume(source)
                    bpy.ops.object.select_all(action='DESELECT')
                    for obj in created:obj.select_set(True)
                    context.view_layer.objects.active=created[0]
                except Exception:
                    for obj in created:
                        mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
                        if mesh.users==0:bpy.data.meshes.remove(mesh)
                    if source.name in context.scene.objects:refresh(source)
                    raise
        except (ValueError,RuntimeError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        return {'FINISHED'}


class WL_OT_displacement_detach(bpy.types.Operator):
    bl_idname='wavelength.displacement_detach';bl_label='Detach Displacements';bl_options={'REGISTER','UNDO'}
    bl_description='Make selected legacy surfaces independent and remove their backing brushes; retain shape, materials and sewn connections'
    @classmethod
    def poll(cls,context):return workspace.active(context) and context.mode=='OBJECT' and context.object and context.object.get('wl_terrain_face_corners')
    def execute(self,context):
        selected=[o for o in context.selected_objects if o.get('wl_terrain_face_corners')];sources={o.wavelength_terrain.surface_source for o in selected if o.wavelength_terrain.surface_source}
        for source in sources:consume(source)
        for obj in selected:
            if not obj.get('wl_terrain_detached'):detach(obj)
        return {'FINISHED'}


def menu(self,context):
    if WL_OT_displacement_from_face.poll(context):self.layout.operator(WL_OT_displacement_from_face.bl_idname,icon='MESH_GRID')


def object_menu(self,context):
    if WL_OT_displacement_detach.poll(context):self.layout.operator('wavelength.displacement_detach')


def register():
    bpy.utils.register_class(WL_OT_displacement_from_face)
    bpy.utils.register_class(WL_OT_displacement_detach);bpy.types.VIEW3D_MT_object_context_menu.append(object_menu)
    bpy.types.VIEW3D_MT_edit_mesh_faces.append(menu);bpy.types.VIEW3D_MT_edit_mesh_context_menu.append(menu)
    bpy.app.handlers.depsgraph_update_post.append(sync_masks)


def unregister():
    if sync_masks in bpy.app.handlers.depsgraph_update_post:bpy.app.handlers.depsgraph_update_post.remove(sync_masks)
    _SIGNATURES.clear()
    bpy.types.VIEW3D_MT_object_context_menu.remove(object_menu);bpy.utils.unregister_class(WL_OT_displacement_detach)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(menu);bpy.types.VIEW3D_MT_edit_mesh_faces.remove(menu)
    bpy.utils.unregister_class(WL_OT_displacement_from_face)
