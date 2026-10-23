"""Bounded, exact-plane convex partition of closed Boolean meshes.

Partition the bounding solid by the input face planes, then retain cells whose
centres lie inside the oriented input surface. No voxelization or grid rounding:
the surface planes survive conversion. This deliberately favours correctness
over brush count; complex assets should use the model pipeline instead.
"""
import math
from .geometry import sub,dot,cross,length,face_plane,validate,TOLERANCE

EPS=1e-7

def _clean(poly):
    points=[]
    for p in poly:
        if not points or length(sub(p,points[-1]))>EPS:points.append(p)
    if len(points)>1 and length(sub(points[0],points[-1]))<=EPS:points.pop()
    changed=True
    while changed and len(points)>3:
        changed=False
        for i,p in enumerate(points):
            a=sub(p,points[i-1]);b=sub(points[(i+1)%len(points)],p)
            if length(cross(a,b))<=EPS*max(length(a),length(b)):
                points.pop(i);changed=True;break
    return points

def _clip(cell,n,d):
    """Keep n·p <= d; append one outward-facing planar cap."""
    out=[];cuts=[]
    for poly in cell:
        clipped=[]
        for a,b in zip(poly,poly[1:]+poly[:1]):
            da=dot(n,a)-d;db=dot(n,b)-d
            if da<=EPS:clipped.append(a)
            if (da < -EPS and db > EPS) or (da > EPS and db < -EPS):
                t=da/(da-db);p=tuple(a[i]+t*(b[i]-a[i]) for i in range(3));clipped.append(p);cuts.append(p)
            if abs(da)<=EPS:cuts.append(a)
        clipped=_clean(clipped)
        if len(clipped)>=3:out.append(clipped)
    cap=[]
    for p in cuts:
        if not any(length(sub(p,q))<=EPS for q in cap):cap.append(p)
    if len(cap)>=3:
        center=tuple(sum(p[i] for p in cap)/len(cap) for i in range(3))
        axis=min(((1,0,0),(0,1,0),(0,0,1)),key=lambda a:abs(dot(a,n)))
        u=cross(axis,n);size=length(u);u=tuple(v/size for v in u);v=cross(n,u)
        cap.sort(key=lambda p:math.atan2(dot(sub(p,center),v),dot(sub(p,center),u)))
        cap=_clean(cap)
        if len(cap)>=3:out.append(cap)
    return out

def _indexed(cell):
    vertices=[];faces=[]
    for poly in cell:
        face=[]
        for p in poly:
            index=next((i for i,q in enumerate(vertices) if length(sub(p,q))<=EPS),None)
            if index is None:index=len(vertices);vertices.append(p)
            face.append(index)
        if len(set(face))>=3:faces.append(face)
    return vertices,faces

def _inside(p,triangles):
    # Generalized winding number tolerates either globally reversed orientation.
    angle=0.
    for triangle in triangles:
        a,b,c=[sub(v,p) for v in triangle];la,lb,lc=map(length,(a,b,c))
        angle+=2*math.atan2(dot(a,cross(b,c)),la*lb*lc+dot(a,b)*lc+dot(b,c)*la+dot(c,a)*lb)
    return abs(angle)>2*math.pi

def volume(vertices,faces):
    # Translate near the solid to avoid cancellation far from the world origin.
    origin=vertices[0]
    return abs(sum(dot(sub(vertices[f[0]],origin),cross(sub(vertices[f[i]],origin),sub(vertices[f[i+1]],origin)))/6
                   for f in faces for i in range(1,len(f)-1)))

def decompose(vertices,faces,triangles,max_cells=512,max_planes=96):
    """Return validated convex (vertices, faces) parts in engine units.

    The caller supplies triangulated, consistently wound manifold geometry.
    Resource limits and volume conservation are checked before any scene commit.
    """
    try:
        validate(vertices,faces)
        return [(vertices,faces)]
    except ValueError:pass
    planes=[]
    for face in faces:
        _,n,d=face_plane(vertices,face)
        if any(abs(dot(n,vertices[i])-d)>EPS*10 for i in face):raise ValueError('Triangulate nonplanar faces before BSP conversion')
        # Boolean vertices are float32. Tiny near-zero normal components must
        # not choose the sign or turn one surface into many almost-equal planes.
        first=n[max(range(3),key=lambda i:abs(n[i]))]
        if first<0:n=tuple(-c for c in n);d=-d
        if not any(length(sub(n,m))<1e-5 and abs(d-e)<TOLERANCE*.1 for m,e in planes):planes.append((n,d))
    if len(planes)>max_planes:raise ValueError(f'BSP conversion exceeds {max_planes} surface planes; simplify the mesh or export a model')
    lo=[min(v[i] for v in vertices) for i in range(3)];hi=[max(v[i] for v in vertices) for i in range(3)]
    if any(b-a<=EPS for a,b in zip(lo,hi)):raise ValueError('BSP conversion needs a solid volume')
    box=[(lo[0],lo[1],lo[2]),(hi[0],lo[1],lo[2]),(hi[0],hi[1],lo[2]),(lo[0],hi[1],lo[2]),
         (lo[0],lo[1],hi[2]),(hi[0],lo[1],hi[2]),(hi[0],hi[1],hi[2]),(lo[0],hi[1],hi[2])]
    faces_box=[[0,3,2,1],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]]
    cells=[[[box[i] for i in f] for f in faces_box]];work=0
    for n,d in planes:
        extent=[dot(n,p)-d for p in vertices]
        # Supporting planes bound the whole solid. Discard their exterior at
        # once instead of partitioning empty space around oblique geometry.
        negative=max(extent)<=TOLERANCE*.1
        positive=min(extent)>=-TOLERANCE*.1
        next_cells=[]
        for cell in cells:
            work+=1
            if work>50000:raise ValueError('BSP conversion work limit reached; simplify the mesh or export a model')
            distances=[dot(n,p)-d for poly in cell for p in poly]
            if min(distances)<-EPS and max(distances)>EPS:
                if not positive:next_cells.append(_clip(cell,n,d))
                if not negative:next_cells.append(_clip(cell,tuple(-x for x in n),-d))
            elif not (negative and min(distances)>EPS or positive and max(distances)<-EPS):next_cells.append(cell)
            if len(next_cells)>max_cells:raise ValueError(f'BSP conversion exceeds {max_cells} cells; simplify the mesh or export a model')
        cells=next_cells
    parts=[]
    for cell in cells:
        vs,fs=_indexed(cell);center=tuple(sum(p[i] for p in vs)/len(vs) for i in range(3))
        if _inside(center,triangles):validate(vs,fs);parts.append((vs,fs))
    expected=abs(sum(dot(sub(a,vertices[0]),cross(sub(b,vertices[0]),sub(c,vertices[0])))/6 for a,b,c in triangles))
    actual=sum(volume(v,f) for v,f in parts)
    if not parts or expected<=EPS or abs(actual-expected)>max(1e-5,expected*1e-5):
        raise ValueError('BSP conversion failed volume conservation; the preview was preserved')
    return parts
