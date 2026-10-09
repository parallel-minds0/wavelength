"""Reusable editing operations for convex brushes and engine texture previews."""
from dataclasses import asdict
from itertools import combinations
import json
import math
import time
import bpy
from bpy.app.handlers import persistent
from . import scene,formats,profiles
from .geometry import cross,dot,sub,length,validate,TOLERANCE,BrushError


def apply_uv(obj,engine):
    faces=scene.brush_from_object(obj,engine)
    attr=obj.data.attributes['wl_face_id'];by_id={i:f for i,f in zip(sorted(d.value for d in attr.data),faces)}
    layer=obj.data.uv_layers.get('wavelength') or obj.data.uv_layers.new(name='wavelength')
    for polygon in obj.data.polygons:
        face=by_id[attr.data[polygon.index].value]
        axes=face.axes or formats.quake_axes(face.plane()[0],face.projection)
        slot=polygon.material_index;material=obj.data.materials[slot] if slot<len(obj.data.materials) else None
        width=material.get('wl_width',64) if material else 64;height=material.get('wl_height',64) if material else 64
        for loop in polygon.loop_indices:
            p=(obj.matrix_world@obj.data.vertices[obj.data.loops[loop].vertex_index].co)/obj.get('wl_unit_meters',1.0)
            u=dot(axes[0][:3],p)/face.projection[3]+axes[0][3]
            v=dot(axes[1][:3],p)/face.projection[4]+axes[1][3]
            layer.data[loop].uv=(u/width,1-v/height)


def clipped_mesh(obj,normal,distance,engine):
    source=scene.brush_from_object(obj,engine);planes=[face.plane() for face in source]+[(normal,distance)]
    vertices=[]
    for (a,da),(b,db),(c,dc) in combinations(planes,3):
        bc,ca,ab=cross(b,c),cross(c,a),cross(a,b);den=dot(a,bc)
        if abs(den)<1e-10:continue
        p=tuple((da*bc[i]+db*ca[i]+dc*ab[i])/den for i in range(3))
        if all(dot(n,p)-d<=TOLERANCE for n,d in planes) and not any(length(sub(p,v))<TOLERANCE for v in vertices):vertices.append(p)
    polygons=[];records=[]
    for index,(n,d) in enumerate(planes):
        ids=[i for i,p in enumerate(vertices) if abs(dot(n,p)-d)<=TOLERANCE]
        if len(ids)<3:continue
        center=tuple(sum(vertices[i][j] for i in ids)/len(ids) for j in range(3))
        u=cross((1,0,0) if abs(n[0])<.9 else (0,1,0),n);v=cross(n,u)
        ids.sort(key=lambda i:math.atan2(dot(sub(vertices[i],center),v),dot(sub(vertices[i],center),u)))
        polygons.append(ids)
        face=source[index] if index<len(source) else formats.Face([vertices[i] for i in ids[:3][::-1]],'', [0,0,0,1,1])
        if profiles.uses_valve_axes(engine) and face.axes is None:face.axes=formats.quake_axes(n,face.projection)
        records.append(asdict(face))
    validate(vertices,polygons)
    return vertices,polygons,records


def clip(obj,normal,distance,engine):
    vertices,polygons,records=clipped_mesh(obj,normal,distance,engine)
    materials=list(obj.data.materials)
    mesh=bpy.data.meshes.new(obj.name+' clipped');mesh.from_pydata(vertices,[],polygons);mesh.update()
    # New geometry is in world coordinates; retain original object transform.
    inverse=obj.matrix_world.inverted()
    from mathutils import Vector
    for v in mesh.vertices:v.co=inverse@(v.co*obj.get('wl_unit_meters',1.0))
    obj.data=mesh;scene.mark_brush(obj);mesh['wl_faces']=json.dumps({str(i+1):record for i,record in enumerate(records)})
    for i,datum in enumerate(mesh.attributes['wl_face_id'].data):datum.value=i+1
    for index,record in enumerate(records):
        material=next((m for m in materials if m and m.get('wl_texture','').casefold()==record['texture'].casefold()),None)
        if material is not None:
            slot=next((i for i,m in enumerate(mesh.materials) if m==material),None)
            if slot is None:slot=len(mesh.materials);mesh.materials.append(material)
            mesh.polygons[index].material_index=slot
    apply_uv(obj,engine)


def capture_uv(obj,engine,indices=None):
    """Fit affine face UVs to engine projections, rejecting unrepresentable edits."""
    layer=obj.data.uv_layers.get('wavelength')
    if layer is None:raise ValueError('Apply a texture or load previews before editing UVs')
    faces=scene.brush_from_object(obj,engine)
    by_id=dict(zip(sorted(d.value for d in obj.data.attributes['wl_face_id'].data),faces))
    records=json.loads(obj.data.get('wl_faces','{}'))
    for polygon in obj.data.polygons:
        if indices is not None and polygon.index not in indices:continue
        fid=obj.data.attributes['wl_face_id'].data[polygon.index].value;face=by_id[fid]
        mat=obj.data.materials[polygon.material_index] if polygon.material_index<len(obj.data.materials) else None
        width=mat.get('wl_width',64) if mat else 64;height=mat.get('wl_height',64) if mat else 64
        normal=face.plane()[0];base=formats.quake_axes(normal,[0,0,0,1,1])
        sv=next(i for i in range(3) if base[0][i]);tv=next(i for i in range(3) if base[1][i])
        rows=[];us=[];vs=[]
        for loop in polygon.loop_indices:
            point=(obj.matrix_world@obj.data.vertices[obj.data.loops[loop].vertex_index].co)/obj.get('wl_unit_meters',1.)
            rows.append((point[sv],point[tv],1.))
            uv=layer.data[loop].uv;us.append(uv.x*width);vs.append((1-uv.y)*height)
        chosen=None
        for triple in combinations(range(len(rows)),3):
            a,b,c=[rows[i] for i in triple];det=dot(a,cross(b,c))
            if abs(det)>1e-9:chosen=(triple,a,b,c,det);break
        if chosen is None:raise ValueError('Cannot derive projection for degenerate face')
        triple,a,b,c,det=chosen
        def fit(values):
            terms=(cross(b,c),cross(c,a),cross(a,b))
            result=tuple(sum(values[triple[j]]*terms[j][i] for j in range(3))/det for i in range(3))
            if any(abs(dot(row,result)-value)>0.002 for row,value in zip(rows,values)):
                raise ValueError('Non-affine UVs cannot be represented by a brush texture projection')
            return result
        u,v=fit(us),fit(vs)
        if math.hypot(*u[:2])<1e-9 or math.hypot(*v[:2])<1e-9:raise ValueError('Collapsed UV mapping')
        if profiles.uses_valve_axes(engine):
            axes=[]
            for fitrow in (u,v):
                axis=[0.,0.,0.,fitrow[2]];axis[sv]=fitrow[0];axis[tv]=fitrow[1];axes.append(axis)
            face.axes=axes;face.projection=[0,0,0,1,1]
        else:
            angle=math.atan2(u[1]/base[0][sv],u[0]/base[0][sv]);scale_u=1/math.hypot(*u[:2])
            direction=(-math.sin(angle)*base[1][tv],math.cos(angle)*base[1][tv])
            factor=v[0]*direction[0]+v[1]*direction[1]
            if abs(factor)<1e-9 or math.hypot(v[0]-factor*direction[0],v[1]-factor*direction[1])>1e-5:
                raise ValueError('Classic Quake cannot represent sheared UVs; use rotation and axis scaling')
            face.axes=None;face.projection=[u[2],v[2],math.degrees(angle),scale_u,1/factor]
        records[str(fid)]=asdict(face)
    # All faces validated before committing any projection changes.
    obj.data['wl_faces']=json.dumps(records)


_live_reprojecting=False
_live_state={}
_live_modes={}
_edit_sessions=set()
_LIVE_POLL_SECONDS=0.10
_last_face_ui=None

def note_edit_session(obj):
    """Record that a brush has entered an edit transaction.

    Gizmos call this explicitly so a fast Edit -> Object transition cannot be
    missed between timer ticks.
    """
    if obj is not None:
        try:
            name = obj.name_full
            _live_modes[name] = 'EDIT'
            _edit_sessions.add(name)
        except (ReferenceError, AttributeError):
            pass



def _finalize_edit_session(obj, settings=None):
    """Finalize one brush edit without selection/context-dependent operators."""
    name = obj.name_full
    scene.origin_to_geometry(obj)
    _live_state.pop(name, None)
    _live_modes[name] = 'OBJECT'
    _edit_sessions.discard(name)
    if settings is not None and getattr(settings, 'live_texture_reproject', False):
        global _live_reprojecting
        if not _live_reprojecting:
            _live_reprojecting = True
            try:
                apply_uv(obj, settings.engine)
                obj.data.update()
            except (ValueError, RuntimeError, KeyError, BrushError):
                pass
            finally:
                _live_reprojecting = False


@persistent
def _edit_commit_handler(scene_data, depsgraph=None):
    """Commit registered brush edit sessions on the actual mode transition.

    depsgraph_update_post runs as Blender applies the Edit -> Object transition, so
    unlike a polling timer it cannot initialize after the edge has already passed.
    """
    from .workspace import active
    if not active(bpy.context, 'textures') or not _edit_sessions:
        return
    settings = getattr(scene_data, 'wavelength', None)
    for name in tuple(_edit_sessions):
        obj = bpy.data.objects.get(name)
        if obj is None:
            _edit_sessions.discard(name)
            _live_modes.pop(name, None)
            _live_state.pop(name, None)
            continue
        if obj.type == 'MESH' and obj.get('wl_role') == 'BRUSH' and obj.mode == 'OBJECT':
            try:
                _finalize_edit_session(obj, settings)
            except (ReferenceError, RuntimeError, AttributeError):
                pass


def _brush_state(obj):
    """Track projection inputs, excluding generated UVs to avoid feedback loops."""
    return (
        tuple(value for row in obj.matrix_world for value in row),
        tuple(tuple(vertex.co) for vertex in obj.data.vertices),
        tuple((tuple(poly.vertices),poly.material_index) for poly in obj.data.polygons),
        str(obj.data.get('wl_faces','{}')),
        tuple((mat.name,mat.get('wl_texture',''),mat.get('wl_width',64),mat.get('wl_height',64))
              if mat else None for mat in obj.data.materials),
        float(obj.get('wl_unit_meters',1.0)),
    )


def _live_tick():
    """Poll brushes and reapply stored texture projection after geometry changes."""
    global _live_reprojecting
    try:
        from .workspace import active
        if not active(bpy.context, 'textures'):return _LIVE_POLL_SECONDS
        scene_data=bpy.context.scene
        if not scene_data or not hasattr(scene_data,'wavelength'):
            return _LIVE_POLL_SECONDS
        settings=scene_data.wavelength
        enabled=settings.live_texture_reproject
        # Keep the face-texture inspector synchronized with the active Edit Mode face.
        global _last_face_ui
        active=bpy.context.edit_object
        if active and active.type=='MESH' and active.get('wl_role')=='BRUSH':
            try:
                import bmesh
                bm=bmesh.from_edit_mesh(active.data);face=bm.faces.active
                if face is not None:
                    attr=active.data.attributes.get('wl_face_id')
                    fid=attr.data[face.index].value if attr and face.index < len(attr.data) else face.index+1
                    token=(active.name_full,int(fid))
                    if token!=_last_face_ui:
                        rec=json.loads(active.data.get('wl_faces','{}')).get(str(fid),{})
                        proj=rec.get('projection',[0,0,0,1,1]);axes=rec.get('axes')
                        settings.texture=rec.get('texture',settings.texture)
                        if axes:
                            settings.shift_u=float(axes[0][3]);settings.shift_v=float(axes[1][3]);settings.texture_rotation=float(proj[2] if len(proj)>2 else 0);settings.texture_scale_u=float(proj[3] if len(proj)>3 else 1);settings.texture_scale_v=float(proj[4] if len(proj)>4 else 1)
                        else:
                            settings.shift_u=float(proj[0]);settings.shift_v=float(proj[1]);settings.texture_rotation=float(proj[2]);settings.texture_scale_u=float(proj[3]);settings.texture_scale_v=float(proj[4])
                        _last_face_ui=token
            except (ReferenceError,RuntimeError,ValueError,KeyError,IndexError,TypeError):
                pass
        live_names=set();now=time.monotonic()
        for obj in scene_data.objects:
            if obj.type!='MESH' or obj.get('wl_role')!='BRUSH':
                continue
            name=obj.name_full;live_names.add(name)
            current_mode = obj.mode
            previous_mode = _live_modes.get(name)
            if current_mode != 'OBJECT':
                # Remember the edit session even when live texture reprojection is off.
                _live_modes[name] = current_mode
                continue

            # Edit -> Object is the universal Wavelength brush commit boundary.
            # Recenter the origin first, preserving world-space geometry, then let
            # the existing projection/state machinery observe the finalized mesh.
            if previous_mode == 'EDIT' or name in _edit_sessions:
                try:
                    _finalize_edit_session(obj, settings)
                except (ReferenceError, RuntimeError, AttributeError):
                    pass
            _live_modes[name] = current_mode

            try: state=_brush_state(obj)
            except (ReferenceError,RuntimeError):
                continue
            old=_live_state.get(name)
            _live_state[name]=state
            if not enabled or old is None or old==state or _live_reprojecting:
                continue
            _live_reprojecting=True
            try:
                apply_uv(obj,settings.engine)
                obj.data.update()
            except (ValueError,RuntimeError,KeyError,BrushError):
                pass
            finally:
                _live_reprojecting=False
        for name in set(_live_state) | set(_live_modes):
            if name not in live_names:
                _live_state.pop(name,None)
                _live_modes.pop(name,None)
    except (ReferenceError,RuntimeError,AttributeError):
        pass
    return _LIVE_POLL_SECONDS


def register():
    _live_state.clear(); _live_modes.clear(); _edit_sessions.clear()
    if _edit_commit_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_edit_commit_handler)
    if not bpy.app.timers.is_registered(_live_tick):
        bpy.app.timers.register(_live_tick,first_interval=_LIVE_POLL_SECONDS,persistent=True)


def unregister():
    if bpy.app.timers.is_registered(_live_tick):
        bpy.app.timers.unregister(_live_tick)
    try:
        bpy.app.handlers.depsgraph_update_post.remove(_edit_commit_handler)
    except ValueError:
        pass
    _live_state.clear(); _live_modes.clear(); _edit_sessions.clear()
