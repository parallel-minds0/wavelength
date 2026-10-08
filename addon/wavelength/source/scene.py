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

def origin_to_geometry(obj):
    """Move a mesh object's origin to its vertex median without moving geometry in world space."""
    if obj is None or obj.type != 'MESH' or not obj.data.vertices:
        return
    center = Vector((0.0, 0.0, 0.0))
    for vertex in obj.data.vertices:
        center += vertex.co
    center /= len(obj.data.vertices)
    if center.length_squared <= 1e-20:
        return
    for vertex in obj.data.vertices:
        vertex.co -= center
    obj.matrix_world = obj.matrix_world @ Matrix.Translation(center)
    obj.data.update()


def mark_brush(obj):
    if not obj.get('wl_role'):obj['wl_unit_meters']=ENGINE_UNIT_METERS
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
    if obj.mode!='OBJECT':raise BrushError('EDIT_MODE',f'{obj.name}: leave Edit Mode before exporting')
    if obj.modifiers:raise BrushError('MODIFIERS_PRESENT',f'{obj.name}: apply modifiers to a copy first')
    if obj.library or obj.data.library or obj.override_library:raise BrushError('LINKED_DATA',obj.name)
    if abs(obj.matrix_world.determinant())<1e-12:raise BrushError('SINGULAR_TRANSFORM',obj.name)
    verts=[tuple(x/obj.get('wl_unit_meters',1.0) for x in (obj.matrix_world@v.co)) for v in obj.data.vertices]
    polygons=[list(p.vertices) for p in obj.data.polygons]
    planes=validate(verts,polygons)
    attr=obj.data.attributes.get('wl_face_id')
    if attr is None:raise BrushError('FACE_ID_MISSING',obj.name)
    ids=[v.value for v in attr.data]
    if len(ids)!=len(set(ids)) or any(i<=0 for i in ids):raise BrushError('FACE_ID_DUPLICATE',f'{obj.name}: use Repair Face IDs after topology edits')
    records=json.loads(obj.data.get('wl_faces','{}'));faces=[]
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
    engine=scene.wavelength.engine
    world_pairs=json.loads(scene.get('wl_world_pairs','[["classname","worldspawn"]]'))
    if profiles.is_goldsrc(engine):
        world_pairs=[(k,v) for k,v in world_pairs if k!='mapversion']
        world_pairs.append(('mapversion','220'))
    world=formats.Entity(world_pairs,[]); grouped={};point=[];seen=set()
    for obj in sorted(scene.objects,key=lambda o:(o.get('wl_id',''),o.name)):
        if obj.get('wl_exclude'):continue
        role=obj.get('wl_role')
        if not role:continue
        identity=obj.get('wl_id')
        if not identity or identity in seen:raise BrushError('OBJECT_ID_DUPLICATE',f'{obj.name}: repair object IDs')
        seen.add(identity)
        if obj.instance_type!='NONE':raise BrushError('INSTANCE_UNSUPPORTED','Realize collection instances before exporting')
        if role=='BRUSH':
            try:brush=brush_from_object(obj,engine,require_texture=True)
            except BrushError as exc:raise BrushError(exc.code,f'{obj.name}: {exc}') from exc
            entity_id=obj.get('wl_entity_id')
            if entity_id:
                pairs=json.loads(obj.get('wl_entity_pairs','[]'))
                if not any(k=='classname' and v for k,v in pairs):
                    raise BrushError('ENTITY_CLASS_MISSING',f'{obj.name}: brush entity has no classname')
                entity=grouped.setdefault(entity_id,formats.Entity(pairs,[]))
                if entity.pairs!=pairs:
                    raise BrushError('ENTITY_MISMATCH',f'{obj.name}: brush entity members have conflicting properties')
                entity.brushes.append(brush)
            else:world.brushes.append(brush)
        elif role=='ENTITY':
            pairs=json.loads(obj.get('wl_pairs','[]'))
            if not any(k=='classname' for k,v in pairs):raise BrushError('ENTITY_CLASS_MISSING',obj.name)
            origin=' '.join(formats.number(x/obj.get('wl_unit_meters',1.0)) for x in obj.matrix_world.translation)
            pairs=[(k,origin if k=='origin' else v) for k,v in pairs]
            if not any(k=='origin' for k,v in pairs):pairs.append(('origin',origin))
            point.append(formats.Entity(pairs,[]))
    if not world.brushes:raise BrushError('EMPTY_MAP','No world brushes')
    document=formats.Map([world,*grouped.values(),*point])
    return document


def import_map(scene,document):
    """Validate all geometry before allocating scene objects; rollback on failure."""
    world=[e for e in document.entities if dict(e.pairs).get('classname')=='worldspawn']
    if len(world)!=1:raise BrushError('WORLDSPAWN','Exactly one worldspawn is required')
    prepared=[]
    for entity in document.entities:
        for brush in entity.brushes:prepared.append((entity,brush,*formats.brush_mesh(brush)))
        if not entity.brushes:
            try:
                origin=[float(x) for x in dict(entity.pairs).get('origin','0 0 0').split()]
                if len(origin)!=3 or not all(math.isfinite(x) for x in origin):raise ValueError()
            except ValueError as exc:raise BrushError('INVALID_ORIGIN','Entity origin must be three finite numbers') from exc
    collection=bpy.data.collections.new('wavelength Map');created=[];meshes=[]
    scene.collection.children.link(collection)
    try:
        groups={}
        for entity,brush,verts,polygons in prepared:
            mesh=bpy.data.meshes.new('Brush');meshes.append(mesh);mesh.from_pydata([tuple(x*ENGINE_UNIT_METERS for x in v) for v in verts],[],polygons);mesh.update()
            obj=bpy.data.objects.new('Brush',mesh);collection.objects.link(obj);created.append(obj);mark_brush(obj)
            records={str(i+1):asdict(face) for i,face in enumerate(brush)};mesh['wl_faces']=json.dumps(records)
            for i,datum in enumerate(mesh.attributes['wl_face_id'].data):datum.value=i+1
            # Recreate texture identity in Blender even if the WAD is absent.
            # The original projection and texture name remain in wl_faces.
            from . import textures
            materials={}
            for i,face in enumerate(brush):
                name=face.texture
                if not name:continue
                if name not in materials:
                    try:
                        mat=textures.material(scene.wavelength,name)
                    except (OSError,ValueError,KeyError):
                        mat=bpy.data.materials.get('wl_missing_'+name)
                        if mat is None:
                            mat=bpy.data.materials.new('wl_missing_'+name)
                        mat['wl_texture']=name
                    materials[name]=len(mesh.materials)
                    mesh.materials.append(mat)
                mesh.polygons[i].material_index=materials[name]
            if entity is not world[0]:
                obj['wl_entity_id']=groups.setdefault(id(entity),uid());obj['wl_entity_pairs']=json.dumps(entity.pairs)
        for entity in document.entities:
            if entity.brushes or entity is world[0]:continue
            values=dict(entity.pairs);obj=bpy.data.objects.new(values.get('classname','Entity'),None)
            obj.empty_display_type='ARROWS';obj.empty_display_size=16*ENGINE_UNIT_METERS
            obj.location=[float(x)*ENGINE_UNIT_METERS for x in values.get('origin','0 0 0').split()]
            obj['wl_unit_meters']=ENGINE_UNIT_METERS
            obj['wl_role']='ENTITY';obj['wl_id']=uid();obj['wl_pairs']=json.dumps(entity.pairs)
            collection.objects.link(obj);created.append(obj)
            if profiles.is_goldsrc(scene.wavelength.engine):entity_models.attach_reference(obj,entity.pairs)
        scene['wl_world_pairs']=json.dumps(world[0].pairs)
    except Exception:
        for obj in created:bpy.data.objects.remove(obj,do_unlink=True)
        for mesh in meshes:
            if mesh.users==0:bpy.data.meshes.remove(mesh)
        bpy.data.collections.remove(collection)
        raise
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
