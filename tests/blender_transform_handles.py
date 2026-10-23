"""Real native toolbar/keyboard routing and workspace restoration, no keymap edits."""
import sys,traceback,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
from mathutils import Vector
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import transform_bridge as bridge,profiles
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.preferences.view.show_splash=False
ctx.workspace['wl_workspace']=True;ctx.workspace['wl_layout_ready']=True
ctx.scene.wavelength.engine='source_hl2_windows';ctx.scene.wavelength.grid_mode='ENGINE';ctx.scene.tool_settings.use_snap=False
area=next(a for a in ctx.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW');window=ctx.window
obj=ctx.object;obj.location=(0,0,0)
from bpy_extras import view3d_utils as view
from mathutils import Quaternion
state={};steps=[]
original=bridge.WL_GGT_native_transform.draw_prepare
def track(self,context):
    original(self,context);state['group']=self
bridge.WL_GGT_native_transform.draw_prepare=track
rv=area.spaces.active.region_3d;rv.view_rotation=Quaternion((1,0,0,0));rv.view_perspective='ORTHO';rv.view_distance=8
ctx.scene.tool_settings.use_snap=True;ctx.scene.tool_settings.snap_elements={'INCREMENT'}
def setup():
    bpy.ops.wm.tool_set_by_id(name='builtin.move');rv.update();area.tag_redraw()
steps.append(setup)
def press():
    group=state['group'];arrow=group.arrows[0]
    p=arrow.matrix_world@Vector((0,0,.8))
    xy=view.location_3d_to_region_2d(region,rv,p)
    print('HANDLE',p[:],xy[:],flush=True)
    state['xy']=xy
    window.event_simulate(type='MOUSEMOVE',value='NOTHING',x=int(region.x+xy.x),y=int(region.y+xy.y))
steps.append(press)
def down():
    xy=state['xy'];window.event_simulate(type='LEFTMOUSE',value='PRESS',x=int(region.x+xy.x),y=int(region.y+xy.y))
steps.append(down)
def drag():
    xy=state['xy'];window.event_simulate(type='MOUSEMOVE',value='NOTHING',x=int(region.x+xy.x+95),y=int(region.y+xy.y))
steps.append(drag)
def up():
    xy=state['xy'];window.event_simulate(type='LEFTMOUSE',value='RELEASE',x=int(region.x+xy.x+95),y=int(region.y+xy.y))
steps.append(up)
def check():
    assert obj.location.x>0 and abs(obj.location.y)<1e-5 and abs(obj.location.z)<1e-5,obj.location[:]
    step=profiles.active_grid_step_meters(ctx.scene.wavelength)
    assert abs(obj.location.x/step-round(obj.location.x/step))<1e-5,obj.location[:]
    print('PASS dragging native Move button controller uses wavelength backend and grid',flush=True)
    bpy.ops.wm.quit_blender()
steps.append(check)
def tick():
    try:
        with ctx.temp_override(area=area,region=region):
            if steps:steps.pop(0)();return .5
    except Exception:traceback.print_exc();print('FAIL HANDLE DRAG',flush=True);bpy.ops.wm.quit_blender()
bpy.app.timers.register(tick,first_interval=2)
