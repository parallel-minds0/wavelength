import sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
from mathutils import Vector,Quaternion
from bpy_extras import view3d_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import terrain,terrain_paint,brush_create
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.preferences.view.show_splash=False
folder=Path(__file__).resolve().parents[1]/'build/terrain-stages';folder.mkdir(exist_ok=True)
ctx.preferences.filepaths.temporary_directory=str(folder);ctx.workspace['wl_workspace']=True;ctx.workspace['wl_layout_ready']=True
ctx.scene.wavelength.engine='source_gmod_windows'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
area=next(a for a in ctx.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW');rv=area.spaces.active.region_3d
rv.view_rotation=Quaternion((1,0,0,0));rv.view_perspective='ORTHO';rv.view_distance=24;rv.view_location=(0,0,0)
obj=terrain.create_footprint(ctx,Vector((-6,-6,0)),Vector((6,6,0)),Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
assert brush_create.WL_Tool_CreateTerrainBrush in brush_create.TOOLS
ctx.view_layer.update();ev=obj.evaluated_get(ctx.evaluated_depsgraph_get());mesh=ev.to_mesh()
assert len(mesh.vertices)==4 and max(abs(v.co.z) for v in mesh.vertices)<1e-6;ev.to_mesh_clear()
try:terrain.patches(obj)
except ValueError as exc:assert 'paintable' in str(exc)
else:raise AssertionError('Plane silently converted at export')
assert bpy.ops.wavelength.terrain_enable_paint()=={'FINISHED'}
assert terrain.paintable(obj)
name=obj.name;steps=[]
def start():
    bpy.ops.ed.undo_push(message='Displacement baseline')
    with ctx.temp_override(area=area,region=region):assert bpy.ops.wavelength.terrain_paint('INVOKE_DEFAULT')=={'RUNNING_MODAL'}
    assert obj.wavelength_terrain.paint_strength>1
steps.append(start)
def send(kind,value='PRESS'):
    def run():
        xy=view3d_utils.location_3d_to_region_2d(region,rv,Vector((0,0,0)))
        ctx.window.event_simulate(type=kind,value=value,x=int(region.x+xy.x),y=int(region.y+xy.y))
    steps.append(run)
send('MOUSEMOVE','NOTHING');send('LEFTMOUSE')
steps.extend([lambda:None]*4)
send('LEFTMOUSE','RELEASE');send('ESC')
def check():
    assert not terrain_paint._RUNNING
    ctx.view_layer.update();ev=obj.evaluated_get(ctx.evaluated_depsgraph_get());mesh=ev.to_mesh()
    height=max(v.co.z for v in mesh.vertices)/obj['wl_unit_meters'];ev.to_mesh_clear()
    assert height>5,height
    assert max(p[2] for patch in terrain.patches(obj) for p in patch[0])>0
    bpy.ops.screen.screenshot(filepath=str(folder/'paint-visible.png'))
    print('PASS flat four-vertex footprint, explicit displacement conversion, stationary mouse paint visibly deforms evaluated geometry and Source output',height,flush=True)
steps.append(check)
def attached():
    global obj
    import bmesh
    from wavelength.source import scene,primitives,terrain_face
    bpy.data.objects.remove(obj,do_unlink=True)
    vertices,faces=primitives.box(-256,-256,-32,256,256,0)
    mesh=bpy.data.meshes.new('Source cube');mesh.from_pydata([[x*.0254 for x in v] for v in vertices],[],faces);mesh.update()
    source=bpy.data.objects.new('Source cube',mesh);ctx.collection.objects.link(source);scene.mark_brush(source)
    source.select_set(True);ctx.view_layer.objects.active=source;bpy.ops.object.mode_set(mode='EDIT');bm=bmesh.from_edit_mesh(mesh)
    for f in bm.faces:f.select_set(False)
    max(bm.faces,key=lambda f:f.normal.z).select_set(True);bmesh.update_edit_mesh(mesh)
    obj=terrain_face.create(ctx)
steps.extend([attached,start])
send('MOUSEMOVE','NOTHING');send('LEFTMOUSE');steps.extend([lambda:None]*4);send('LEFTMOUSE','RELEASE');send('ESC')
steps.append(check)
def finish():
    print('PASS real stationary Source brush-face displacement painting visibly updates its evaluated surface',flush=True)
    bpy.ops.wm.quit_blender()
steps.append(finish)
def tick():
    try:
        if steps:steps.pop(0)()
        return .2 if steps else None
    except Exception:traceback.print_exc();print('FAIL TERRAIN STAGES',flush=True);bpy.ops.wm.quit_blender()
bpy.app.timers.register(tick,first_interval=2)
