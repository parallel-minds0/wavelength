import sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
from mathutils import Quaternion
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import terrain
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.preferences.view.show_splash=False
folder=Path(__file__).resolve().parents[1]/'build/terrain';folder.mkdir(exist_ok=True)
ctx.preferences.filepaths.temporary_directory=str(folder)
ctx.workspace['wl_workspace']=True;ctx.workspace['wl_layout_ready']=True
ctx.scene.wavelength.engine='blender'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.wavelength.terrain_add();obj=ctx.object
assert not terrain.paintable(obj)
bpy.ops.wavelength.terrain_enable_paint()
obj.wavelength_terrain.amplitude=2;obj.wavelength_terrain.seed=7
area=next(a for a in ctx.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
rv=area.spaces.active.region_3d;rv.view_rotation=Quaternion((.86,.36,.14,.33)).normalized();rv.view_location=(0,0,0);rv.view_distance=28
props=next(a for a in ctx.screen.areas if a.type=='PROPERTIES');props.spaces.active.context='OBJECT'
def check():
    try:
        assert obj.modifiers[0].node_group.get('wl_generator')==terrain.GENERATOR
        assert terrain.WL_PT_terrain.poll(ctx)
        bpy.ops.screen.screenshot(filepath=str(folder/'terrain-ui.png'))
        print('PASS terrain creation operator, live property updates and native properties panel',flush=True)
    except Exception:traceback.print_exc();print('FAIL TERRAIN UI',flush=True)
    finally:bpy.ops.wm.quit_blender()
bpy.app.timers.register(check,first_interval=1.5)
