"""Visible duplicates, automatic failure capture, native selection and live repair."""
import sys,traceback,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils,bmesh
from mathutils import Vector
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import geometry_debug as debug,scene,diagnostics
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.preferences.view.show_splash=False
ctx.workspace['wl_workspace']=True;ctx.workspace['wl_layout_ready']=True
ctx.scene.wavelength.engine='source_hl2_windows'
obj=ctx.object;obj.name='Cube Brush.007';old=obj.data
v=[tuple(v.co) for v in old.vertices];f=[list(p.vertices) for p in old.polygons]
mesh=bpy.data.meshes.new('Coincident fixture');mesh.from_pydata(v+[v[0]],[],f);mesh.update();obj.data=mesh;scene.mark_brush(obj)
area=next(a for a in ctx.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
folder=Path(__file__).resolve().parents[1]/'build/geometry-debug';folder.mkdir(exist_ok=True)
steps=[]
def setup():
 try:scene.export_map(ctx.scene)
 except Exception as error:
  assert error.code=='DUPLICATE_VERTEX' and error.object_name==obj.name
  diagnostics.error('Test geometry failure',error)
 else:raise AssertionError('Invalid cube exported')
 debug.tick();state=ctx.scene.wavelength_geometry_debug
 assert len(state.issues)==1 and state.issues[0].target==obj
 assert json.loads(state.issues[0].details)['vertices']==[0,8]
 area.spaces.active.show_region_ui=True
 print('PASS automatic export-failure capture locates exact coincident vertices',flush=True)
steps.append(setup)
def open_panel():
 region_ui=next(r for r in area.regions if r.type=='UI');region_ui.active_panel_category='wavelength'
steps.append(open_panel)
def capture():
 bpy.ops.screen.screenshot(filepath=str(folder/'coincident-vertices.png'))
 assert bpy.ops.wavelength.select_geometry_problem()=={'FINISHED'}
 bm=bmesh.from_edit_mesh(obj.data);assert sum(v.select for v in bm.verts)==2
 print('PASS native Edit Mode selects only the problem vertices',flush=True)
 bpy.ops.mesh.remove_doubles(threshold=.000001);ctx.view_layer.update()
steps.append(capture)
def repair():
 debug.tick();assert not ctx.scene.wavelength_geometry_debug.issues,'Stale issue after native merge'
 assert len(bmesh.from_edit_mesh(obj.data).verts)==8
 print('PASS live diagnostics clear after native Merge by Distance',flush=True)
 bpy.ops.object.mode_set(mode='OBJECT')
 # Missing face produces boundary markers, not an object-wide guess.
 data=bpy.data.meshes.new('Open fixture');data.from_pydata(v,[],f[1:]);obj.data=data;scene.mark_brush(obj)
 debug.scan(ctx.scene);issue=ctx.scene.wavelength_geometry_debug.issues[0]
 assert issue.code=='NONMANIFOLD' and len(json.loads(issue.details)['edges'])==4
 # Evaluated indices must not be applied to a different base mesh.
 tree=bpy.data.node_groups.new('Bad evaluated cube','GeometryNodeTree');tree.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
 cube=tree.nodes.new('GeometryNodeMeshCube');cube.inputs['Size'].default_value=(0,2,2)
 output=tree.nodes.new('NodeGroupOutput');tree.links.new(cube.outputs['Mesh'],output.inputs['Geometry'])
 modifier=obj.modifiers.new('Evaluated failure','NODES');modifier.node_group=tree;ctx.view_layer.update()
 debug.scan(ctx.scene);assert ctx.scene.wavelength_geometry_debug.issues[0].evaluated
 bpy.ops.wavelength.select_geometry_problem();assert ctx.mode=='OBJECT'
 print('PASS evaluated-node problems do not select unrelated base-mesh indices',flush=True)
 ctx.scene.wavelength.engine='blender';debug.scan(ctx.scene)
 assert not ctx.scene.wavelength_geometry_debug.issues
 print('PASS boundary edges and profile-aware BSP validation',flush=True)
 addon_utils.disable('wavelength',default_set=False);assert not debug._handles
 addon_utils.enable('wavelength',default_set=False);assert len(debug._handles)==2
 print('PASS GEOMETRY DEBUG lifecycle',flush=True);bpy.ops.wm.quit_blender()
steps.append(repair)
def tick():
 try:
  with ctx.temp_override(area=area,region=region):
   if steps:steps.pop(0)();return .7
 except Exception:traceback.print_exc();print('FAIL GEOMETRY DEBUG',flush=True);bpy.ops.wm.quit_blender()
bpy.app.timers.register(tick,first_interval=2)
