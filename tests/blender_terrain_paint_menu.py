import sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import terrain,terrain_paint
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.preferences.view.show_splash=False
folder=Path(__file__).resolve().parents[1]/'build/terrain';folder.mkdir(exist_ok=True)
ctx.preferences.filepaths.temporary_directory=str(folder);ctx.workspace['wl_workspace']=True;ctx.workspace['wl_layout_ready']=True
ctx.scene.wavelength.engine='blender';obj=terrain.create(ctx,paintable_surface=True)
area=next(a for a in ctx.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
steps=[]
def choose():
    with ctx.temp_override(area=area,region=region):assert bpy.ops.wavelength.terrain_paint('INVOKE_DEFAULT',mode='SMOOTH')=={'RUNNING_MODAL'}
    assert obj.wavelength_terrain.paint_mode=='SMOOTH'
    # Finish the modal operator through its normal event path.
    ctx.window.event_simulate(type='ESC',value='PRESS',x=region.x+200,y=region.y+200)
steps.append(choose)
def menu():
    assert not terrain_paint._RUNNING
    with ctx.temp_override(area=area,region=region):bpy.ops.wm.call_menu(name='WL_MT_terrain_paint_types')
steps.append(menu)
def check():
    bpy.ops.screen.screenshot(filepath=str(folder/'terrain-paint-menu.png'))
    print('PASS paint type selection and native hold-menu contents',flush=True)
    bpy.ops.wm.quit_blender()
steps.append(check)
def tick():
    try:
        if steps:steps.pop(0)()
        return .5 if steps else None
    except Exception:traceback.print_exc();print('FAIL PAINT MENU',flush=True);bpy.ops.wm.quit_blender()
bpy.app.timers.register(tick,first_interval=1.5)
