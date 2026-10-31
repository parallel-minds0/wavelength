import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy
from mathutils import Matrix,Vector
from wavelength.source.resize_gizmo import _handle_matrix
for scales in ((1,1,1),(.01,300,8),(-40,2,.2)):
 matrix=Matrix.Translation((7,8,9))@Matrix.Rotation(.7,4,'Z')@Matrix.Diagonal((*scales,1))
 for axis in range(3):
  for sign in (-1,1):
   point=Vector((1,2,3));direction=Vector(tuple(sign if i==axis else 0 for i in range(3)))
   handle=_handle_matrix(matrix,point,direction)
   assert (handle.translation-matrix@point).length<1e-5
   assert all(abs(handle.to_3x3().col[i].length-1)<1e-5 for i in range(3))
   assert handle.to_3x3().col[2].dot((matrix.to_3x3()@direction).normalized())>.99999
print('PASS fixed-size handle matrices: boundary positions/directions preserved under rotated, nonuniform and mirrored object scales',flush=True)
