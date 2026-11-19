"""Source brush-face displacement attachments; preserve the original solid."""
import json
import bpy,bmesh
from bpy.props import BoolProperty,EnumProperty,PointerProperty,StringProperty
from mathutils import Vector,Matrix
from . import profiles,workspace

MASK='wavelength.displacement.face_mask'
WARP='wavelength.displacement.face_warp'
MAPPING='wavelength.displacement.face_mapping'
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
    if any(o.get('wl_source_displacement') for o in source.children):
        from . import source_displacement
        source_displacement.mask(source)
        return
    attr=source.data.attributes.get('wl_displacement_surface') or source.data.attributes.new('wl_displacement_surface','BOOLEAN','FACE')
    ids=source.data.attributes.get('wl_face_id')
    attached={o.get('wl_terrain_face_id') for o in bpy.context.scene.objects if o.get('wl_terrain_face_corners') and not o.get('wl_face_mapping') and not o.get('wl_exclude') and o.wavelength_terrain.surface_source==source}
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
    if not obj.get('wl_face_mapping') and (source.get('wl_role')!='BRUSH' or source.get('wl_entity_id')):
        raise ValueError('Displacement source must remain a world brush')
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
        # The Edit -> Object commit may have recentered the brush origin.
        # Capture its new local coordinates, while preserving the same world face.
        points=[source.data.vertices[i].co.copy() for i in source.data.polygons[index].vertices]
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
        seen.add(fid);parts=terrain.brushes(obj,validate_seams=False,unit=source.get('wl_unit_meters'))
        if len(parts)!=1:raise ValueError('A brush-face displacement must have exactly one patch')
        generated=parts[0][0];face=brush[ids.index(fid)]
        face.vmf=dict(face.vmf or {});face.vmf['dispinfo']=generated.vmf['dispinfo'];face.texture=generated.texture
    return brush


class WL_OT_displacement_from_face(bpy.types.Operator):
    bl_idname='wavelength.displacement_from_face';bl_label='Create Displacement from Face';bl_options={'REGISTER','UNDO'}
    bl_description='Create editable Source displacement grids on selected quad faces, preserving their backing brush'
    independent:BoolProperty(default=True,options={'HIDDEN','SKIP_SAVE'})
    native:BoolProperty(default=True,options={'HIDDEN','SKIP_SAVE'})
    @classmethod
    def poll(cls,context):return workspace.active(context) and context.mode=='EDIT_MESH' and context.object and context.object.get('wl_role')=='BRUSH' and profiles.is_source(context.scene.wavelength.engine)
    def execute(self,context):
        try:
            if self.native and self.independent:
                from . import source_displacement
                source_displacement.create_faces(context)
                return {'FINISHED'}
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
    def poll(cls,context):return workspace.active(context) and context.mode=='OBJECT' and context.object and context.object.get('wl_terrain_face_corners') and not context.object.get('wl_face_mapping')
    def execute(self,context):
        selected=[o for o in context.selected_objects if o.get('wl_terrain_face_corners') and not o.get('wl_face_mapping')];sources={o.wavelength_terrain.surface_source for o in selected if o.wavelength_terrain.surface_source}
        for source in sources:consume(source)
        for obj in selected:
            if not obj.get('wl_terrain_detached'):detach(obj)
        return {'FINISHED'}



def mapping_modifier(obj):
    source=obj.wavelength_terrain.surface_source
    if not source:return None
    for modifier in source.modifiers:
        tree=modifier.node_group if modifier.type=='NODES' else None
        if tree and tree.get('wl_generator')==MAPPING:
            if any(node.type=='OBJECT_INFO' and node.inputs['Object'].default_value==obj for node in tree.nodes):
                return modifier
    return None


def compose_mapping(source,patches):
    """Replace mapped faces with independently evaluated patch geometry."""
    tree=bpy.data.node_groups.new('Wavelength · Face Heightfields','GeometryNodeTree')
    tree['wl_generator']=MAPPING
    for direction in ('INPUT','OUTPUT'):
        tree.interface.new_socket(name='Geometry',in_out=direction,socket_type='NodeSocketGeometry')
    nodes=tree.nodes;links=tree.links
    inp=nodes.new('NodeGroupInput');out=nodes.new('NodeGroupOutput')
    attr=nodes.new('GeometryNodeInputNamedAttribute');attr.data_type='INT'
    attr.inputs['Name'].default_value='wl_face_id'
    join=nodes.new('GeometryNodeJoinGeometry')
    selection=None
    for patch in patches:
        compare=nodes.new('FunctionNodeCompare');compare.data_type='INT';compare.operation='EQUAL'
        links.new(attr.outputs['Attribute'],next(socket for socket in compare.inputs if socket.name=='A' and socket.type=='INT'))
        next(socket for socket in compare.inputs if socket.name=='B' and socket.type=='INT').default_value=patch['wl_terrain_face_id']
        if selection is None:selection=compare.outputs['Result']
        else:
            either=nodes.new('FunctionNodeBooleanMath');either.operation='OR'
            links.new(selection,either.inputs[0]);links.new(compare.outputs['Result'],either.inputs[1])
            selection=either.outputs[0]
        reference=nodes.new('GeometryNodeObjectInfo');reference.transform_space='RELATIVE'
        reference.label=patch.name
        reference.inputs['Object'].default_value=patch
        links.new(reference.outputs['Geometry'],join.inputs['Geometry'])
    delete=nodes.new('GeometryNodeDeleteGeometry');delete.domain='FACE'
    links.new(inp.outputs[0],delete.inputs['Geometry']);links.new(selection,delete.inputs['Selection'])
    links.new(delete.outputs[0],join.inputs['Geometry']);links.new(join.outputs[0],out.inputs[0])
    modifier=source.modifiers.new('Wavelength · Face Heightfields','NODES')
    modifier.node_group=tree
    source.modifiers.move(len(source.modifiers)-1,0)
    return modifier


def map_selected_faces(context,auto_sew=True):
    from . import terrain,terrain_sew,primitive_ui,procedural
    settings=context.scene.wavelength;unit=profiles.unit_meters(settings)
    sources=list(context.objects_in_mode)
    selections=[]
    for source in sources:
        if source.type!='MESH':continue
        bm=bmesh.from_edit_mesh(source.data);bm.faces.index_update()
        selected=[f for f in bm.faces if f.select and not f.hide]
        if not selected:continue
        if source.data.users!=1 or source.library or source.data.library:
            raise ValueError(f'{source.name}: use a local, single-user mesh')
        if source.get('wl_terrain') or source.get('wl_source_displacement'):
            raise ValueError(f'{source.name}: select the original mesh or brush')
        root=primitive_ui.root_for(source)
        if (root and procedural.state(root)=='PROCEDURAL') or any(
            m.type=='NODES' and m.node_group and
            str(m.node_group.get('wl_generator','')).startswith('wavelength.geometry_nodes.')
            for m in source.modifiers
        ):
            raise ValueError(f'{source.name}: finalize the primitive to expose stable faces before mapping heightfields')
        if abs(source.matrix_world.determinant())<1e-12:
            raise ValueError(f'{source.name}: apply nonzero object scale first')
        for face in selected:
            points=[v.co for v in face.verts];normal=face.normal.normalized()
            if len(points)!=4 or any(abs((p-points[0]).dot(normal))>1e-6 for p in points) or any(
                (points[(i+1)%4]-points[i]).cross(points[(i+2)%4]-points[(i+1)%4]).dot(normal)<=1e-10
                for i in range(4)):
                raise ValueError(f'{source.name}, face {face.index}: select planar convex quads')
        selections.append((source,[f.index for f in selected]))
    if not selections:raise ValueError('Select at least one quad in Face Select mode')
    active=context.object
    bpy.ops.object.mode_set(mode='OBJECT')
    created=[];modifiers=[];new_attributes=[]
    try:
        for source,indices in selections:
            ids=source.data.attributes.get('wl_face_id')
            if ids is None:
                ids=source.data.attributes.new('wl_face_id','INT','FACE')
                new_attributes.append(source)
                for index,item in enumerate(ids.data):item.value=index+1
            if ids.data_type!='INT' or ids.domain!='FACE':
                raise ValueError(f'{source.name}: wl_face_id must be an integer face attribute')
            existing={o.get('wl_terrain_face_id') for o in source.children
                      if o.get('wl_terrain_face_corners') and
                      (not o.get('wl_face_mapping') or mapping_modifier(o))}
            from . import source_displacement
            existing.update(source_displacement.info(o)['face_id'] for o in source_displacement.surfaces(source))
            patches=[]
            for index in indices:
                fid=ids.data[index].value
                if fid<=0 or sum(d.value==fid for d in ids.data)!=1:
                    raise ValueError(f'{source.name}: repair face IDs before mapping terrain')
                if fid in existing:raise ValueError(f'{source.name}: a selected face already has a displacement')
                face=source.data.polygons[index]
                points=[source.data.vertices[i].co.copy() for i in face.vertices]
                normal=face.normal.normalized();u=(points[1]-points[0]).normalized();v=normal.cross(u)
                frame=Matrix((u,v,normal)).transposed().to_4x4();frame.translation=sum(points,Vector())/4
                local=[frame.inverted()@p for p in points]
                patch=terrain.create(context,paintable_surface=True)
                created.append(patch);patches.append(patch)
                patch.name=f'{source.name} · Heightfield {fid}'
                patch.parent=source;patch.matrix_parent_inverse=Matrix.Identity(4);patch.matrix_basis=frame
                patch['wl_face_mapping']=True
                patch['wl_terrain_face_id']=fid
                patch['wl_terrain_face_corners']=json.dumps([list(p) for p in local])
                patch['wl_terrain_source_corners']=json.dumps([list(p) for p in points])
                patch['wl_terrain_face_matrix']=json.dumps([list(row) for row in frame])
                controls=patch.wavelength_terrain;controls.surface_source=source
                controls.width=(max(p.x for p in local)-min(p.x for p in local))/unit
                controls.length=(max(p.y for p in local)-min(p.y for p in local))/unit
                controls.tiles_x=controls.tiles_y=1
                if face.material_index<len(source.data.materials):
                    material=source.data.materials[face.material_index]
                    if material:patch.data.materials.append(material)
                terrain.update(patch);warp(patch)
            modifiers.append((source,compose_mapping(source,patches)))
        context.view_layer.update()
        seams=terrain_sew.sew(created,allow_unmatched=True) if auto_sew and len(created)>1 else 0
        for patch in created:
            patch.hide_render=True
            patch.hide_set(True)
        bpy.ops.object.select_all(action='DESELECT')
        for source,_ in selections:source.select_set(True)
        context.view_layer.objects.active=active
        context.view_layer.update()
        return created,seams
    except Exception:
        for source,modifier in modifiers:
            group=modifier.node_group
            source.modifiers.remove(modifier)
            if not group.users:bpy.data.node_groups.remove(group)
        for patch in created:
            mesh=patch.data
            groups=[m.node_group for m in patch.modifiers if m.type=='NODES' and m.node_group and m.node_group.get('wl_generator')==WARP]
            bpy.data.objects.remove(patch,do_unlink=True)
            if not mesh.users:bpy.data.meshes.remove(mesh)
            for group in groups:
                if not group.users:bpy.data.node_groups.remove(group)
        for source in new_attributes:source.data.attributes.remove(source.data.attributes['wl_face_id'])
        bpy.ops.object.select_all(action='DESELECT')
        for source in sources:source.select_set(True)
        context.view_layer.objects.active=active
        bpy.ops.object.mode_set(mode='EDIT')
        raise



def export_mesh(obj,depsgraph):
    """Mesh exports honor the mapping modifier's render switch."""
    switched=[]
    try:
        for modifier in obj.modifiers:
            tree=modifier.node_group if modifier.type=='NODES' else None
            if tree and tree.get('wl_generator')==MAPPING and modifier.show_viewport!=modifier.show_render:
                switched.append((modifier,modifier.show_viewport))
                modifier.show_viewport=modifier.show_render
        if switched:depsgraph.update()
        return bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph),preserve_all_data_layers=True,depsgraph=depsgraph)
    finally:
        for modifier,value in switched:
            modifier.show_viewport=value
        if switched:depsgraph.update()



class WL_OT_copy_heightfield_inputs(bpy.types.Operator):
    bl_idname='wavelength.copy_heightfield_inputs'
    bl_label='Copy Settings to Selected Meshes'
    bl_description='Copy this patch’s height and noise settings to all mapped faces on selected meshes'
    bl_options={'REGISTER','UNDO'}
    patch_name:StringProperty(options={'HIDDEN'})

    def execute(self,context):
        patch=bpy.data.objects.get(self.patch_name)
        if not patch or not patch.get('wl_face_mapping') or not mapping_modifier(patch):
            self.report({'ERROR'},'The source heightfield is unavailable')
            return {'CANCELLED'}
        targets=[child for source in context.selected_objects for child in source.children
                 if child!=patch and child.get('wl_face_mapping') and mapping_modifier(child)]
        if not targets:
            self.report({'ERROR'},'Select meshes with mapped heightfields')
            return {'CANCELLED'}
        inputs=patch.wavelength_terrain
        for target in targets:
            settings=target.wavelength_terrain
            ratio=patch['wl_unit_meters']/target['wl_unit_meters']
            for name in ('elevation','amplitude','heightmap_scale'):
                setattr(settings,name,getattr(inputs,name)*ratio)
            settings.frequency=inputs.frequency/ratio
            for name in ('seed','noise_detail','noise_roughness','heightmap','heightmap_midlevel'):
                setattr(settings,name,getattr(inputs,name))
        return {'FINISHED'}


class WL_PT_face_heightfields(bpy.types.Panel):
    bl_label='Wavelength Face Heightfields'
    bl_space_type='PROPERTIES'
    bl_region_type='WINDOW'
    bl_context='modifier'

    @classmethod
    def poll(cls,context):
        obj=context.object
        return bool(obj and any(child.get('wl_face_mapping') and mapping_modifier(child) for child in obj.children))

    def draw(self,context):
        host=context.object
        layout=self.layout
        layout.prop(host,'wavelength_heightfield_scope',text='Edit')
        scope=host.wavelength_heightfield_scope
        if scope=='GROUP':
            layout.operator_context='INVOKE_DEFAULT'
            layout.operator('wavelength.edit_heightfield_group')
            return
        for patch in mapped_patches(host):
            if str(patch['wl_terrain_face_id'])==scope:
                draw_inputs(layout,patch.wavelength_terrain,context)
                layout.operator('wavelength.copy_heightfield_inputs').patch_name=patch.name
                break


HEIGHTFIELD_INPUTS=('resolution','elevation','amplitude','frequency','seed',
                    'noise_detail','noise_roughness','heightmap','heightmap_scale',
                    'heightmap_midlevel','power')
_SCOPE_ITEMS={}


def mapped_patches(host):
    return [patch for patch in host.children
            if patch.get('wl_face_mapping') and mapping_modifier(patch)]


def heightfield_scopes(self,context):
    items=[('GROUP','Entire Group','Selected hosts and sewn neighbors',0)]
    items.extend((str(p['wl_terrain_face_id']),p.name,'Edit this mapped face',p['wl_terrain_face_id'])
                 for p in mapped_patches(self))
    # Dynamic RNA enum strings must outlive the callback.
    return [_SCOPE_ITEMS.setdefault(item,item) for item in items]


def draw_inputs(layout,settings,context):
    for name in HEIGHTFIELD_INPUTS[:7]:
        layout.prop(settings,name)
    layout.template_ID(settings,'heightmap',open='image.open')
    if settings.heightmap:
        layout.prop(settings,'heightmap_scale')
        layout.prop(settings,'heightmap_midlevel')
    if profiles.is_source(context.scene.wavelength.engine):
        layout.prop(settings,'power')


def heightfield_group(context):
    from .terrain_sew import network
    hosts=dict.fromkeys([context.object,*context.selected_objects])
    return list(dict.fromkeys(member for host in hosts if host
                              for patch in mapped_patches(host) for member in network(patch)
                              if member.get('wl_face_mapping') and mapping_modifier(member)))


def apply_group_inputs(targets,changes,unit):
    for patch in targets:
        ratio=unit/patch['wl_unit_meters']
        for name,value in changes.items():
            if name in {'elevation','amplitude','heightmap_scale'}:
                value*=ratio
            elif name=='frequency':
                value/=ratio
            setattr(patch.wavelength_terrain,name,value)


class WL_OT_edit_heightfield_group(bpy.types.Operator):
    bl_idname='wavelength.edit_heightfield_group'
    bl_label='Edit Heightfield Group'
    bl_options={'UNDO','INTERNAL'}

    @classmethod
    def poll(cls,context):
        return context.mode=='OBJECT' and WL_PT_face_heightfields.poll(context)

    def invoke(self,context,event):
        try:
            self.targets=heightfield_group(context)
        except ValueError as exc:
            self.report({'ERROR'},str(exc))
            return {'CANCELLED'}
        patch=mapped_patches(context.object)[0]
        self.unit=patch['wl_unit_meters']
        self.initial={name:getattr(patch.wavelength_terrain,name) for name in HEIGHTFIELD_INPUTS}
        for name,value in self.initial.items():
            setattr(context.scene.wavelength_heightfield_group_inputs,name,value)
        return context.window_manager.invoke_props_dialog(self)

    def draw(self,context):
        self.layout.label(text=f'{len(self.targets)} mapped faces · only changed values apply')
        draw_inputs(self.layout,context.scene.wavelength_heightfield_group_inputs,context)

    def execute(self,context):
        if not hasattr(self,'targets'):
            return {'CANCELLED'}
        inputs=context.scene.wavelength_heightfield_group_inputs
        changes={name:getattr(inputs,name) for name,value in self.initial.items()
                 if getattr(inputs,name)!=value}
        apply_group_inputs(self.targets,changes,self.unit)
        return {'FINISHED'}


class WL_PT_mapped_terrain_paint(bpy.types.Panel):
    bl_label='Wavelength Terrain Paint'
    bl_space_type='PROPERTIES'
    bl_region_type='WINDOW'
    bl_context='modifier'

    @classmethod
    def poll(cls,context):
        return workspace.active(context) and context.mode=='OBJECT' and WL_PT_face_heightfields.poll(context)

    def draw(self,context):
        from .terrain_paint import PAINT_TYPES
        layout=self.layout
        settings=context.scene.wavelength_mapped_paint
        for name in ('paint_radius','paint_strength','paint_opacity'):
            layout.prop(settings,name)
        if profiles.is_source(context.scene.wavelength.engine):
            layout.prop(settings,'blend_base')
            layout.prop(settings,'paint_material',text='Second Material')
            layout.operator('wavelength.terrain_blend',text='Create Source Blend for Selected and Sewn Patches').shared=True
        else:
            layout.prop(settings,'paint_material',text='Second Material')
        row=layout.row(align=True)
        row.operator_context='INVOKE_REGION_WIN'
        for mode,label,icon in PAINT_TYPES:
            op=row.operator('wavelength.terrain_paint',text=label,icon=icon)
            op.mode=mode
            op.shared=True


class WL_OT_map_heightfields(bpy.types.Operator):
    bl_idname='wavelength.map_heightfields'
    bl_label='Map Heightfields to Selected Faces'
    bl_description='Add live terrain to selected quads across meshes and sew matching full edges'
    bl_options={'REGISTER','UNDO'}
    auto_sew:BoolProperty(name='Sew Matching Edges',default=True)

    @classmethod
    def poll(cls,context):
        from .terrain import supports_terrain
        return workspace.active(context) and context.mode=='EDIT_MESH' and supports_terrain(context.scene.wavelength.engine)

    def execute(self,context):
        try:
            patches,seams=map_selected_faces(context,self.auto_sew)
        except (ValueError,RuntimeError) as exc:
            self.report({'ERROR'},str(exc))
            return {'CANCELLED'}
        self.report({'INFO'},f'Mapped {len(patches)} heightfields and sewed {seams} edges')
        return {'FINISHED'}


def menu(self,context):
    if WL_OT_map_heightfields.poll(context):self.layout.operator(WL_OT_map_heightfields.bl_idname,icon='MESH_GRID')
    if WL_OT_displacement_from_face.poll(context):self.layout.operator(WL_OT_displacement_from_face.bl_idname,icon='MESH_GRID')


def object_menu(self,context):
    if WL_OT_displacement_detach.poll(context):self.layout.operator('wavelength.displacement_detach')


def register():
    bpy.app.handlers.depsgraph_update_post.append(sync_masks)


def unregister():
    bpy.app.handlers.depsgraph_update_post.remove(sync_masks)
    _SIGNATURES.clear()
