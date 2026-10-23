"""Export structured drawing grids as exact Source displacement brush faces."""
import json
from mathutils import Vector
from . import formats


def brush(obj):
    info=json.loads(obj['wl_displacement']);power=info['power'];size=2**power+1
    if power not in (2,3,4) or len(obj.data.vertices)!=size*size:
        raise ValueError('Drawing displacement needs an intact power 2/3/4 square grid; rebuild the drawing')
    expected=[{j*size+i,(j+1)*size+i,(j+1)*size+i+1,j*size+i+1} for j in range(size-1) for i in range(size-1)]
    if len(obj.data.polygons)!=len(expected) or any(set(face.vertices)!=ids for face,ids in zip(obj.data.polygons,expected)):
        raise ValueError('Displacement quad topology changed; rebuild the drawing')
    if obj.modifiers:raise ValueError('Apply displacement modifiers on a copy before export')
    unit=obj['wl_unit_meters'];points=[obj.matrix_world@v.co/unit for v in obj.data.vertices]
    if any(abs(c)>32768 for p in points for c in p):raise ValueError('Displacement exceeds Source coordinate bounds')
    n=(obj.matrix_world.to_3x3().inverted().transposed()@Vector(info['normal'])).normalized()
    base_points=[obj.matrix_world@Vector(p)/unit for p in info['base_corners']] if 'base_corners' in info else None
    u=base_points[1]-base_points[0] if info.get('vector_surface') else points[size-1]-points[0];u-=n*u.dot(n)
    if u.length<1e-5:raise ValueError('Displacement has zero length')
    u.normalize();v=n.cross(u).normalized();height=points[0].dot(n)
    domain=base_points if info.get('vector_surface') else points
    xs=[p.dot(u) for p in domain];ys=[p.dot(v) for p in domain]
    x0,x1=min(xs),max(xs);y0,y1=min(ys),max(ys)
    if x1-x0<1e-4 or y1-y0<1e-4:raise ValueError('Displacement needs at least two parallel rows')
    # Refuse folded/overlapping cells rather than exporting inverted terrain.
    for j in range(size-1):
        for i in range(size-1):
            a=points[j*size+i];b=points[j*size+i+1];c=points[(j+1)*size+i];d=points[(j+1)*size+i+1]
            if info.get('vector_surface'):
                if min((b-a).cross(c-a).length,(d-b).cross(c-b).length)<=1e-7:raise ValueError('Displacement has collapsed triangles')
            elif min((b-a).cross(c-a).dot(n),(d-b).cross(c-b).dot(n))<=1e-7:raise ValueError('Displacement folds over itself; reduce curvature or parallel spacing')
    top=base_points if base_points is not None else [u*x+v*y+n*height for x,y in ((x0,y0),(x1,y0),(x1,y1),(x0,y1))]
    verts=top+[p-n*16 for p in top]
    material=next((m.get('wl_texture') for m in obj.data.materials if m and m.get('wl_texture')),None)
    if not material:raise ValueError('Assign a Source material to the displacement before export')
    faces=[]
    for indices in ((0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)):
        face=formats.Face([list(verts[i]) for i in (indices[0],indices[2],indices[1])],material if not faces else 'tools/toolsnodraw',[0,0,0,1,1])
        face.axes=formats.quake_axes(face.plane()[0],face.projection);faces.append(face)
    normals=[];distances=[]
    for j in range(size):
        nr=[];dr=[]
        for i in range(size):
            if 'base_corners' in info:
                a=i/(size-1);b=j/(size-1);base=top[0]*((1-a)*(1-b))+top[1]*(a*(1-b))+top[2]*(a*b)+top[3]*((1-a)*b)
            else:base=u*(x0+(x1-x0)*i/(size-1))+v*(y0+(y1-y0)*j/(size-1))+n*height
            delta=points[j*size+i]-base;distance=delta.length
            nr.extend(delta/distance if distance>1e-8 else n);dr.append(distance)
        normals.append(nr);distances.append(dr)
    faces[0].vmf={'dispinfo':dict(power=power,startposition=list(top[0]),normals=normals,distances=distances)}
    return faces
