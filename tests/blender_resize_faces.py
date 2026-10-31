import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,bmesh
from wavelength.source.resize_gizmo import _boundary_vertices
for triangulate in (False,True):
 bm=bmesh.new();bmesh.ops.create_cube(bm,size=2)
 # A planar sloped top: only two corners are at the coordinate maximum.
 for v in bm.verts:
  if v.co.z>0:v.co.z+=.3*v.co.x+.2*v.co.y
 if triangulate:bmesh.ops.triangulate(bm,faces=list(bm.faces))
 bm.verts.index_update()
 side=_boundary_vertices(bm,2,1)
 assert len(side)==4,(triangulate,side)
 before={v.index:v.co.copy() for v in bm.verts}
 for v in bm.verts:
  if v.index in side:v.co.z+=.5
 for v in bm.verts:
  assert abs(v.co.z-before[v.index].z-(.5 if v.index in side else 0))<1e-6
 assert all(len(e.link_faces)==2 for e in bm.edges)
 bm.normal_update()
 assert all(max(abs((v.co-f.verts[0].co).dot(f.normal)) for v in f.verts)<1e-5 for f in bm.faces)
 for axis in range(3):
  for sign in (-1,1):assert len(_boundary_vertices(bm,axis,sign))==4
 bm.free()
print('PASS whole boundary faces: sloped cube, triangles, six directions, connected planar faces, opposite vertices unchanged',flush=True)

