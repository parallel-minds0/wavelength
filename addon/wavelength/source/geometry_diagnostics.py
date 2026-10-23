"""Locate the mesh elements responsible for the convex validator's first error."""
from collections import defaultdict
from . import geometry as g

HINTS={
 'DUPLICATE_VERTEX':'Merge unintended duplicates by distance, or separate touching solids.',
 'LOOSE_VERTEX':'Delete unused vertices, or connect them to the solid.',
 'NONMANIFOLD':'Close boundary edges; remove internal faces or inconsistent winding.',
 'NONPLANAR_FACE':'Flatten the marked face or split it into planar faces.',
 'NONCONVEX':'Split the shape into convex brushes for this profile.',
 'DUPLICATE_PLANE':'Dissolve coplanar face boundaries.',
 'ZERO_VOLUME':'Give the solid thickness.',
 'DEGENERATE_FACE':'Remove collapsed faces or rebuild their corners.',
 'EMPTY_OR_DEGENERATE':'A brush must be a closed solid with at least four faces.',
 'NONFINITE_COORDINATE':'Replace invalid vertex coordinates.'}

def problem(vertices,faces):
    """Use the export validator and its exact tolerance; never guess a merge radius."""
    try:g.validate(vertices,faces)
    except g.BrushError as error:
        code=error.code;vs=set();es=[];fs=[]
        if code=='DUPLICATE_VERTEX':
            groups=defaultdict(list)
            for i,v in enumerate(vertices):groups[tuple(v)].append(i)
            vs={i for ids in groups.values() if len(ids)>1 for i in ids}
        elif code=='LOOSE_VERTEX':vs=set(range(len(vertices)))-{i for face in faces for i in face}
        elif code=='NONFINITE_COORDINATE':vs={i for i,v in enumerate(vertices) if any(not g.math.isfinite(c) for c in v)}
        elif code=='NONMANIFOLD':
            links=defaultdict(list)
            for face in faces:
                for a,b in zip(face,face[1:]+face[:1]):links[tuple(sorted((a,b)))].append((a,b))
            es=[edge for edge,uses in links.items() if len(uses)!=2 or uses[0]!=uses[1][::-1]]
        elif code in {'NONPLANAR_FACE','NONCONVEX','DUPLICATE_PLANE','ZERO_VOLUME','DEGENERATE_FACE'}:
            center=tuple(sum(v[i] for v in vertices)/max(1,len(vertices)) for i in range(3));planes=[]
            for index,face in enumerate(faces):
                if len(face)<3 or len(set(face))!=len(face):fs.append(index);continue
                try:_,n,d=g.face_plane(vertices,face)
                except g.BrushError:
                    if code=='DEGENERATE_FACE':fs.append(index)
                    continue
                if g.dot(n,center)>d:n,d=tuple(-c for c in n),-d
                if code=='NONPLANAR_FACE' and any(abs(g.dot(n,vertices[i])-d)>g.TOLERANCE for i in face):fs.append(index)
                if code=='NONCONVEX' and any(g.dot(n,v)-d>g.TOLERANCE for v in vertices):fs.append(index)
                if code=='ZERO_VOLUME' and d-g.dot(n,center)<=g.TOLERANCE:fs.append(index)
                if code=='DUPLICATE_PLANE':
                    for prior,pn,pd in planes:
                        if g.length(g.sub(n,pn))<g.TOLERANCE and abs(d-pd)<g.TOLERANCE:fs.extend((prior,index))
                planes.append((index,n,d))
        else:vs=set(range(len(vertices)))
        fs=sorted(set(fs));vs.update(i for f in fs for i in faces[f]);vs.update(i for edge in es for i in edge)
        return dict(code=code,message=str(error),vertices=sorted(vs),edges=es,faces=fs,hint=HINTS.get(code,'Inspect the marked geometry.'))
    return None
