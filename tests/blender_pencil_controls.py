"""Real mouse/key regression for the guide-first line/curve cutter."""
import sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
from mathutils import Vector,Quaternion
from bpy_extras import view3d_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import pencil
bpy.context.preferences.use_preferences_save=False;bpy.context.preferences.view.show_splash=False
folder=Path(__file__).resolve().parents[1]/'build/cutter';folder.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.temporary_directory=str(folder)
bpy.context.workspace['wl_workspace']=True;bpy.context.workspace['wl_layout_ready']=True
bpy.context.scene.wavelength_draw.auto_extrude=False
bpy.context.scene.wavelength_draw.separate_objects=False
bpy.context.scene.wavelength.engine='blender';bpy.context.scene.tool_settings.use_snap=False
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add();target=bpy.context.object;target.name='Cutter Test Target';target.scale=(4,4,.5)
target_name=target.name
window=bpy.context.window;area=next(a for a in window.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
space=area.spaces.active;space.show_region_ui=False;space.region_3d.view_rotation=Quaternion((1,0,0,0));space.region_3d.view_perspective='ORTHO';space.region_3d.view_location=(0,0,0);space.region_3d.view_distance=12
with bpy.context.temp_override(area=area,region=region):
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.wm.tool_set_by_id(name='wavelength.pencil_edit_tool')
steps=[];state={}
def send(kind,value='PRESS',point=None,unicode=None,ctrl=False):
    def step():
        with bpy.context.temp_override(area=area,region=region):
            xy=view3d_utils.location_3d_to_region_2d(region,space.region_3d,Vector(point or (0,0,.5)))
            args=dict(type=kind,value=value,x=int(region.x+xy.x),y=int(region.y+xy.y),ctrl=ctrl)
            if unicode is not None:args['unicode']=unicode
            window.event_simulate(**args)
    steps.append(step)
def click(point):
    send('MOUSEMOVE','NOTHING',point);send('LEFTMOUSE',point=point);send('LEFTMOUSE','RELEASE',point)
click((-3,-2,.5))
send('MOUSEMOVE','NOTHING',(-1,-2,.5));send('LEFTMOUSE',point=(-1,-2,.5));send('MOUSEMOVE','NOTHING',(-.5,-1.5,.5));send('LEFTMOUSE','RELEASE',(-.5,-1.5,.5))
click((-1,1,.5));send('RET',point=(-1,1,.5))
def check_open():
    roots=[o for o in bpy.context.scene.objects if pencil.is_guide(o)];assert len(roots)==1
    root=roots[0];assert not root.data.splines[0].use_cyclic_u
    assert all(abs((root.matrix_world@p.co).z-.5)<1e-4 for p in root.data.splines[0].bezier_points)
    assert bpy.context.workspace.tools.from_space_view3d_mode('OBJECT').idname=='wavelength.pencil_tool'
    assert (root.data.splines[0].bezier_points[1].handle_right-root.data.splines[0].bezier_points[1].co).length>.1
    assert len(bpy.data.objects[target_name].data.polygons)==6
    assert not root.children and not root.modifiers
    print('PASS click corners, drag curved handles, Enter open; target unchanged',flush=True)
steps.append(check_open)
for p in [(1,-1,.5),(3,-1,.5),(3,1,.5),(1,1,.5)]:click(p)
click((1,-1,.5))
def check_closed():
    roots=[o for o in bpy.context.scene.objects if pencil.is_guide(o)];assert len(roots)==2
    root=next(o for o in roots if o.data.splines[0].use_cyclic_u);state['closed']=root.name
    assert root.wavelength_cutter.target==bpy.data.objects[target_name]
    assert len([o for o in bpy.context.scene.objects if o.type=='MESH'])==1
    assert len(bpy.data.objects[target_name].data.polygons)==6 and bpy.context.mode=='OBJECT'
    assert not pencil._drawing
    print('PASS closing creates only a guide; no cut or automatic extrusion',flush=True)
steps.append(check_closed)
send('K',point=(2,0,.5))
def check_cut():
    obj=bpy.data.objects[target_name];obj.update_from_editmode()
    assert len(obj.data.polygons)>6 and bpy.context.mode=='EDIT_MESH'
    assert pencil.is_guide(bpy.data.objects[state['closed']])
    print('PASS K explicitly applies native knife cut',flush=True)
steps.append(check_cut)
send('Z',point=(2,0,.5),ctrl=True)
def check_undo():
    obj=bpy.data.objects[target_name]
    if bpy.context.mode=='EDIT_MESH':obj.update_from_editmode()
    assert len(obj.data.polygons)==6,len(obj.data.polygons)
    assert pencil.is_guide(bpy.data.objects[state['closed']])
    print('PASS Ctrl+Z restores mesh while keeping guide',flush=True)
    if bpy.context.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
    root=bpy.data.objects[state['closed']];bpy.ops.object.select_all(action='DESELECT');root.select_set(True);bpy.context.view_layer.objects.active=root
    bpy.ops.wavelength.keep_cut_guide();assert bpy.context.object==root
    bpy.ops.wavelength.create_cut_geometry()
    assert len([o for o in bpy.context.scene.objects if o.type=='MESH'])==2
    assert len(bpy.data.objects[target_name].data.polygons)==6
    print('PASS explicit Create Geometry makes a separate face',flush=True)
steps.append(check_undo)
def prepare_solid():
    bpy.ops.object.select_all(action='DESELECT');obj=bpy.data.objects[target_name];obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.context.scene.wavelength_draw.guide=None;bpy.context.scene.wavelength_draw.operation='SPLIT'
    # Scripted fixture creation is outside the event system's automatic undo pushes.
    bpy.ops.ed.undo_push(message='Solid cutter test baseline')
steps.append(prepare_solid)
click((-5,0,.5));click((5,0,.5));send('Z',point=(5,0,.5));send('D',point=(5,0,.5));send('D',point=(5,0,.5));send('K',point=(5,0,.5))
def check_solid():
    import bmesh
    assert bpy.context.mode=='OBJECT'
    selected=list(bpy.context.selected_objects);assert len(selected)==1
    assert len([o for o in bpy.context.scene.objects if o.type=='MESH'])==2
    for obj in selected:
        bm=bmesh.new();bm.from_mesh(obj.data);assert all(e.is_manifold for e in bm.edges);bm.free()
    print('PASS K during drawing splits into capped solids',flush=True)
steps.append(check_solid)
send('Z',point=(0,0,.5),ctrl=True)
def check_solid_undo():
    meshes=[o.name for o in bpy.context.scene.objects if o.type=='MESH']
    assert len(meshes)==2,meshes
    assert len(bpy.data.objects[target_name].data.polygons)==6
    print('PASS solid split native undo',flush=True)
steps.append(check_solid_undo)

def prepare_extrude():
    if bpy.context.mode!='OBJECT':bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT');obj=bpy.data.objects[target_name];obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.context.scene.wavelength_draw.guide=None;bpy.context.scene.wavelength_draw.operation='FACE';bpy.context.scene.wavelength_draw.auto_extrude=True
    with bpy.context.temp_override(area=area,region=region):bpy.ops.wm.tool_set_by_id(name='wavelength.pencil_tool')
    bpy.ops.ed.undo_push(message='Extrusion fixture')
steps.append(prepare_extrude)
for p in [(-2,-1,.5),(0,-1,.5),(0,1,.5)]:click(p)
send('C',point=(0,1,.5))
def check_height_stage():
    assert len(pencil._drawing)==1 and pencil._drawing[0]._extruding
    state['initial_height']=pencil._drawing[0]._height_m
steps.append(check_height_stage)
send('MOUSEMOVE','NOTHING',(0,2,.5))
def check_height_motion():
    assert pencil._drawing[0]._height_m>state['initial_height']
    print('PASS closure starts mouse-driven extrusion preview',flush=True)
steps.append(check_height_motion)
send('LEFTMOUSE',point=(0,2,.5));send('LEFTMOUSE','RELEASE',(0,2,.5))
def check_extrusion():
    import bmesh
    assert not pencil._drawing and bpy.context.object.type=='MESH'
    bm=bmesh.new();bm.from_mesh(bpy.context.object.data);assert all(e.is_manifold for e in bm.edges);assert bm.calc_volume()>0;bm.free()
    assert len([o for o in bpy.context.scene.objects if o.type=='MESH'])==3
    print('PASS click finishes one capped extrusion mesh',flush=True)
steps.append(check_extrusion)
send('Z',point=(0,2,.5),ctrl=True)
def check_extrude_undo():
    assert len([o for o in bpy.context.scene.objects if o.type=='MESH'])==2
    print('PASS interactive extrusion undo',flush=True)
steps.append(check_extrude_undo)

def finish():
    bpy.ops.screen.screenshot(filepath=str(folder/'cutter-controls.png'))
    print('PASS CUTTER GESTURES',flush=True);bpy.ops.wm.quit_blender()
steps.append(finish)
def tick():
    try:
        if steps:steps.pop(0)()
        return .16 if steps else None
    except Exception:traceback.print_exc();print('FAIL CUTTER GESTURES',flush=True);bpy.ops.wm.quit_blender()
bpy.app.timers.register(tick,first_interval=2)
