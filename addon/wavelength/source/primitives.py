"""Editable BSP primitives. Dimensions are engine units; each part is convex."""
from math import sin, cos, pi
from .geometry import validate

BOX_FACES=((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))

def box(x0,y0,z0,x1,y1,z1):
    return [(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)],list(BOX_FACES)


def generate(kind, p):
    parts=[]
    if kind=='STAIRS':
        count=int(p['steps']);rise=float(p['rise']);run=float(p['run']);width=float(p['width']);landing=float(p.get('landing',0))
        if not 1<=count<=64 or min(rise,run,width)<1 or landing<0:raise ValueError('Stairs require 1–64 steps and positive map-unit dimensions')
        for i in range(count):parts.append(box(-width/2,i*run,0,width/2,(i+1)*run,(i+1)*rise))
        if landing:parts.append(box(-width/2,count*run,0,width/2,count*run+landing,count*rise))
    elif kind=='ARCH':
        radius=float(p['radius']);thick=float(p['thickness']);depth=float(p['depth']);angle=float(p['angle'])*pi/180;segments=int(p['segments'])
        if not 3<=segments<=64 or not 0<thick<radius or depth<1 or not 0<angle<=2*pi or angle/segments>=pi:raise ValueError('Arch requires positive radius, thickness below radius, depth, and 3–64 segments')
        inner=radius-thick
        for i in range(segments):
            a=pi/2-angle/2+angle*i/segments;b=a+angle/segments
            ring=[(r*cos(t),0,r*sin(t)) for r,t in ((inner,a),(radius,a),(radius,b),(inner,b))]
            # Extrusion is -Y so polygon orientation follows the XZ plane.
            verts=ring+[(x,-depth,z) for x,y,z in ring]
            parts.append((verts,list(BOX_FACES)))
    elif kind=='SPHERE':
        radius=float(p['radius']);detail=int(p.get('subdivisions',1))
        if radius<1 or detail not in (0,1):raise ValueError('Sphere supports 20 or 80 triangular faces (detail 0 or 1)')
        from math import sqrt
        t=(1+sqrt(5))/2
        verts=[(-1,t,0),(1,t,0),(-1,-t,0),(1,-t,0),(0,-1,t),(0,1,t),(0,-1,-t),(0,1,-t),(t,0,-1),(t,0,1),(-t,0,-1),(-t,0,1)]
        def normalized(v):
            d=sqrt(sum(c*c for c in v));return tuple(c/d for c in v)
        verts=[normalized(v) for v in verts]
        faces=[(0,11,5),(0,5,1),(0,1,7),(0,7,10),(0,10,11),(1,5,9),(5,11,4),(11,10,2),(10,7,6),(7,1,8),(3,9,4),(3,4,2),(3,2,6),(3,6,8),(3,8,9),(4,9,5),(2,4,11),(6,2,10),(8,6,7),(9,8,1)]
        if detail:
            cache={};refined=[]
            def midpoint(a,b):
                key=tuple(sorted((a,b)))
                if key not in cache:
                    cache[key]=len(verts);verts.append(normalized(tuple((x+y)/2 for x,y in zip(verts[a],verts[b]))))
                return cache[key]
            for a,b,c in faces:
                ab,bc,ca=midpoint(a,b),midpoint(b,c),midpoint(c,a)
                refined.extend(((a,ab,ca),(b,bc,ab),(c,ca,bc),(ab,bc,ca)))
            faces=refined
        parts=[([tuple(c*radius for c in v) for v in verts],faces)]
    else:raise ValueError('Unknown primitive')
    rotation=float(p.get('direction',0))*pi/180
    result=[]
    for verts,faces in parts:
        verts=[(x*cos(rotation)-y*sin(rotation),x*sin(rotation)+y*cos(rotation),z) for x,y,z in verts]
        if any(abs(c)>32768 for v in verts for c in v):raise ValueError('Primitive exceeds the supported map coordinate range')
        validate(verts,[list(f) for f in faces]);result.append((verts,faces))
    return result
