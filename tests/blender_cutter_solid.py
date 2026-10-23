import sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils,bmesh
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import pencil
bpy.context.preferences.use_preferences_save=False
ctx=bpy.context;ctx.workspace['wl_workspace']=True;ctx.scene.wavelength.engine='blender'
def cube():
    if ctx.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.mesh.primitive_cube_add();return ctx.object

def volume(obj):
    bm=bmesh.new();bm.from_mesh(obj.data);assert all(e.is_manifold for e in bm.edges)
    v=abs(bm.calc_volume());bm.free();return v
ctx.scene.wavelength_draw.separate_objects=False  # Retain coverage of the optional combined result.
for closed,op,through in [(False,'SPLIT',True),(True,'SPLIT',True),(True,'SUBTRACT',True),(True,'SUBTRACT',False)]:
    target=cube();original=target.data
    coords=[(-2,0,1),(2,0,1)] if not closed else [(-.5,-.5,1),(.5,-.5,1),(.5,.5,1),(-.5,.5,1)]
    root=pencil.create_guide(ctx,[pencil.point(p) for p in coords],(0,0,1),closed,target)
    root.wavelength_cutter.operation=op;root.wavelength_cutter.through=through;root.wavelength_cutter.depth=.5
    pieces=pencil.apply_cut(ctx,root)
    expected=8 if op=='SPLIT' else (6 if through else 7.5)
    assert abs(volume(target)-expected)<1e-4,(closed,op,through,volume(target))
    if op=='SPLIT':assert not pieces and len(ctx.selected_objects)==1
    if op=='SPLIT':assert abs(volume(target)+sum(volume(o) for o in pieces)-8)<1e-4
    print('PASS capped solid',closed,op,through,flush=True)
target=cube();original=target.data
linked=bpy.data.objects.new('Linked',original);ctx.collection.objects.link(linked)
a,b=map(pencil.point,[(-2,0,1),(2,0,1)]);a['right']=[-1,.8,1];b['left']=[1,.8,1]
root=pencil.create_guide(ctx,[a,b],(0,0,1),False,target);root.wavelength_cutter.operation='SPLIT'
pieces=pencil.apply_cut(ctx,root)
assert abs(volume(target)-8)<1e-4
assert linked.data==original and len(original.polygons)==6
assert target.data.uv_layers and len(target.data.uv_layers[0].data)==len(target.data.loops)
print('PASS curved solid split, linked mesh isolation, UV preservation',flush=True)
root.wavelength_cutter.operation='SUBTRACT';before=target.data
try:pencil.apply_cut(ctx,root)
except ValueError:pass
else:raise AssertionError('Open subtraction accepted')
assert target.data==before and ctx.object==target
assert not any(o.name.startswith(('.Cutter Work','.Cutter Volume')) for o in ctx.scene.objects)
print('PASS invalid operation rollback and temporary geometry cleanup',flush=True)
print('PASS SOLID CUTTER',flush=True)

for axis,coords in [('X',[(1,-2,0),(1,2,0)]),('Y',[(-2,1,0),(2,1,0)]),('Z',[(-2,0,1),(2,0,1)])]:
    target=cube();root=pencil.create_guide(ctx,[pencil.point(p) for p in coords],(0,0,1),False,target)
    st=root.wavelength_cutter;st.operation='SPLIT';st.direction=axis
    pieces=pencil.apply_cut(ctx,root);assert not pieces and abs(volume(target)-8)<1e-4
    print('PASS directional clipping',axis,flush=True)
target=cube();root=pencil.create_guide(ctx,[pencil.point(p) for p in [(-2,0,1),(2,0,1)]],(0,0,1),False,target)
st=root.wavelength_cutter;st.operation='SPLIT';st.direction='Z';st.through=False;st.depth=.5
pieces=pencil.apply_cut(ctx,root);assert abs(volume(target)-8)<1e-4
print('PASS finite-depth open clipping',flush=True)

for keep in ['INSIDE','OUTSIDE']:
    target=cube();root=pencil.create_guide(ctx,[pencil.point(p) for p in [(-2,0,1),(2,0,1)]],(0,0,1),False,target)
    st=root.wavelength_cutter;st.operation='SPLIT';st.keep=keep
    pieces=pencil.apply_cut(ctx,root);assert not pieces and abs(volume(target)-4)<1e-4
    print('PASS clipping keep side',keep,flush=True)

root=pencil.create_guide(ctx,[pencil.point(p) for p in [(0,0,0),(2,0,0),(2,2,0),(0,2,0)]],(0,0,1),True)
before_meshes={o.name for o in ctx.scene.objects if o.type=='MESH'}
result=pencil.create_geometry(ctx,root,'EXTRUDE',1)
assert {o.name for o in ctx.scene.objects if o.type=='MESH'}-before_meshes=={result.name}
assert abs(volume(result)-4)<1e-4 and result.modifiers
from wavelength.source import node_pencil
node_pencil.finalize(result)
assert not result.modifiers and abs(volume(result)-4)<1e-4
print('PASS extrusion creates one capped mesh object',flush=True)
