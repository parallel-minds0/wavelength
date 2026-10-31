"""Editable Source displacement surfaces attached to their original brush faces.

The brush remains authoritative for the base quad; the surface owns only grid
positions, blend values and triangle attributes. Neither is regenerated on edit.
"""
import copy,json,math
from dataclasses import asdict
import bpy,bmesh
from bpy.props import EnumProperty,IntProperty,BoolProperty
from mathutils import Vector,Matrix
from . import displacement,formats,profiles,workspace

KEY='wl_source_displacement'
INDEX='wl_displacement_index'
BLEND='wl_terrain_blend'
TAGS='wl_displacement_triangle_tags'
_RUNNING=[]


def info(obj):return json.loads(obj[KEY])

def surfaces(source):return [o for o in source.children if o.get(KEY)]


def surface_material(obj):
    slots={p.material_index for p in obj.data.polygons}
    materials=[obj.data.materials[i] if i<len(obj.data.materials) else None for i in slots]
    if not materials or any(m is None or not m.get('wl_texture') for m in materials):
        raise ValueError(obj.name+': assign a Source material to the displacement')
    if len({m['wl_texture'] for m in materials})!=1:
        raise ValueError(obj.name+': one displacement is one Source material surface; use Texture Blend or separate patches')
    return materials[0]


def _export_quad(source,fid,corners):
    """Use the exported brush planes, avoiding float preview errors at map edges."""
    from .scene import brush_from_object
    brush=brush_from_object(source,source.get('wl_owner_profile',bpy.context.scene.wavelength.engine))
    ids=sorted(d.value for d in source.data.attributes['wl_face_id'].data)
    vertices,polygons=formats.brush_mesh(brush)
    points=[Vector(vertices[i]) for i in polygons[ids.index(fid)]]
    return [min(points,key=lambda p:(p-Vector(corner)).length_squared).copy() for corner in corners]


def source_face(obj):
    source=obj.parent
    if source is None or source.type!='MESH' or source.get('wl_role')!='BRUSH':
        raise ValueError(obj.name+': displacement backing brush is missing')
    if source.mode!='OBJECT':raise ValueError('Finish editing the displacement backing brush before exporting')
    record=info(obj);attribute=source.data.attributes.get('wl_face_id')
    polygon=next((p for p,d in zip(source.data.polygons,attribute.data) if d.value==record['face_id']),None) if attribute else None
    if polygon is None or len(polygon.vertices)!=4 or set(polygon.vertices)!=set(record['corners']):
        raise ValueError(obj.name+': backing face topology changed; recreate the displacement')
    unit=obj['wl_unit_meters']
    from .scene import world_point
    corners=[Vector(world_point(source,source.data.vertices[i].co,unit)) for i in record['corners']]
    return source,record,_export_quad(source,record['face_id'],corners)


def _uv(obj,face,quad):
    size=2**info(obj)['data']['power']+1
    domain=obj.data.uv_layers.get('UVMap') or obj.data.uv_layers.new(name='UVMap')
    layer=obj.data.uv_layers.get('wavelength') or obj.data.uv_layers.new(name='wavelength')
    material=surface_material(obj)
    width=material.get('wl_width',64) if material else 64;height=material.get('wl_height',64) if material else 64
    axes=face.axes or formats.quake_axes(face.plane()[0],face.projection)
    ids=obj.data.attributes[INDEX]
    for loop in obj.data.loops:
        index=ids.data[loop.vertex_index].value;j,i=divmod(index,size);u=i/(size-1);v=j/(size-1)
        domain.data[loop.index].uv=(u,v)
        point=displacement.base(quad,u,v)
        layer.data[loop.index].uv=((sum(axes[0][k]*point[k] for k in range(3))/face.projection[3]+axes[0][3])/width,
            1-(sum(axes[1][k]*point[k] for k in range(3))/face.projection[4]+axes[1][3])/height)


def attach(source,face_index,face):
    data=face.vmf['dispinfo'];size=2**data['power']+1;unit=source['wl_unit_meters']
    polygon=source.data.polygons[face_index]
    from .scene import world_point
    verts=[world_point(source,v.co,unit) for v in source.data.vertices]
    quad=displacement.quad(verts,list(polygon.vertices),data['startposition'])
    corners=[min(polygon.vertices,key=lambda i:(Vector(verts[i])-Vector(p)).length_squared) for p in quad]
    quad=[tuple(p) for p in _export_quad(source,source.data.attributes['wl_face_id'].data[face_index].value,quad)]
    points=displacement.grid(data,quad,face.plane()[0])
    inverse=source.matrix_world.inverted()
    local=[tuple(sum(float(inverse[i][j])*float(p[j])*unit for j in range(3))+float(inverse[i][3]) for i in range(3)) for p in points]
    mesh=bpy.data.meshes.new('Source Displacement Grid');mesh.from_pydata(local,[],displacement.triangles(size));mesh.update()
    obj=bpy.data.objects.new(source.name+' · Displacement',mesh)
    source.users_collection[0].objects.link(obj);obj.parent=source
    obj[KEY]=json.dumps({'face_id':source.data.attributes['wl_face_id'].data[face_index].value,'corners':corners,'data':data,
        'initial_vertices':[list(v.co) for v in mesh.vertices],
        'initial_matrix':[list(row) for row in source.matrix_world],
        'initial_quad':[list(Vector(p)) for p in quad]})
    obj['wl_role']='DISPLACEMENT';obj['wl_unit_meters']=unit;obj['wl_owner_profile']=bpy.context.scene.wavelength.engine
    from .scene import uid
    obj['wl_id']=uid()
    ids=mesh.attributes.new(INDEX,'INT','POINT')
    for i,d in enumerate(ids.data):d.value=i
    blend=mesh.attributes.new(BLEND,'FLOAT','POINT')
    alphas=data.get('alphas',[[0]*size for _ in range(size)])
    for i,d in enumerate(blend.data):d.value=max(0,min(1,alphas[i//size][i%size]/255))
    tags=mesh.attributes.new(TAGS,'INT','FACE');values=[x for row in data.get('triangle_tags',[]) for x in row]
    for i,d in enumerate(tags.data):d.value=values[i] if values else 9
    if source.data.materials:mesh.materials.append(source.data.materials[polygon.material_index])
    for p in mesh.polygons:p.use_smooth=True
    settings=obj.wavelength_terrain
    settings.width=(Vector(quad[1])-Vector(quad[0])).length;settings.length=(Vector(quad[3])-Vector(quad[0])).length
    settings.paint_radius=max(settings.width,settings.length)*.2;settings.paint_strength=max(settings.width,settings.length)*.01
    settings.power=str(data['power'])
    _uv(obj,face,quad)
    record=info(obj);uvs=[None]*len(mesh.vertices)
    for loop in mesh.loops:uvs[loop.vertex_index]=list(mesh.uv_layers['wavelength'].data[loop.index].uv)
    material=surface_material(obj)
    record['initial_uv']=uvs
    record['initial_material']=[material['wl_texture'].casefold(),material.get('wl_width',64),material.get('wl_height',64)]
    record['initial_face_uv']=[face.projection,face.axes]
    obj[KEY]=json.dumps(record)
    return obj


def mask(source):
    from . import terrain_face
    attribute=source.data.attributes.get('wl_displacement_surface') or source.data.attributes.new('wl_displacement_surface','BOOLEAN','FACE')
    # Source does not render the ordinary sides of a displaced backing solid.
    attached=bool(surfaces(source))
    for d in attribute.data:d.value=attached
    if attached and not any(m.type=='NODES' and m.node_group and m.node_group.get('wl_generator')==terrain_face.MASK for m in source.modifiers):
        modifier=source.modifiers.new('Source Displacement Backing','NODES');modifier.node_group=terrain_face.mask_group()
    source.data.update()


def read_surface(obj,with_uv=False):
    record=info(obj);size=2**record['data']['power']+1
    if obj.mode=='EDIT':obj.update_from_editmode()
    surface_material(obj)
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    try:
        ids=mesh.attributes.get(INDEX)
        if ids is None or len(mesh.vertices)!=size*size:raise ValueError(obj.name+': displacement topology changed; keep the original grid or use Change Power')
        order=[d.value for d in ids.data]
        if set(order)!=set(range(size*size)):raise ValueError(obj.name+': displacement vertex identities changed')
        expected={frozenset(tri) for tri in displacement.triangles(size)}
        mesh.calc_loop_triangles()
        actual={frozenset(order[i] for i in tri.vertices) for tri in mesh.loop_triangles}
        if actual!=expected or len(mesh.loop_triangles)!=2*(size-1)**2:raise ValueError(obj.name+': displacement triangle topology changed')
        unit=obj['wl_unit_meters'];points=[None]*(size*size);alphas=[0.]*(size*size)
        blend=mesh.attributes.get(BLEND)
        for v,index in zip(mesh.vertices,order):
            point=obj.matrix_world@v.co/unit
            if any(not math.isfinite(c) or abs(c)>32768 for c in point):raise ValueError(obj.name+': displacement exceeds finite Source coordinate bounds')
            points[index]=point;alphas[index]=max(0,min(1,blend.data[v.index].value))*255 if blend else 0
        tags=mesh.attributes.get(TAGS)
        if tags is None:raise ValueError(obj.name+': displacement triangle attributes were removed')
        tag_lookup={frozenset(order[i] for i in p.vertices):tags.data[p.index].value for p in mesh.polygons}
        values=[tag_lookup[frozenset(t)] for t in displacement.triangles(size)]
        for a,b,c in displacement.triangles(size):
            if (points[b]-points[a]).cross(points[c]-points[a]).length<1e-8:
                error=ValueError(obj.name+': displacement has a collapsed triangle')
                inverse={d.value:i for i,d in enumerate(obj.data.attributes[INDEX].data)}
                error.vertices=[inverse[i] for i in (a,b,c)];error.object_name=obj.name
                raise error
        if with_uv:
            layer=mesh.uv_layers.get('wavelength')
            if layer is None:raise ValueError(obj.name+': displacement material UVs are missing')
            uvs=[None]*(size*size)
            for loop in mesh.loops:
                index=order[loop.vertex_index];uv=layer.data[loop.index].uv.copy()
                if uvs[index] is not None and (uvs[index]-uv).length>1e-5:
                    raise ValueError(obj.name+': UV seams cannot be represented by a Source displacement face')
                uvs[index]=uv
            return points,alphas,values,uvs
        return points,alphas,values
    finally:evaluated.to_mesh_clear()


def export_surface(obj,face):
    source,record,quad=source_face(obj);data=copy.deepcopy(record['data']);size=2**data['power']+1
    points,alphas,tags,uvs=read_surface(obj,True)
    normal=Vector(face.plane()[0]);start=list(quad[0])
    # A mirrored brush reverses the canonical row/column orientation.
    if (quad[1]-quad[0]).cross(quad[3]-quad[0]).dot(normal)<0:
        quad=[quad[0],quad[3],quad[2],quad[1]]
        permutation=[i*size+j for j in range(size) for i in range(size)]
        points=[points[i] for i in permutation];alphas=[alphas[i] for i in permutation];uvs=[uvs[i] for i in permutation]
        triangles=displacement.triangles(size);lookup={frozenset(t):i for i,t in enumerate(triangles)}
        tag_order=[lookup[frozenset(permutation[i] for i in tri)] for tri in triangles]
        tags=[tags[i] for i in tag_order]
        for key,width in displacement.WIDTHS.items():
            if key not in data:continue
            rows=data[key]
            data[key]=[[x for i in range(size) for x in rows[i][j*width:(j+1)*width]] for j in range(size)]
        if data.get('triangle_tags'):
            values=[x for row in data['triangle_tags'] for x in row]
            values=[values[i] for i in tag_order]
            data['triangle_tags']=[values[j*2*(size-1):(j+1)*2*(size-1)] for j in range(size-1)]
    # startposition is an orientation hint, not necessarily the exact corner.
    # Decompiled maps can legitimately differ by a few thousandths of a unit.
    if (record.get('initial_quad')!=[list(p) for p in quad] and
            (quad[0]-Vector(data['startposition'])).length>max(.001,quad[0].length*2e-7)):
        data['startposition']=start
    original=displacement.grid(data,[tuple(p) for p in quad],normal)
    changed=any((p-Vector(q)).length>max(.001,p.length*2e-7) for p,q in zip(points,original))
    if (not obj.modifiers and record.get('initial_vertices')==[list(v.co) for v in obj.data.vertices] and
            record.get('initial_matrix')==[list(row) for row in obj.matrix_world] and
            record.get('initial_quad')==[list(p) for p in quad]):
        changed=False  # Keep imported fields byte-for-byte through float32 previews.
    if changed:
        normals=[];distances=[]
        for j in range(size):
            nr=[];dr=[]
            for i in range(size):
                base=Vector(displacement.base(quad,i/(size-1),j/(size-1)))+normal*data.get('elevation',0)
                if data.get('offsets'):base+=Vector(data['offsets'][j][i*3:i*3+3])
                delta=points[j*size+i]-base;distance=delta.length
                nr.extend(delta/distance if distance>1e-10 else normal);dr.append(distance)
            normals.append(nr);distances.append(dr)
        data['normals']=normals;data['distances']=distances
    original_alpha=[max(0,min(255,x)) for row in data.get('alphas',[[0]*size for _ in range(size)]) for x in row]
    if any(abs(a-b)>.0001 for a,b in zip(alphas,original_alpha)):
        data['alphas']=[alphas[j*size:(j+1)*size] for j in range(size)]
        _ensure_raw(data,'alphas')
    original_tags=[x for row in data.get('triangle_tags',[]) for x in row] or [9]*len(tags)
    if tags!=original_tags:
        data['triangle_tags']=[tags[j*2*(size-1):(j+1)*2*(size-1)] for j in range(size-1)]
        _ensure_raw(data,'triangle_tags')
    material=surface_material(obj);face.texture=material['wl_texture']
    pristine_uv=(record.get('initial_uv')==[list(uv) for uv in uvs] and record.get('initial_quad')==[list(p) for p in quad] and
        record.get('initial_material')==[material['wl_texture'].casefold(),material.get('wl_width',64),material.get('wl_height',64)] and
        record.get('initial_face_uv')==[face.projection,face.axes])
    if not pristine_uv:export_uv(face,quad,uvs,material,size)
    face.vmf=dict(face.vmf or {});face.vmf['dispinfo']=data
    return face


def export_uv(face,quad,uvs,material,size):
    """Capture native affine UV edits/texture lock as a Valve face projection."""
    width=material.get('wl_width',64);height=material.get('wl_height',64)
    axes=face.axes or formats.quake_axes(face.plane()[0],face.projection)
    positions=[Vector(displacement.base(quad,i/(size-1),j/(size-1))) for j in range(size) for i in range(size)]
    values=[(uv.x*width,(1-uv.y)*height) for uv in uvs]
    expected=[tuple(sum(axes[k][c]*p[c] for c in range(3))/face.projection[3+k]+axes[k][3] for k in range(2)) for p in positions]
    if all(abs(a[k]-b[k])<.01 for a,b in zip(values,expected) for k in range(2)):return
    u=(quad[1]-quad[0]).normalized();normal=Vector(face.plane()[0]);v=normal.cross(u).normalized()
    origin=quad[0];p=quad[1]-origin;q=quad[3]-origin
    x1,y1=p.dot(u),p.dot(v);x2,y2=q.dot(u),q.dot(v);det=x1*y2-y1*x2
    if abs(det)<1e-10:raise ValueError('Displacement UV base is degenerate')
    result=[]
    for channel in range(2):
        first=values[0][channel];b=values[size-1][channel]-first;c=values[(size-1)*size][channel]-first
        axis=u*((b*y2-c*y1)/det)+v*((x1*c-x2*b)/det);shift=first-axis.dot(origin)
        if axis.length<1e-10:raise ValueError('Displacement UV projection is collapsed')
        if any(abs(axis.dot(p)+shift-value[channel])>.01 for p,value in zip(positions,values)):
            raise ValueError('Non-affine displacement UV edits cannot be represented by Source; keep one planar projection')
        result.append([*axis,shift])
    face.axes=result;face.projection=[0,0,0,1,1]


def _ensure_raw(data,key):
    if '_raw' in data and not any(k==key for k,v in data['_raw']):data['_raw'].append((key,[]))


def assign_material(context,obj,material):
    """A Source patch is one face: assigning a texture covers the entire grid."""
    source,record,quad=source_face(obj)
    from .scene import brush_from_object
    faces=brush_from_object(source,context.scene.wavelength.engine)
    face=faces[sorted(d.value for d in source.data.attributes['wl_face_id'].data).index(record['face_id'])]
    try:face=export_surface(obj,face)
    except ValueError:pass  # Material assignment can repair invalid/missing UVs.
    slot=next((i for i,m in enumerate(obj.data.materials) if m==material),None)
    if slot is None:slot=len(obj.data.materials);obj.data.materials.append(material)
    if obj.mode=='EDIT':
        bm=bmesh.from_edit_mesh(obj.data);ids=bm.verts.layers.int.get(INDEX)
        layer=bm.loops.layers.uv.get('wavelength') or bm.loops.layers.uv.new('wavelength')
        size=2**record['data']['power']+1;axes=face.axes or formats.quake_axes(face.plane()[0],face.projection)
        for polygon in bm.faces:
            polygon.material_index=slot
            for loop in polygon.loops:
                index=loop.vert[ids];j,i=divmod(index,size);p=displacement.base(quad,i/(size-1),j/(size-1))
                loop[layer].uv=((sum(axes[0][k]*p[k] for k in range(3))/face.projection[3]+axes[0][3])/material.get('wl_width',64),
                    1-(sum(axes[1][k]*p[k] for k in range(3))/face.projection[4]+axes[1][3])/material.get('wl_height',64))
        bmesh.update_edit_mesh(obj.data,loop_triangles=False,destructive=False)
    else:
        for polygon in obj.data.polygons:polygon.material_index=slot
        _uv(obj,face,quad)


def copy_surfaces(source,duplicate):
    """Native brush duplication includes every otherwise-unselected grid child."""
    existing={info(o)['face_id'] for o in surfaces(duplicate)}
    from .scene import uid
    for surface in surfaces(source):
        if info(surface)['face_id'] in existing:continue
        child=surface.copy()
        if source.data!=duplicate.data:child.data=surface.data.copy()
        duplicate.users_collection[0].objects.link(child);child.parent=duplicate;child['wl_id']=uid()


def duplicate_surface(original,duplicate):
    """Duplicating a surface creates its own backing rather than a second claim."""
    if original.parent is None or duplicate.parent!=original.parent:return
    source=original.parent
    from .scene import uid
    root=source.copy()
    if duplicate.data!=original.data:root.data=source.data.copy()
    duplicate.users_collection[0].objects.link(root);root['wl_id']=uid()
    duplicate.parent=root
    copy_surfaces(source,root)


def apply(source,brush):
    children=surfaces(source);ids=sorted(d.value for d in source.data.attributes['wl_face_id'].data)
    expected={ids[i] for i,f in enumerate(brush) if (f.vmf or {}).get('dispinfo')}
    owners={}
    for obj in children:
        fid=info(obj)['face_id']
        if fid in owners:raise ValueError('Two displacement grids claim the same backing face')
        owners[fid]=obj
    if expected!=set(owners):raise ValueError(source.name+': displacement surface is missing or has lost its backing face')
    for fid,obj in owners.items():brush[ids.index(fid)]=export_surface(obj,brush[ids.index(fid)])
    return brush

# docs:begin native-displacement-authoring

def create_faces(context,power=3):
    """Make native grids from selected quad faces without consuming the brush."""
    source=context.object
    if context.mode!='EDIT_MESH' or not source or source.get('wl_role')!='BRUSH':raise ValueError('Select quad brush faces in Edit Mode')
    if len(context.objects_in_mode)!=1:raise ValueError('Create displacements on one backing brush at a time')
    if source.get('wl_entity_id'):raise ValueError('Source displacements must belong to world brushes; convert the brush entity to world geometry first')
    from . import primitive_ui,procedural
    root=primitive_ui.root_for(source)
    if root and procedural.state(root)=='PROCEDURAL':raise ValueError('Finalize Geometry before creating displacements on a live primitive')
    if any(not (m.type=='NODES' and m.node_group and m.node_group.get('wl_generator')=='wavelength.displacement.face_mask') for m in source.modifiers):
        raise ValueError('Finalize or apply backing-brush modifiers before creating displacements')
    bm=bmesh.from_edit_mesh(source.data);bm.faces.ensure_lookup_table()
    selected=[f.index for f in bm.faces if f.select and not f.hide]
    if not selected or any(len(bm.faces[i].verts)!=4 for i in selected):raise ValueError('Select one or more four-sided brush faces')
    bpy.ops.object.mode_set(mode='OBJECT')
    from . import scene
    brush=scene.brush_from_object(source,context.scene.wavelength.engine,True)
    ids=source.data.attributes['wl_face_id'];records=json.loads(source.data['wl_faces']);ordered=sorted(d.value for d in ids.data)
    made=[]
    try:
        for index in selected:
            fid=ids.data[index].value;face=brush[ordered.index(fid)]
            if (face.vmf or {}).get('dispinfo'):raise ValueError('That face already has a displacement')
            n=face.plane()[0];size=2**power+1
            start=list(scene.world_point(source,source.data.vertices[source.data.polygons[index].vertices[0]].co,source['wl_unit_meters']))
            data={'power':power,'startposition':start,'normals':[list(n)*size for _ in range(size)],'distances':[[0]*size for _ in range(size)]}
            face.vmf=dict(face.vmf or {});face.vmf['dispinfo']=data
            made.append(attach(source,index,face));records[str(fid)]=asdict(face)
        source.data['wl_faces']=json.dumps(records);mask(source)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in made:obj.select_set(True)
        context.view_layer.objects.active=made[0]
        return made
    except Exception:
        for obj in made:
            mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(mesh)
        raise


def sample(values,size,u,v):
    """Piecewise-linear sampling matches Source's alternating triangle diagonals."""
    x=max(0,min(size-1,u*(size-1)));y=max(0,min(size-1,v*(size-1)))
    i=min(size-2,int(x));j=min(size-2,int(y));u=x-i;v=y-j;a=j*size+i;b=a+1;c=a+size;d=c+1
    if a%2:
        ids,weights=((a,b,c),(1-u-v,u,v)) if u+v<=1 else ((b,d,c),(1-v,u+v-1,1-u))
    else:ids,weights=((a,b,d),(1-u,u-v,v)) if u>=v else ((a,d,c),(1-v,u,v-u))
    if isinstance(values[0],(int,float)):return sum(values[k]*w for k,w in zip(ids,weights))
    return sum((Vector(values[k])*w for k,w in zip(ids,weights)),Vector((0,)*len(values[0])))


def change_power(obj,power):
    if obj.mode!='OBJECT':raise ValueError('Leave Edit Mode before changing displacement power')
    source,record,quad=source_face(obj);old=record['data'];size=2**old['power']+1;newsize=2**power+1
    if old['power']==power:return
    points,alphas,tags,uvs=read_surface(obj,True)
    data=copy.deepcopy(old);data['power']=power
    for key,width in displacement.WIDTHS.items():
        if key not in data:continue
        flat=[row[i:i+width] for row in old[key] for i in range(0,len(row),width)]
        rows=[]
        for j in range(newsize):
            row=[]
            for i in range(newsize):
                value=sample([v[0] for v in flat],size,i/(newsize-1),j/(newsize-1)) if width==1 else sample(flat,size,i/(newsize-1),j/(newsize-1))
                row.extend([value] if width==1 else value)
            rows.append(row)
        data[key]=rows
    data['allowed_verts']=[-1]*10;data['triangle_tags']=[[9]*(2*(newsize-1)) for _ in range(newsize-1)]
    record['data']=data;obj[KEY]=json.dumps(record)
    inverse=obj.matrix_world.inverted();unit=obj['wl_unit_meters']
    verts=[inverse@(sample(points,size,i/(newsize-1),j/(newsize-1))*unit) for j in range(newsize) for i in range(newsize)]
    mesh=bpy.data.meshes.new('Source Displacement Grid');mesh.from_pydata(verts,[],displacement.triangles(newsize));mesh.update()
    mesh.materials.append(surface_material(obj))
    oldmesh=obj.data;obj.data=mesh
    ids=mesh.attributes.new(INDEX,'INT','POINT');blend=mesh.attributes.new(BLEND,'FLOAT','POINT');attr=mesh.attributes.new(TAGS,'INT','FACE')
    for k,d in enumerate(ids.data):
        d.value=k;j,i=divmod(k,newsize);blend.data[k].value=sample(alphas,size,i/(newsize-1),j/(newsize-1))/255
    # Triangle-specific attributes follow the nearest original cell/triangle.
    for k,d in enumerate(attr.data):
        cell,tri=divmod(k,2);j,i=divmod(cell,newsize-1);oi=min(size-2,int((i+.5)*(size-1)/(newsize-1)));oj=min(size-2,int((j+.5)*(size-1)/(newsize-1)))
        d.value=tags[2*(oj*(size-1)+oi)+tri]
    for p in mesh.polygons:p.use_smooth=True
    from .scene import brush_from_object
    face=brush_from_object(source,bpy.context.scene.wavelength.engine)[sorted(d.value for d in source.data.attributes['wl_face_id'].data).index(record['face_id'])]
    _uv(obj,face,quad)
    layer=mesh.uv_layers['wavelength']
    for loop in mesh.loops:
        j,i=divmod(loop.vertex_index,newsize);layer.data[loop.index].uv=sample(uvs,size,i/(newsize-1),j/(newsize-1))
    if not oldmesh.users:bpy.data.meshes.remove(oldmesh)


def edge_indices(size):
    return [list(range(size)),[i*size+size-1 for i in range(size)],list(range(size*size-1,size*(size-1)-1,-1)),[i*size for i in range(size-1,-1,-1)]]


def connections(items):
    """Find full and half-edge Source neighbors, including differing powers."""
    result=[];quads={o:[p*o['wl_unit_meters'] for p in source_face(o)[2]] for o in items}
    bounds={o:([min(p[i] for p in quads[o]) for i in range(3)],[max(p[i] for p in quads[o]) for i in range(3)]) for o in items}
    for index,a in enumerate(items):
        for b in items[index+1:]:
            tolerance=max(a['wl_unit_meters'],b['wl_unit_meters'])*.05
            if any(bounds[a][1][i]<bounds[b][0][i]-tolerance or bounds[b][1][i]<bounds[a][0][i]-tolerance for i in range(3)):continue
            for ae in range(4):
                p,q=quads[a][ae],quads[a][(ae+1)%4];direction=q-p;length=direction.length
                if length<1e-10:continue
                for be in range(4):
                    r,s=quads[b][be],quads[b][(be+1)%4];other=s-r
                    tolerance=max(a['wl_unit_meters'],b['wl_unit_meters'])*.05
                    if other.length<1e-10 or abs(direction.normalized().dot(other.normalized()))<1-1e-5:continue
                    if max((r-p).cross(direction).length,(s-p).cross(direction).length)/length>tolerance:continue
                    t0=(r-p).dot(direction)/direction.length_squared;t1=(s-p).dot(direction)/direction.length_squared
                    lo=max(0,min(t0,t1));hi=min(1,max(t0,t1))
                    if (hi-lo)*length<=tolerance:continue
                    u0=(lo-t0)/(t1-t0);u1=(hi-t0)/(t1-t0)
                    if any(min(abs(x-y) for y in (0,.5,1))>1e-4 for x in (lo,hi,u0,u1)):
                        raise ValueError('Source displacement neighbors must meet at full or half edges')
                    result.append((a,ae,b,be,t0,t1,lo,hi))
    return result


def connected(obj):
    items=[o for o in bpy.context.scene.objects if o.get(KEY) and not o.get('wl_exclude')]
    pairs=connections(items);found={obj};changed=True
    while changed:
        changed=False
        for a,_,b,*_ in pairs:
            if (a in found)!=(b in found):found.update((a,b));changed=True
    return list(found)


def sew(items,smooth=False):
    if any(o.modifiers for o in items):raise ValueError('Apply surface modifiers to a copy before sewing')
    pairs=connections(items)
    if not pairs:raise ValueError('No matching displacement edges were found')
    sizes={o:2**info(o)['data']['power']+1 for o in items};edges={o:edge_indices(sizes[o]) for o in items}
    world={};alphas={}
    for obj in items:
        points,alpha,_=read_surface(obj);world[obj]=[p*obj['wl_unit_meters'] for p in points];alphas[obj]=alpha
    parents={}
    def find(x):
        parents.setdefault(x,x)
        if parents[x]!=x:parents[x]=find(parents[x])
        return parents[x]
    def union(a,b):parents[find(a)]=find(b)
    matches=[]
    for a,ae,b,be,t0,t1,lo,hi in pairs:
        aa=edges[a][ae];bb=edges[b][be];knots=[]
        for ai,index in enumerate(aa):
            t=ai/(sizes[a]-1);u=(t-t0)/(t1-t0);bi=round(u*(sizes[b]-1))
            if lo-1e-5<=t<=hi+1e-5 and 0<=bi<len(bb) and abs(u-bi/(sizes[b]-1))<1e-5:
                union((a,index),(b,bb[bi]));knots.append((t,(a,index)))
        if len(knots)<2:raise ValueError('Displacement neighbors have no compatible edge samples')
        matches.append((a,aa,b,bb,t0,t1,lo,hi,knots))
    groups={}
    for key in tuple(parents):groups.setdefault(find(key),[]).append(key)
    targets={};masks={}
    for group in groups.values():
        target=sum((world[o][i] for o,i in group),Vector())/len(group)
        if smooth:
            nearby=[]
            for o,i in group:
                for edge in o.data.edges:
                    if i in edge.vertices:
                        other=edge.vertices[1] if edge.vertices[0]==i else edge.vertices[0]
                        if (o,other) not in parents:nearby.append(world[o][other])
            if nearby:target=target.lerp(sum(nearby,Vector())/len(nearby),.25)
        alpha=sum(alphas[o][i] for o,i in group)/len(group)
        for key in group:targets[key]=target;masks[key]=alpha
    for a,aa,b,bb,t0,t1,lo,hi,knots in matches:
        for obj,indices in ((a,aa),(b,bb)):
            for k,index in enumerate(indices):
                t=k/(len(indices)-1) if obj==a else t0+(t1-t0)*k/(len(indices)-1)
                if not lo-1e-5<=t<=hi+1e-5:continue
                lower=max((row for row in knots if row[0]<=t+1e-5),key=lambda row:row[0]);upper=min((row for row in knots if row[0]>=t-1e-5),key=lambda row:row[0])
                amount=0 if abs(upper[0]-lower[0])<1e-8 else (t-lower[0])/(upper[0]-lower[0])
                targets[obj,index]=targets[lower[1]].lerp(targets[upper[1]],amount)
                masks[obj,index]=masks[lower[1]]*(1-amount)+masks[upper[1]]*amount
    for (obj,index),target in targets.items():
        actual=next(v.index for v,d in zip(obj.data.vertices,obj.data.attributes[INDEX].data) if d.value==index)
        obj.data.vertices[actual].co=obj.matrix_world.inverted()@target
        obj.data.attributes[BLEND].data[actual].value=masks[obj,index]/255
    for obj in items:obj.data.update();obj['wl_source_sewn']=True
    return len(pairs)


def paint_stroke(items,point,mode,radius,strength,opacity,invert=False):
    """A spherical brush affects native grids across arbitrary surface planes."""
    count=0;snapshots={o:[o.matrix_world@v.co for v in o.data.vertices] for o in items}
    for obj in items:
        if obj.modifiers:raise ValueError('Use native editing or apply surface modifiers before painting')
        points=snapshots[obj];inverse=obj.matrix_world.inverted();normals=obj.matrix_world.to_3x3().inverted().transposed()
        neighbors={i:[] for i in range(len(points))}
        if mode=='SMOOTH':
            for edge in obj.data.edges:
                a,b=edge.vertices;neighbors[a].append(b);neighbors[b].append(a)
        for v,p in zip(obj.data.vertices,points):
            distance=(p-point).length
            if distance>radius:continue
            falloff=(1-distance/radius)**2;count+=1
            if mode=='TEXTURE':
                value=obj.data.attributes[BLEND].data[v.index];value.value=max(0,min(1,value.value+(-1 if invert else 1)*opacity*falloff))
            elif mode=='SMOOTH':
                adjacent=neighbors[v.index]
                if adjacent:
                    target=sum((points[i] for i in adjacent),Vector())/len(adjacent)
                    v.co=inverse@p.lerp(target,min(1,opacity*falloff))
            else:
                normal=(normals@v.normal).normalized();v.co=inverse@(p+normal*strength*falloff*(-1 if invert else 1))
        obj.data.update()
    return count

# docs:end native-displacement-authoring

class WL_OT_source_displacement(bpy.types.Operator):
    bl_idname='wavelength.source_displacement';bl_label='Source Displacement';bl_options={'REGISTER','UNDO'}
    action:EnumProperty(items=[(key,label,'') for key,label in (
        ('POWER','Change Power'),('SEW','Sew Selected'),('SMOOTH','Smooth Seams'),('REMOVE','Remove Displacement'),
        ('TAGS','Set Triangle Tags'),('VALIDATE','Check Displacement'),('CONVERT','Make Editable Displacements'))])
    power:EnumProperty(name='Power',items=[('2','2 — 5×5',''),('3','3 — 9×9',''),('4','4 — 17×17','')],default='3')
    tags:IntProperty(name='Triangle Tags',default=9,min=0,max=65535)
    @classmethod
    def poll(cls,context):return workspace.active(context) and context.object and profiles.is_source(context.scene.wavelength.engine)
    def invoke(self,context,event):
        if self.action=='POWER':
            self.power=str(info(context.object)['data']['power']);return context.window_manager.invoke_props_dialog(self)
        if self.action=='TAGS':return context.window_manager.invoke_props_dialog(self)
        if self.action=='REMOVE':return context.window_manager.invoke_confirm(self,event)
        return self.execute(context)
    def draw(self,context):self.layout.prop(self,'power' if self.action=='POWER' else 'tags')
    def execute(self,context):
        obj=context.object
        try:
            if self.action=='POWER':change_power(obj,int(self.power))
            elif self.action in {'SEW','SMOOTH'}:
                items=[o for o in context.selected_objects if o.get(KEY)]
                if context.mode!='OBJECT':raise ValueError('Sew displacements in Object Mode')
                count=sew(items,self.action=='SMOOTH');self.report({'INFO'},str(count)+' shared edges sewn')
            elif self.action=='TAGS':
                if obj.mode=='EDIT':
                    bm=bmesh.from_edit_mesh(obj.data);layer=bm.faces.layers.int.get(TAGS)
                    if layer is None:raise ValueError('Triangle tag attribute is missing')
                    for f in bm.faces:
                        if f.select:f[layer]=self.tags
                    bmesh.update_edit_mesh(obj.data,loop_triangles=False,destructive=False)
                else:raise ValueError('Select displacement triangles in Edit Mode')
            elif self.action=='REMOVE':
                if obj.mode!='OBJECT':raise ValueError('Leave Edit Mode before removing a displacement')
                source,record,_=source_face(obj);records=json.loads(source.data['wl_faces'])
                records[str(record['face_id'])]['vmf'].pop('dispinfo',None);source.data['wl_faces']=json.dumps(records)
                mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
                if not mesh.users:bpy.data.meshes.remove(mesh)
                mask(source);source.select_set(True);context.view_layer.objects.active=source
            elif self.action=='CONVERT':
                from . import terrain,scene
                if context.mode!='OBJECT':raise ValueError('Convert procedural terrain in Object Mode')
                selected=[o for o in context.selected_objects if o.get('wl_terrain')]
                if not selected:raise ValueError('Select procedural terrain to convert')
                sources={o.wavelength_terrain.surface_source for o in selected if o.wavelength_terrain.surface_source}
                selected=list(dict.fromkeys([*selected,*(o for o in context.scene.objects if o.get('wl_terrain') and o.wavelength_terrain.surface_source in sources and not o.get('wl_exclude'))]))
                prepared=[(original,terrain.brushes(original)) for original in selected]
                old_world=context.scene.get('wl_world_pairs')
                collections=[];states=[(o,o.get('wl_exclude'),o.hide_get()) for o in [*selected,*sources]]
                try:
                    made=[]
                    for original,brushes in prepared:
                        collection=scene.import_map(context.scene,formats.Map([formats.Entity([('classname','worldspawn')],brushes)]))
                        collections.append(collection)
                        made.extend(o for o in collection.objects if o.get(KEY))
                        original['wl_exclude']=True;original.hide_set(True)
                        source=original.wavelength_terrain.surface_source
                        if source:source['wl_exclude']=True;source.hide_set(True)
                    bpy.ops.object.select_all(action='DESELECT')
                    for item in made:item.select_set(True)
                    context.view_layer.objects.active=made[0]
                except Exception:
                    for collection in collections:
                        for item in tuple(collection.objects):
                            mesh=item.data;bpy.data.objects.remove(item,do_unlink=True)
                            if mesh and not mesh.users:bpy.data.meshes.remove(mesh)
                        bpy.data.collections.remove(collection)
                    for item,excluded,hidden in states:
                        if excluded is None:item.pop('wl_exclude',None)
                        else:item['wl_exclude']=excluded
                        item.hide_set(hidden)
                    raise
                finally:
                    if old_world is None:context.scene.pop('wl_world_pairs',None)
                    else:context.scene['wl_world_pairs']=old_world
            else:
                source,record,_=source_face(obj)
                from .scene import brush_from_object
                faces=brush_from_object(source,context.scene.wavelength.engine)
                export_surface(obj,faces[sorted(d.value for d in source.data.attributes['wl_face_id'].data).index(record['face_id'])])
                self.report({'INFO'},'Displacement grid, backing face, attributes and export are valid')
        except (ValueError,RuntimeError,KeyError) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
        return {'FINISHED'}


class WL_OT_source_displacement_paint(bpy.types.Operator):
    bl_idname='wavelength.source_displacement_paint';bl_label='Paint Source Displacement';bl_options={'REGISTER','UNDO','BLOCKING'}
    mode:EnumProperty(items=[(key,label,'') for key,label in [('CURRENT','Current'),('RAISE','Raise / Lower'),('SMOOTH','Smooth'),('TEXTURE','Texture Blend')]],default='CURRENT')
    @classmethod
    def poll(cls,context):return workspace.active(context) and context.mode=='OBJECT' and context.object and context.object.get(KEY)
    def invoke(self,context,event):
        self.obj=context.object
        try:
            self.members=connected(self.obj) if self.obj.wavelength_displacement_connected else [self.obj]
            for obj in self.members:read_surface(obj)
            settings=self.obj.wavelength_terrain
            if self.mode!='CURRENT':settings.paint_mode=self.mode
            if settings.paint_mode=='TEXTURE':
                if any(not o.data.materials or not o.data.materials[0].get('wl_source_blend') for o in self.members):
                    raise ValueError('Assign WorldVertexTransition materials before painting texture blends')
            self.area=context.area if context.area.type=='VIEW_3D' else next(a for a in context.screen.areas if a.type=='VIEW_3D')
            if settings.paint_mode=='TEXTURE' and self.area.spaces.active.shading.type in {'SOLID','WIREFRAME'}:
                self.area.spaces.active.shading.type='MATERIAL'
            self.region=next(r for r in self.area.regions if r.type=='WINDOW');self.down=False;self.last=None;self.hit=None;self.changed=False
            self.mouse=(event.mouse_x,event.mouse_y)
            self.timer=context.window_manager.event_timer_add(.05,window=context.window)
            self.handle=bpy.types.SpaceView3D.draw_handler_add(self.draw_brush,(),'WINDOW','POST_VIEW')
            _RUNNING.append(self)
            context.window_manager.modal_handler_add(self)
            self.area.header_text_set('Displacement Paint: LMB drag · Ctrl lower/erase · Shift smooth · wheel radius · Enter/Esc finish · Ctrl+Z undo')
            context.window.cursor_modal_set('PAINT_BRUSH')
            return {'RUNNING_MODAL'}
        except (ValueError,RuntimeError,StopIteration) as exc:self.report({'ERROR'},str(exc));return {'CANCELLED'}
    def finish(self,context):
        context.window_manager.event_timer_remove(self.timer)
        if self.handle:bpy.types.SpaceView3D.draw_handler_remove(self.handle,'WINDOW');self.handle=None
        self.area.header_text_set(None);context.window.cursor_modal_restore()
        if self in _RUNNING:_RUNNING.remove(self)
        return {'FINISHED'} if self.changed else {'CANCELLED'}
    def cancel(self,context):self.finish(context)
    def draw_brush(self):
        if self.hit is None or bpy.context.area!=self.area:return
        import gpu
        from gpu_extras.batch import batch_for_shader
        point,normal=self.hit
        axis=Vector((1,0,0)) if abs(normal.x)<.8 else Vector((0,1,0))
        u=normal.cross(axis).normalized();v=normal.cross(u)
        radius=self.obj.wavelength_terrain.paint_radius*self.obj['wl_unit_meters']
        center=point+normal*max(1e-5,radius*.001)
        points=[center+radius*(u*math.cos(i*math.tau/64)+v*math.sin(i*math.tau/64)) for i in range(65)]
        shader=gpu.shader.from_builtin('POLYLINE_UNIFORM_COLOR');batch=batch_for_shader(shader,'LINE_STRIP',{'pos':points})
        gpu.state.blend_set('ALPHA')
        try:
            shader.bind();shader.uniform_float('viewportSize',(self.region.width,self.region.height));shader.uniform_float('lineWidth',2)
            shader.uniform_float('color',(.2,.85,1,.9));batch.draw(shader)
        finally:gpu.state.blend_set('NONE')
    def modal(self,context,event):
        from bpy_extras import view3d_utils
        if not workspace.active(context) or (event.type in {'ESC','RET','NUMPAD_ENTER','RIGHTMOUSE'} and event.value=='PRESS'):return self.finish(context)
        settings=self.obj.wavelength_terrain
        if event.type in {'WHEELUPMOUSE','WHEELDOWNMOUSE'}:
            settings.paint_radius*=1.1 if event.type=='WHEELUPMOUSE' else 1/1.1;return {'RUNNING_MODAL'}
        if event.type=='MIDDLEMOUSE' or event.alt:self.down=False;return {'PASS_THROUGH'}
        if event.type=='LEFTMOUSE':self.down=event.value=='PRESS';self.last=None
        if event.type in {'LEFTMOUSE','MOUSEMOVE'}:self.mouse=(event.mouse_x,event.mouse_y)
        if event.type not in {'LEFTMOUSE','MOUSEMOVE','TIMER'} or (event.type=='TIMER' and not self.down):return {'RUNNING_MODAL'}
        x=self.mouse[0]-self.region.x;y=self.mouse[1]-self.region.y
        if not (0<=x<self.region.width and 0<=y<self.region.height):return {'RUNNING_MODAL'}
        rv=self.area.spaces.active.region_3d
        origin=view3d_utils.region_2d_to_origin_3d(self.region,rv,(x,y));direction=view3d_utils.region_2d_to_vector_3d(self.region,rv,(x,y));best=None
        for obj in self.members:
            inverse=obj.matrix_world.inverted();evaluated=obj.evaluated_get(context.evaluated_depsgraph_get())
            found,co,normal,_=evaluated.ray_cast(inverse@origin,(inverse.to_3x3()@direction).normalized())
            if found:
                point=obj.matrix_world@co;distance=(point-origin).length
                if best is None or distance<best[0]:best=(distance,point,(inverse.transposed().to_3x3()@normal).normalized())
        self.hit=(best[1],best[2]) if best else None
        if best and self.down:
            unit=self.obj['wl_unit_meters'];radius=settings.paint_radius*unit
            if event.type=='TIMER' or self.last is None or (best[1]-self.last).length>radius*.08:
                mode='SMOOTH' if event.shift else settings.paint_mode;rate=.2 if event.type=='TIMER' else 1
                try:
                    count=paint_stroke(self.members,best[1],mode,radius,settings.paint_strength*unit*rate,settings.paint_opacity*rate,event.ctrl)
                    if count and len(self.members)>1:sew(self.members)
                    self.changed=bool(count) or self.changed;self.last=best[1].copy()
                except (ValueError,RuntimeError) as exc:self.report({'ERROR'},str(exc));return self.finish(context)
        self.area.tag_redraw();return {'RUNNING_MODAL'}


def _flags(obj):return info(obj)['data'].get('flags',0) if obj.get(KEY) else 0

def _flag(obj,value,bit):
    record=info(obj);data=record['data'];flags=data.get('flags',0)
    data['flags']=(flags|bit) if value else (flags&~bit);_ensure_raw(data,'flags');obj[KEY]=json.dumps(record)


class WL_PT_source_displacement(bpy.types.Panel):
    bl_label='Source Displacement';bl_space_type='PROPERTIES';bl_region_type='WINDOW';bl_context='object'
    @classmethod
    def poll(cls,context):return workspace.active(context) and context.object and context.object.get(KEY)
    def draw(self,context):
        obj=context.object;data=info(obj)['data'];s=obj.wavelength_terrain;l=self.layout
        l.label(text=f"Power {data['power']} · {2**data['power']+1} × {2**data['power']+1} grid")
        l.label(text='Edit vertices or sculpt; keep grid topology intact')
        l.operator('wavelength.source_displacement',text='Change Power').action='POWER'
        l.prop(obj,'wavelength_displacement_connected',text='Paint Across Connected Surfaces')
        l.prop(s,'paint_mode');l.prop(s,'paint_radius',text='Radius (engine units)')
        l.prop(s,'paint_opacity' if s.paint_mode=='TEXTURE' else 'paint_strength')
        l.operator('wavelength.source_displacement_paint',text='Paint Displacement')
        row=l.row(align=True)
        row.operator('wavelength.source_displacement',text='Sew Selected').action='SEW'
        row.operator('wavelength.source_displacement',text='Smooth Seams').action='SMOOTH'
        l.prop(obj,'wavelength_displacement_no_physics');l.prop(obj,'wavelength_displacement_no_hull');l.prop(obj,'wavelength_displacement_no_ray')
        l.operator('wavelength.source_displacement',text='Set Selected Triangle Tags').action='TAGS'
        l.operator('wavelength.source_displacement',text='Check Displacement').action='VALIDATE'
        l.operator('wavelength.source_displacement',text='Remove Displacement').action='REMOVE'


def context_menu(self,context):
    if workspace.active(context) and context.object and context.object.get('wl_terrain') and profiles.is_source(context.scene.wavelength.engine):
        self.layout.operator('wavelength.source_displacement',text='Make Editable Displacements').action='CONVERT'


def register():
    for cls in (WL_OT_source_displacement,WL_OT_source_displacement_paint,WL_PT_source_displacement):bpy.utils.register_class(cls)
    bpy.types.Object.wavelength_displacement_connected=BoolProperty(name='Connected Surfaces',default=True)
    bpy.types.Object.wavelength_displacement_no_physics=BoolProperty(name='No Physics Collision',get=lambda o:bool(_flags(o)&2),set=lambda o,v:_flag(o,v,2))
    bpy.types.Object.wavelength_displacement_no_hull=BoolProperty(name='No Player / NPC Collision',get=lambda o:bool(_flags(o)&4),set=lambda o,v:_flag(o,v,4))
    bpy.types.Object.wavelength_displacement_no_ray=BoolProperty(name='No Ray / Bullet Collision',get=lambda o:bool(_flags(o)&8),set=lambda o,v:_flag(o,v,8))
    bpy.types.VIEW3D_MT_object_context_menu.append(context_menu)


def unregister():
    for operator in tuple(_RUNNING):
        try:operator.finish(bpy.context)
        except (ReferenceError,RuntimeError):pass
    _RUNNING.clear()
    bpy.types.VIEW3D_MT_object_context_menu.remove(context_menu)
    for field in ('connected','no_physics','no_hull','no_ray'):
        if hasattr(bpy.types.Object,'wavelength_displacement_'+field):delattr(bpy.types.Object,'wavelength_displacement_'+field)
    for cls in (WL_PT_source_displacement,WL_OT_source_displacement_paint,WL_OT_source_displacement):bpy.utils.unregister_class(cls)
