import sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
from mathutils import Vector,Quaternion
from bpy_extras import view3d_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import terrain,terrain_sew as sew,terrain_paint as paint
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.preferences.view.show_splash=False
folder=Path(__file__).resolve().parents[1]/'build/terrain-sew';folder.mkdir(exist_ok=True)
ctx.preferences.filepaths.temporary_directory=str(folder);ctx.workspace['wl_workspace']=True;ctx.workspace['wl_layout_ready']=True;ctx.scene.wavelength.engine='source_gmod_windows'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
def make(a,b):
    obj=terrain.create_footprint(ctx,Vector(a),Vector(b),Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)));terrain.enable_paint(obj);return obj
left=make((-6,-3,0),(0,3,0));left.name='Sewn left';right=make((0,-3,0),(6,3,0));right.name='Sewn right'
left.select_set(True);right.select_set(True);ctx.view_layer.objects.active=left
assert bpy.ops.wavelength.terrain_sew()=={'FINISHED'}
names=[left.name,right.name]
area=next(a for a in ctx.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW');rv=area.spaces.active.region_3d
rv.view_rotation=Quaternion((1,0,0,0));rv.view_perspective='ORTHO';rv.view_distance=20;rv.view_location=(0,0,0)
steps=[]
def start():
    bpy.ops.ed.undo_push(message='Sewn paint baseline')
    with ctx.temp_override(area=area,region=region):assert bpy.ops.wavelength.terrain_paint('INVOKE_DEFAULT')=={'RUNNING_MODAL'}
    assert len(paint._RUNNING[0].members)==2
steps.append(start)
def send(kind,value='PRESS',x=0,ctrl=False):
    def run():
        xy=view3d_utils.location_3d_to_region_2d(region,rv,Vector((x,0,0)));ctx.window.event_simulate(type=kind,value=value,x=int(region.x+xy.x),y=int(region.y+xy.y),ctrl=ctrl)
    steps.append(run)
send('MOUSEMOVE','NOTHING',-.3);send('LEFTMOUSE',x=-.3);send('MOUSEMOVE','NOTHING',.3);steps.extend([lambda:None]*2);send('LEFTMOUSE','RELEASE',.3);send('ESC',x=.3)
def check():
    assert not paint._RUNNING
    for name in names:
        obj=ctx.scene.objects[name];assert max(d.vector.length for d in obj.data.attributes['wl_terrain_vector'].data)>.01
    sew.validate_export(ctx.scene.objects[names[0]])
    bpy.ops.screen.screenshot(filepath=str(folder/'sewn-paint-ui.png'))
    print('PASS real mouse painting crosses separate objects and holds the seam together',flush=True)
steps.append(check);send('Z',ctrl=True)
def check_undo():
    for name in names:
        obj=ctx.scene.objects[name];assert max(d.vector.length for d in obj.data.attributes['wl_terrain_vector'].data)<1e-5
    assert len(sew.network(ctx.scene.objects[names[0]]))==2
    print('PASS native paint undo restores both sewn surfaces while preserving their connection',flush=True)
    bpy.ops.wm.quit_blender()
steps.append(check_undo)
def tick():
    try:
        if steps:steps.pop(0)()
        return .25 if steps else None
    except Exception:traceback.print_exc();print('FAIL SEWN PAINT UI',flush=True);bpy.ops.wm.quit_blender()
bpy.app.timers.register(tick,first_interval=2)
