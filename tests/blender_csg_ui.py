import sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
from mathutils import Quaternion,Vector
addon_utils.enable('wavelength',default_set=False)
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.preferences.view.show_splash=False
ctx.workspace['wl_workspace']=True;ctx.workspace['wl_layout_ready']=True
ctx.scene.wavelength.engine='quake'
area=next(a for a in ctx.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
steps=[];state={}
def setup():
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete()
    bpy.ops.mesh.primitive_cube_add();target=ctx.object;target.name='Wall';target.scale=(3,.5,2)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    bpy.ops.mesh.primitive_cube_add(location=(0,0,-1));cutter=ctx.object;cutter.name='Doorway cutter';cutter.scale=(.8,1.5,1.5)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    target.select_set(True);ctx.view_layer.objects.active=target
    assert bpy.ops.wavelength.csg(operation='DIFFERENCE')=={'FINISHED'}
    state.update(target=target,cutter=cutter)
    area.spaces.active.show_region_ui=True
    area.spaces.active.region_3d.view_distance=13
    area.spaces.active.region_3d.view_location=(0,0,0)
    area.spaces.active.region_3d.view_rotation=Quaternion((.86,.49,.07,.12)).normalized()
steps.append(setup)
def panel():next(r for r in area.regions if r.type=='UI').active_panel_category='wavelength'
steps.append(panel)
def verify():
    path=Path(__file__).resolve().parents[1]/'build/csg-preview.png';bpy.ops.screen.screenshot(filepath=str(path))
    ctx.workspace['wl_workspace']=False;assert not bpy.ops.wavelength.csg.poll() and not bpy.ops.wavelength.csg_finish.poll()
    ctx.workspace['wl_workspace']=True
    ctx.view_layer.objects.active=state['cutter']
    assert bpy.ops.wavelength.csg_finish()=={'FINISHED'}
    assert not state['target'].get('wl_csg')
    print('PASS CSG UI operators, cutter-context finalization and workspace scope',flush=True)
    bpy.ops.wm.quit_blender()
steps.append(verify)
def tick():
    try:
        with ctx.temp_override(area=area,region=region):
            if steps:steps.pop(0)();return .8
    except Exception:traceback.print_exc();print('FAIL CSG UI',flush=True);bpy.ops.wm.quit_blender()
bpy.app.timers.register(tick,first_interval=2)
