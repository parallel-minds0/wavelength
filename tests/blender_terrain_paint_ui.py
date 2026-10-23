import sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
from mathutils import Vector,Quaternion
from bpy_extras import view3d_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import terrain,terrain_paint
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.preferences.view.show_splash=False
folder=Path(__file__).resolve().parents[1]/'build/terrain';folder.mkdir(exist_ok=True)
ctx.preferences.filepaths.temporary_directory=str(folder);ctx.workspace['wl_workspace']=True;ctx.workspace['wl_layout_ready']=True
ctx.scene.wavelength.engine='blender';bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
obj=terrain.create(ctx,paintable_surface=True);obj.wavelength_terrain.amplitude=0;name=obj.name
area=next(a for a in ctx.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW');rv=area.spaces.active.region_3d
rv.view_rotation=Quaternion((1,0,0,0));rv.view_perspective='ORTHO';rv.view_distance=24;rv.view_location=(0,0,0)
steps=[]
def start():
    bpy.ops.ed.undo_push(message='Terrain paint baseline')
    with ctx.temp_override(area=area,region=region):bpy.ops.wavelength.terrain_paint('INVOKE_DEFAULT')
steps.append(start)
def send(kind,value='PRESS',co=(0,0,0),ctrl=False):
    def run():
        xy=view3d_utils.location_3d_to_region_2d(region,rv,Vector(co));ctx.window.event_simulate(type=kind,value=value,x=int(region.x+xy.x),y=int(region.y+xy.y),ctrl=ctrl)
    steps.append(run)
send('MOUSEMOVE','NOTHING');send('LEFTMOUSE');send('MOUSEMOVE','NOTHING',(.5,0,0));send('MOUSEMOVE','NOTHING',(1,0,0));send('LEFTMOUSE','RELEASE',(1,0,0));send('ESC')
def check():
    assert not terrain_paint._RUNNING
    assert max(v.co.z for v in ctx.scene.objects[name].data.vertices)>0
    print('PASS real mouse height paint and clean brush exit',flush=True)
steps.append(check)
send('Z',ctrl=True)
def check_undo():
    assert max(abs(v.co.z) for v in ctx.scene.objects[name].data.vertices)<1e-6
    print('PASS terrain paint native undo',flush=True)
    obj=ctx.scene.objects[name];obj.wavelength_terrain.paint_mode='TEXTURE'
    mat=bpy.data.materials.new('Paint layer');mat.diffuse_color=(0,1,0,1);obj.wavelength_terrain.paint_material=mat
    with ctx.temp_override(area=area,region=region):bpy.ops.wavelength.terrain_paint('INVOKE_DEFAULT')
steps.append(check_undo)
send('MOUSEMOVE','NOTHING');send('LEFTMOUSE');send('MOUSEMOVE','NOTHING',(.5,0,0));send('LEFTMOUSE','RELEASE',(.5,0,0));send('ESC')
def finish():
    assert max(x.value for x in ctx.scene.objects[name].data.attributes['wl_terrain_blend'].data)>0
    assert not terrain_paint._RUNNING
    bpy.ops.screen.screenshot(filepath=str(folder/'terrain-paint-ui.png'))
    print('PASS real mouse texture blend paint',flush=True);bpy.ops.wm.quit_blender()
steps.append(finish)
def tick():
    try:
        if steps:steps.pop(0)()
        return .2 if steps else None
    except Exception:traceback.print_exc();print('FAIL TERRAIN PAINT UI',flush=True);bpy.ops.wm.quit_blender()
bpy.app.timers.register(tick,first_interval=2)
