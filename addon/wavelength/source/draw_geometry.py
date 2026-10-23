"""Curve sampling and outline validation independent of Blender."""
import math


def add(a, b): return tuple(x+y for x, y in zip(a, b))
def sub(a, b): return tuple(x-y for x, y in zip(a, b))
def mul(a, k): return tuple(x*k for x in a)
def length(a): return math.sqrt(sum(x*x for x in a))
def cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def sample(a, b, resolution=16):
    """Cubic Bezier segment, including both endpoints."""
    p, q, r, s = a['co'], a['right'], b['left'], b['co']
    return [add(add(mul(p,(1-t)**3),mul(q,3*(1-t)**2*t)),
                add(mul(r,3*(1-t)*t*t),mul(s,t**3))) for t in (i/resolution for i in range(resolution+1))]



def simple_polygon(points, normal):
    """Reject self-intersection before filling/extruding a closed outline."""
    axis=max(range(3),key=lambda i:abs(normal[i]));axes=[i for i in range(3) if i!=axis]
    pts=[(p[axes[0]],p[axes[1]]) for p in points]
    def turn(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    for i in range(len(pts)):
        a,b=pts[i],pts[(i+1)%len(pts)]
        for j in range(i+2,len(pts)):
            if i==0 and j==len(pts)-1:continue
            c,d=pts[j],pts[(j+1)%len(pts)]
            if turn(a,b,c)*turn(a,b,d)<0 and turn(c,d,a)*turn(c,d,b)<0:return False
    return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(pts,pts[1:]+pts[:1])))>1e-8
