"""Regression for the measured Cube Brush.052 Boolean sliver, without user files."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy
from mathutils import Vector,Matrix
from wavelength.source import csg,geometry
v=[(-3520,576,16),(-3520,1024,16),(-3072,1024,16),(-3072,576,16),(-3264,768.434128,816),(-3264,1024,816),(-3520,1024,816),(-3520,768.434278,816),(-3072,576,16.0084),(-3520,576,16.007949)]
f=[[0,1,2,3],[4,5,6,7],[0,3,8,9],[3,2,5,4,8],[2,1,6,5],[1,0,9,7,6],[7,9,8,4]]
unit=.0254
mesh=bpy.data.meshes.new('Measured CSG sliver');obj=bpy.data.objects.new('Regression',mesh)
obj['wl_unit_meters']=unit
obj.matrix_world=Matrix.Translation((-84.693756,20.159645,8.534442))@Matrix.Diagonal((1,1,4.166667,1))
inv=obj.matrix_world.inverted()
mesh.from_pydata([inv@(Vector(p)*unit) for p in v],[],f);mesh.update()
mesh.uv_layers.new(name='UVMap');material=bpy.data.materials.new('Preserved');mesh.materials.append(material)
def validate():
 return geometry.validate([tuple(x/unit for x in obj.matrix_world@p.co) for p in mesh.vertices],[list(p.vertices) for p in mesh.polygons])
try:validate()
except geometry.BrushError as exc:assert exc.code=='NONPLANAR_FACE'
else:raise AssertionError('Fixture must reproduce the failure')
csg.clean_boolean_mesh(mesh,obj)
assert len(mesh.vertices)==8 and len(mesh.polygons)==6
validate();csg._solid(mesh)
assert mesh.uv_layers.get('UVMap') and mesh.materials[0]==material
before=[tuple(p.co) for p in mesh.vertices];csg.clean_boolean_mesh(mesh,obj)
assert before==[tuple(p.co) for p in mesh.vertices]
print('PASS measured CSG sliver, scaled engine-unit cleanup, manifold planar result, materials/UV layers, idempotence',flush=True)
