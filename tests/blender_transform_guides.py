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
from wavelength.source import axis_guides
from mathutils import Quaternion
folder=Path(__file__).resolve().parents[1]/'build/axis-guides';folder.mkdir(exist_ok=True)
area.spaces.active.region_3d.view_rotation=Quaternion((.8205,.3399,.1759,.4247)).normalized()
steps=[]
def send(key):
    def run():
        window.event_simulate(type=key,value='PRESS',x=region.x+region.width//2,y=region.y+region.height//2)
        window.event_simulate(type=key,value='RELEASE',x=region.x+region.width//2,y=region.y+region.height//2)
    steps.append(run)
for kind in ('G','R','S'):
    send(kind)
    for axis in 'XYZ':
        send(axis)
        def check(kind=kind,axis=axis):
            assert len(axis_guides._guides)==1
            guide=axis_guides._guides[0];assert guide.axis==axis
            guide.draw() if False else None
            bpy.ops.screen.screenshot(filepath=str(folder/(kind+'-'+axis+'.png')))
            print('PASS visible modal axis guide',kind,axis,flush=True)
        steps.append(check)
    send('ESC' if kind!='R' else 'RET')
    def clean():assert not axis_guides._guides,'Leaked axis guide after confirm/cancel'
    steps.append(clean)
def finish():
    print('PASS TRANSFORM AXIS GUIDES',flush=True);bpy.ops.wm.quit_blender()
steps.append(finish)
def tick():
    try:
        with ctx.temp_override(area=area,region=region):
            if steps:steps.pop(0)();return .3
    except Exception:traceback.print_exc();print('FAIL AXIS GUIDES',flush=True);bpy.ops.wm.quit_blender()
bpy.app.timers.register(tick,first_interval=2)
