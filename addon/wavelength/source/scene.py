"""Blender scene adapter. Geometry and MAP data remain independent of bpy."""
from dataclasses import asdict
import json
import math
import uuid
import bpy
from mathutils import Matrix, Vector
from . import formats, profiles
from .entity import models as entity_models
from .geometry import BrushError,validate,dot,sub,length,TOLERANCE


ENGINE_UNIT_METERS = 0.0254  # Approximate authoring convention, not exact engine physics.

def uid(): return str(uuid.uuid4())


def world_point(obj,co,unit=1.0):
    """Evaluate mesh coordinates in Python double precision, not mathutils float32."""
    matrix=obj.matrix_world
    return tuple((sum(float(matrix[i][j])*float(co[j]) for j in range(3))+float(matrix[i][3]))/unit for i in range(3))

def origin_to_geometry(obj):
    """Move a mesh object's origin to its vertex median without moving geometry in world space."""
    if obj is None or obj.type != 'MESH' or not obj.data.vertices:
        return
    if obj.parent and (obj.parent.get('wl_primitive') or obj.parent.get('wl_assembly')):
        return
    if obj.mode == 'EDIT':
        import bmesh
        bm = bmesh.from_edit_mesh(obj.data)
        vertices = bm.verts
    else:
        vertices = obj.data.vertices
    if not vertices:
        return
    center = Vector((0.0, 0.0, 0.0))

    for vertex in vertices:
        center += vertex.co
    center /= len(vertices)
    if center.length_squared <= 1e-20:
        return
    children = [(child, child.matrix_world.copy()) for child in obj.children]
    for vertex in vertices:
        vertex.co -= center
    obj.matrix_world = obj.matrix_world @ Matrix.Translation(center)
    for child, matrix in children:
        child.matrix_world = matrix
        if child.get('wl_terrain_source_corners') and not child.get('wl_terrain_detached'):
            child['wl_terrain_source_corners']=json.dumps([list(Vector(p)-center) for p in json.loads(child['wl_terrain_source_corners'])])
            if child.get('wl_terrain_face_matrix'):
                frame=Matrix.Translation(-center)@Matrix(json.loads(child['wl_terrain_face_matrix']))
                child['wl_terrain_face_matrix']=json.dumps([list(row) for row in frame])
    if obj.mode == 'EDIT':
        bmesh.update_edit_mesh(obj.data, loop_triangles=False, destructive=False)
    else:
        obj.data.update()


def mark_brush(obj):
    if not obj.get('wl_role'):obj['wl_unit_meters']=profiles.unit_meters(bpy.context.scene.wavelength) if hasattr(bpy.context.scene,'wavelength') else ENGINE_UNIT_METERS
    obj['wl_role']='BRUSH'
    if not obj.get('wl_id'):obj['wl_id']=uid()
    attribute=obj.data.attributes.get('wl_face_id') or obj.data.attributes.new('wl_face_id','INT','FACE')
    existing={x.value for x in attribute.data if x.value>0};next_id=max(existing,default=0)+1
    seen=set()
    for datum in attribute.data:
        if datum.value<=0 or datum.value in seen:datum.value=next_id;next_id+=1
        seen.add(datum.value)
    if not obj.data.get('wl_faces'):obj.data['wl_faces']='{}'


def brush_from_object(obj,engine,require_texture=False):
    if obj.get('wl_csg'):raise BrushError('CSG_NOT_FINALIZED','Finalize Geometry before exporting live CSG')
    if obj.mode!='OBJECT':raise BrushError('EDIT_MODE',f'{obj.name}: leave Edit Mode before exporting')
    modifiers=[m for m in obj.modifiers if not (m.type=='NODES' and m.node_group and m.node_group.get('wl_generator')=='wavelength.displacement.face_mask')]
    if modifiers:
        if all(m.type=='NODES' and m.node_group and str(m.node_group.get('wl_generator','')).startswith('wavelength.geometry_nodes.') for m in modifiers):
            depsgraph=bpy.context.evaluated_depsgraph_get()
            mesh=bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph),preserve_all_data_layers=True,depsgraph=depsgraph)
            temporary=bpy.data.objects.new(obj.name+' evaluated export',mesh)
            try:
                temporary.matrix_world=obj.matrix_world.copy()
                temporary['wl_unit_meters']=obj.get('wl_unit_meters',1.0)
                mesh['wl_faces']=obj.data.get('wl_faces','{}')
                mesh.materials.clear()
                for material in obj.data.materials:mesh.materials.append(material)
                return brush_from_object(temporary,engine,require_texture)
            finally:
                bpy.data.objects.remove(temporary,do_unlink=True);bpy.data.meshes.remove(mesh)
        raise BrushError('MODIFIERS_PRESENT',f'{obj.name}: apply modifiers to a copy first')
    if obj.library or obj.data.library or obj.override_library:raise BrushError('LINKED_DATA',obj.name)
    if abs(obj.matrix_world.determinant())<1e-12:raise BrushError('SINGULAR_TRANSFORM',obj.name)
    verts=[world_point(obj,v.co,obj.get('wl_unit_meters',1.0)) for v in obj.data.vertices]
    polygons=[list(p.vertices) for p in obj.data.polygons]
    attr=obj.data.attributes.get('wl_face_id')
    if attr is None:raise BrushError('FACE_ID_MISSING',obj.name)
    ids=[v.value for v in attr.data]
    if len(ids)!=len(set(ids)) or any(i<=0 for i in ids):raise BrushError('FACE_ID_DUPLICATE',f'{obj.name}: use Repair Face IDs after topology edits')
    records=json.loads(obj.data.get('wl_faces','{}'));faces=[]
    imported=obj.data.get('wl_import_geometry')
    signature=[[list(v.co) for v in obj.data.vertices],polygons,ids]
    unchanged=(imported and json.loads(imported)==signature and
               obj.get('wl_import_matrix')==json.dumps([list(row) for row in obj.matrix_world]) and
               all(str(fid) in records for fid in ids))
    if unchanged:
        planes=[((0,1,2),*formats.Face(**records[str(fid)]).plane()) for fid in ids]
    else:
        try:planes=validate(verts,polygons)
        except BrushError as exc:
            exc.object_name=obj.name
            raise
    for index,((triplet,n,d),fid) in enumerate(zip(planes,ids,strict=True)):
        record=records.get(str(fid))
        if record:
            face=formats.Face(**record)
            old_n,old_d=face.plane()
            if length(sub(n,old_n))>TOLERANCE or abs(d-old_d)>TOLERANCE:
                face.points=[list(verts[i]) for i in triplet[::-1]]
        else:
            face=formats.Face([list(verts[i]) for i in triplet[::-1]],'', [0,0,0,1,1])
        material=None
        slot=obj.data.polygons[index].material_index
        if slot<len(obj.data.materials):material=obj.data.materials[slot]
        if material and material.get('wl_texture'):face.texture=material['wl_texture']
        if require_texture and not str(face.texture or '').strip():
            raise BrushError('FACE_TEXTURE_MISSING',f'{obj.name}: face {index + 1} has no engine texture assigned')
        if profiles.uses_valve_axes(engine) and face.axes is None:
            face.axes=formats.quake_axes(n,face.projection)
        if engine=='quake' and face.axes is not None:
            raise BrushError('PROJECTION_MISMATCH','Valve 220 axes require GoldSrc mode; conversion to classic can be lossy')
        faces.append((fid,face))
    return [face for _,face in sorted(faces)]


def export_map(scene):
    if profiles.is_mesh_export(scene.wavelength.engine):raise BrushError('PROFILE_EXPORT_FORMAT','Use Export Meshes & Textures for this profile')
    if any(o.get('wl_csg') and not o.get('wl_exclude') for o in scene.objects):
        raise BrushError('CSG_NOT_FINALIZED','Finalize Geometry before exporting live CSG')
    if bpy.context.scene==scene:bpy.context.view_layer.update()
    engine=scene.wavelength.engine
    if not profiles.is_source(engine) and any(o.get('wl_source_displacement') and not o.get('wl_exclude') for o in scene.objects):
        raise BrushError('PROFILE_EXPORT_FORMAT','Native displacements require a Source 1 profile and VMF export')
    world_pairs=json.loads(scene.get('wl_world_pairs','[["classname","worldspawn"]]'))
    if profiles.is_goldsrc(engine):
        world_pairs=[(k,v) for k,v in world_pairs if k!='mapversion']
        world_pairs.append(('mapversion','220'))
    world=formats.Entity(world_pairs,[]); grouped={};point=[];seen=set()
    attachments={};validated_seams=set()
    from . import terrain_face,terrain_sew
    for obj in scene.objects:
        if obj.get('wl_terrain_seams') and not obj.get('wl_exclude') and obj not in validated_seams:
            members=terrain_sew.network(obj);terrain_sew.validate_export(obj);validated_seams.update(members)
        if obj.get('wl_exclude') or not obj.get('wl_terrain_face_corners'):continue
        source,_=terrain_face.validate_attachment(obj)
        if source is None:continue
        if source.get('wl_exclude'):raise ValueError('Displacement source brush is excluded from export')
        attachments.setdefault(source,[]).append(obj)
    for obj in sorted(scene.objects,key=lambda o:(o.get('wl_id',''),o.name)):
        if obj.get('wl_exclude') or obj.get('wl_custom_model_owner'):continue
        if obj.get('wl_custom_model') and not profiles.is_source(engine):raise ValueError('Custom model compilation currently requires its owning Source profile')
        if obj.get('wl_terrain'):
            if not profiles.is_source(engine):raise ValueError('Terrain map export currently requires a Source profile')
            from . import terrain
            world.brushes.extend(terrain.brushes(obj,validate_seams=False));continue
        if obj.get('wl_displacement'):
            if not profiles.is_source(engine):raise ValueError('Drawing displacements require a Source profile')
            from .draw_displacement import brush
            world.brushes.append(brush(obj));continue
        role=obj.get('wl_role')
        if not role:continue
        if obj.get('wl_source_displacement'):continue  # Serialized on its backing face.
        identity=obj.get('wl_id')
        if not identity or identity in seen:raise BrushError('OBJECT_ID_DUPLICATE',f'{obj.name}: repair object IDs')
        seen.add(identity)
        if obj.instance_type!='NONE':raise BrushError('INSTANCE_UNSUPPORTED','Realize collection instances before exporting')
        if role=='BRUSH':
            # A displacement's own frame defines grid orientation. Reusing the
            # original brush side can transpose rows when mesh winding and the
            # convex exporter's outward plane orientation disagree. Source also
            # discards the backing brush's ordinary sides, so emit independent
            # displacement backings for legacy attachments as well.
            if obj in attachments:continue
            try:brush=brush_from_object(obj,engine,require_texture=True)
            except BrushError as exc:
                error=BrushError(exc.code,f'{obj.name}: {exc}');error.object_name=obj.name
                raise error from exc
            if any((f.vmf or {}).get('dispinfo') for f in brush):
                from . import source_displacement
                brush=source_displacement.apply(obj,brush)
            entity_id=obj.get('wl_entity_id')
            if entity_id:
                pairs=json.loads(obj.get('wl_entity_pairs','[]'))
                if profiles.is_source(engine):
                    from .entity import source_schema
                    pairs=source_schema.export_pairs(scene.wavelength,pairs,bpy.path.abspath)
                if not any(k=='classname' and v for k,v in pairs):
                    raise BrushError('ENTITY_CLASS_MISSING',f'{obj.name}: brush entity has no classname')
                entity=grouped.setdefault(entity_id,formats.Entity(pairs,[],vmf_hidden=bool(obj.get('wl_vmf_entity_hidden'))))
                if entity.pairs!=pairs:
                    raise BrushError('ENTITY_MISMATCH',f'{obj.name}: brush entity members have conflicting properties')
                entity.brushes.append(brush)
            else:world.brushes.append(brush)
        elif role=='ENTITY':
            pairs=json.loads(obj.get('wl_pairs','[]'))
            if profiles.is_source(engine):
                from .entity import source_schema
                pairs=source_schema.export_pairs(scene.wavelength,pairs,bpy.path.abspath)
                from . import source_pose
                pairs=source_pose.export_pairs(obj,pairs)
            if obj.get('wl_custom_model') and not profiles.is_source(engine):
                rotation=obj.matrix_world.to_euler('XYZ')
                angles=' '.join(formats.number(math.degrees(rotation[i])) for i in (1,2,0))
                pairs=[(k,v) for k,v in pairs if k!='angles'];pairs.append(('angles',angles))
            if dict(pairs).get('classname')=='light_environment':
                from . import sun
                pairs=sun.export_pairs(obj,pairs)
            if not any(k=='classname' for k,v in pairs):raise BrushError('ENTITY_CLASS_MISSING',obj.name)
            origin=' '.join(formats.number(x/obj.get('wl_unit_meters',1.0)) for x in obj.matrix_world.translation)
            original_origin=dict(pairs).get('origin')
            if original_origin:
                try:
                    original_world=Vector([float(x)*obj.get('wl_unit_meters',1.0) for x in original_origin.split()])
                    if len(original_world)==3 and original_world==obj.matrix_world.translation:
                        # Preserve exact native coordinates on an unchanged
                        # round trip instead of serializing float32 noise.
                        origin=original_origin
                except (ValueError,TypeError):
                    pass
            pairs=[(k,origin if k=='origin' else v) for k,v in pairs]
            if not any(k=='origin' for k,v in pairs):pairs.append(('origin',origin))
            point.append(formats.Entity(pairs,[],vmf_hidden=bool(obj.get('wl_vmf_entity_hidden'))))
    if not world.brushes:raise BrushError('EMPTY_MAP','No world brushes')
    document=formats.Map([world,*grouped.values(),*point])
    return document


def import_map(scene,document,defer_assets=None):
    """Synchronous adapter for scripts/background operation; UI uses the iterator."""
    iterator=import_map_iter(scene,document,defer_assets)
    while True:
        try:next(iterator)
        except StopIteration as done:return done.value


def import_map_iter(scene,document,defer_assets=None,prepared=None):
    """Validate all geometry before allocating scene objects; rollback on failure."""
    if defer_assets is None:defer_assets=not bpy.app.background
    unit=profiles.unit_meters(scene.wavelength)
    world=[e for e in document.entities if dict(e.pairs).get('classname')=='worldspawn']
    if len(world)!=1:raise BrushError('WORLDSPAWN','Exactly one worldspawn is required')
    if prepared is None:
        from .map_prepare import geometry
        prepared=list(geometry(document))
    collection=bpy.data.collections.new('wavelength Map');created=[];meshes=[]
    hidden=[]
    try:
        groups={};material_cache={}
        for entity,brush,verts,polygons in prepared:
            center=tuple(sum(v[i] for v in verts)/len(verts) for i in range(3))
            mesh=bpy.data.meshes.new('Brush');meshes.append(mesh);mesh.from_pydata([tuple((v[i]-center[i])*unit for i in range(3)) for v in verts],[],polygons);mesh.update()
            obj=bpy.data.objects.new('Brush',mesh);collection.objects.link(obj);created.append(obj);mark_brush(obj)
            obj.matrix_world=Matrix.Translation(tuple(x*unit for x in center))
            obj['wl_unit_meters']=unit
            if entity.vmf_hidden:obj['wl_vmf_entity_hidden']=True
            records={str(i+1):asdict(face) for i,face in enumerate(brush)};mesh['wl_faces']=json.dumps(records)
            for i,datum in enumerate(mesh.attributes['wl_face_id'].data):datum.value=i+1
            mesh['wl_import_geometry']=json.dumps([[list(v.co) for v in mesh.vertices],[list(p.vertices) for p in mesh.polygons],[d.value for d in mesh.attributes['wl_face_id'].data]])
            obj['wl_import_matrix']=json.dumps([list(row) for row in obj.matrix_world])
            # Recreate texture identity in Blender even if the WAD is absent.
            # The original projection and texture name remain in wl_faces.
            from . import textures
            materials={}
            for i,face in enumerate(brush):
                name=face.texture
                if not name:continue
                if name not in materials:
                    mat=material_cache.get(name)
                    if mat is None:
                        try:
                            mat=textures.material(scene.wavelength,name,defer=defer_assets)
                        except (OSError,ValueError,KeyError):
                            mat=bpy.data.materials.get('wl_missing_'+name)
                            if mat is None:
                                mat=bpy.data.materials.new('wl_missing_'+name)
                            mat['wl_texture']=name
                        material_cache[name]=mat
                    materials[name]=len(mesh.materials)
                    mesh.materials.append(mat)
                mesh.polygons[i].material_index=materials[name]
            # Imported VMT shaders read this UV layer. Preserve the VMF's axes,
            # texture offsets/scales and the original texture dimensions.
            from .editor import apply_uv
            apply_uv(obj,scene.wavelength.engine,faces=brush)
            if entity is not world[0]:
                obj['wl_entity_id']=groups.setdefault(id(entity),uid());obj['wl_entity_pairs']=json.dumps(entity.pairs)
            for index,face in enumerate(brush):
                if (face.vmf or {}).get('dispinfo'):
                    from . import source_displacement
                    surface=source_displacement.attach(obj,index,face)
                    created.append(surface);meshes.append(surface.data)
            if any((f.vmf or {}).get('dispinfo') for f in brush):source_displacement.mask(obj)
            if entity.vmf_hidden or any((f.vmf or {}).get('hidden') for f in brush):
                hidden.append(obj)
            yield ('BRUSH',obj)
        for entity in document.entities:
            if entity.brushes or entity is world[0]:continue
            values=dict(entity.pairs);obj=bpy.data.objects.new(values.get('classname','Entity'),None)
            obj.empty_display_type='ARROWS';obj.empty_display_size=16*unit
            obj.location=[float(x)*unit for x in values.get('origin','0 0 0').split()]
            obj['wl_unit_meters']=unit
            obj['wl_role']='ENTITY';obj['wl_id']=uid();obj['wl_pairs']=json.dumps(entity.pairs)
            if profiles.is_source(scene.wavelength.engine):
                from . import source_pose
                source_pose.apply(obj,entity.pairs,force=True)
            collection.objects.link(obj);created.append(obj)
            if entity.vmf_hidden:obj['wl_vmf_entity_hidden']=True
            obj['_wl_reference_fresh']=True
            if profiles.is_goldsrc(scene.wavelength.engine) or profiles.is_source(scene.wavelength.engine):
                if defer_assets:
                    from . import asset_loading
                    asset_loading.entity(scene,obj)
                else:entity_models.attach_reference(obj,entity.pairs)
            obj.pop('_wl_reference_fresh',None)
            if values.get('classname')=='light_environment':
                from . import sun
                sun.ensure(obj)
            if entity.vmf_hidden:
                hidden.append(obj)
            yield ('ENTITY',obj)
        yield ('COMMIT',None)
        scene.collection.children.link(collection)
        hidden_pointers={o.as_pointer() for o in hidden}
        for obj in collection.objects:
            if obj.as_pointer() in hidden_pointers or (obj.parent and obj.parent.as_pointer() in hidden_pointers):obj.hide_set(True)
        scene['wl_world_pairs']=json.dumps(world[0].pairs)
    except BaseException:
        for obj in list(collection.objects):bpy.data.objects.remove(obj,do_unlink=True)
        for mesh in meshes:
            if mesh.users==0:bpy.data.meshes.remove(mesh)
        bpy.data.collections.remove(collection)
        raise
    from . import native_source
    if profiles.is_source(scene.wavelength.engine) and native_source.enabled():native_source.configure_viewports()
    return collection


def validate_scene(scene):
    diagnostics=[]
    try:document=export_map(scene)
    except (BrushError,ValueError) as exc:
        diagnostics.append({'schema_version':1,'severity':'error','code':getattr(exc,'code','INVALID_DATA'),'message':str(exc),'engine':scene.wavelength.engine})
        return diagnostics
    names={};targets=[]
    for entity in document.entities:
        values=dict(entity.pairs)
        if values.get('targetname'):names[values['targetname']]=names.get(values['targetname'],0)+1
        if values.get('target'):targets.append(values['target'])
    for target in targets:
        if target not in names:diagnostics.append({'schema_version':1,'severity':'warning','code':'MISSING_TARGET','message':f'Target {target!r} does not exist'})
    return diagnostics
