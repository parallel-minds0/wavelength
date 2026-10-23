import sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
from mathutils import Vector,Quaternion
from bpy_extras import view3d_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import terrain,brush_create
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.preferences.view.show_splash=False
folder=Path(__file__).resolve().parents[1]/'build/terrain-stages';folder.mkdir(exist_ok=True)
ctx.preferences.filepaths.temporary_directory=str(folder);ctx.workspace['wl_workspace']=True;ctx.workspace['wl_layout_ready']=True;ctx.scene.wavelength.engine='source_gmod_windows'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
area=next(a for a in ctx.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW');rv=area.spaces.active.region_3d
rv.view_rotation=Quaternion((1,0,0,0));rv.view_perspective='ORTHO';rv.view_distance=24;rv.view_location=(0,0,0)
with ctx.temp_override(area=area,region=region):bpy.ops.wm.tool_set_by_id(name=brush_create.WL_Tool_CreateTerrainBrush.bl_idname)
steps=[]
def send(kind,value,point):
    def run():
        xy=view3d_utils.location_3d_to_region_2d(region,rv,Vector(point));ctx.window.event_simulate(type=kind,value=value,x=int(region.x+xy.x),y=int(region.y+xy.y))
    steps.append(run)
send('MOUSEMOVE','NOTHING',(-3,-3,0));send('LEFTMOUSE','PRESS',(-3,-3,0));send('LEFTMOUSE','RELEASE',(-3,-3,0));send('MOUSEMOVE','NOTHING',(3,3,0));send('LEFTMOUSE','PRESS',(3,3,0));send('LEFTMOUSE','RELEASE',(3,3,0))
def check():
    obj=ctx.object;assert obj and obj.get('wl_terrain') and not terrain.paintable(obj)
    ctx.view_layer.update();ev=obj.evaluated_get(ctx.evaluated_depsgraph_get());mesh=ev.to_mesh();assert len(mesh.vertices)==4;ev.to_mesh_clear()
    assert obj.wavelength_terrain.amplitude==0
    bpy.ops.screen.screenshot(filepath=str(folder/'terrain-plane-tool.png'))
    print('PASS terrain in primitive tool group, real two-click flat footprint placement without height phase',flush=True)
    bpy.ops.wm.quit_blender()
steps.append(check)
def tick():
    try:
        if steps:steps.pop(0)()
        return .2 if steps else None
    except Exception:traceback.print_exc();print('FAIL TERRAIN TOOL',flush=True);bpy.ops.wm.quit_blender()
bpy.app.timers.register(tick,first_interval=2)
