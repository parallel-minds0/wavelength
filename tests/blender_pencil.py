"""Background regression: guide-first cutter and explicit geometry creation."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
from mathutils import Vector
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import pencil
assert hasattr(bpy.context.scene,'wavelength_draw')
bpy.context.workspace['wl_workspace']=True
ctx=bpy.context
cube=ctx.object;original=cube.data;before=(len(original.vertices),len(original.edges),len(original.polygons))
pts=[pencil.point((-1,-1,1)),pencil.point((1,-1,1)),pencil.point((1,1,1)),pencil.point((-1,1,1))]
root=pencil.create_guide(ctx,pts,(0,0,1),True,cube)
assert root.wavelength_cutter.target==cube
assert root.type=='CURVE' and len(root.children)==0 and not root.modifiers
assert cube.data==original and before==(len(original.vertices),len(original.edges),len(original.polygons))
assert root.data.splines[0].use_cyclic_u
face=pencil.create_geometry(ctx,root,'FACE');assert len(face.data.polygons)==1
solid=pencil.create_geometry(ctx,root,'EXTRUDE',2)
assert len(solid.data.polygons)==6 and abs(solid.dimensions.z-2)<1e-5,(len(solid.data.polygons),solid.dimensions[:],[tuple(v.co) for v in solid.data.vertices])
assert cube.data==original
open_guide=pencil.create_guide(ctx,[pencil.point((0,0,0)),pencil.point((2,0,0))],(0,0,1),False,cube)
edges=pencil.create_geometry(ctx,open_guide,'EDGES');assert len(edges.data.edges)==1 and len(edges.data.polygons)==0
wall=pencil.create_geometry(ctx,open_guide,'EXTRUDE',1);assert len(wall.data.polygons)==1
try:pencil.create_geometry(ctx,open_guide,'FACE')
except ValueError:pass
else:raise AssertionError('Open guide filled without closure')
a,b=map(pencil.point,[(0,0,0),(2,0,0)]);a['right']=[.5,1,0];b['left']=[1.5,1,0]
curved=pencil.create_guide(ctx,[a,b],(0,0,1),False,cube)
values,closed=pencil.sampled(curved);assert len(values)>2 and max(p.y for p in values)>.5
bpy.ops.wavelength.keep_cut_guide();assert ctx.object==curved
assert cube.data==original
# Actions consume current Curve Edit Mode coordinates, not stale object data.
bpy.ops.object.select_all(action='DESELECT');root.select_set(True);ctx.view_layer.objects.active=root
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.curve.select_all(action='SELECT')
bpy.ops.transform.translate(value=(0,0,2))
updated=pencil.create_geometry(ctx,root,'FACE')
assert all(abs(v.co.z-3)<1e-5 for v in updated.data.vertices)
for field in ('spacing','spread','output','power','instance','density'):
    assert not hasattr(ctx.scene.wavelength_draw,field),field
addon_utils.disable('wavelength',default_set=False);addon_utils.enable('wavelength',default_set=False)
assert hasattr(ctx.scene,'wavelength_draw');addon_utils.disable('wavelength',default_set=False)
print('PASS guide-first drawing, explicit edges/face/extrusion, curved sampling, retired controls absent, restricted enable/reload',flush=True)
