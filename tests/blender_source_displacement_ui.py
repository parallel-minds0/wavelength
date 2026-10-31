"""Real UI displacement paint, cursor rendering and single-step undo."""
import sys,traceback,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'addon'));sys.path.insert(0,str(root))
import bpy,wavelength
from mathutils import Quaternion
from bpy_extras.view3d_utils import location_3d_to_region_2d
wavelength.register()
from wavelength.source import scene,source_displacement as sd
from tests.test_displacement import fixture
c=bpy.context;c.preferences.use_preferences_save=False;c.preferences.view.show_splash=False;c.workspace['wl_workspace']=True;c.workspace['wl_layout_ready']=True
c.scene.wavelength.engine='source_hl2_windows'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete()
col=scene.import_map(c.scene,fixture(3)[0]);obj=next(o for o in col.objects if o.get(sd.KEY));name=obj.name
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);c.view_layer.objects.active=obj
obj.wavelength_displacement_connected=False;obj.wavelength_terrain.paint_radius=64;obj.wavelength_terrain.paint_strength=2
area=next(a for a in c.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW');rv=area.spaces.active.region_3d
c.view_layer.update();target=obj.matrix_world@obj.data.vertices[40].co
rv.view_rotation=Quaternion((1,0,0,0));rv.view_perspective='ORTHO';rv.view_distance=5;rv.view_location=target
state={};steps=[]
def setup():
 rv.update();state['point']=location_3d_to_region_2d(region,rv,target);state['before']=tuple(obj.data.vertices[40].co)
 bpy.ops.ed.undo_push(message='Before native displacement paint')
 assert bpy.ops.wavelength.source_displacement_paint('INVOKE_DEFAULT')=={'RUNNING_MODAL'}
steps.append(setup)
def event(kind,value='PRESS'):
 def run():
  p=state['point'];c.window.event_simulate(type=kind,value=value,x=int(region.x+p.x),y=int(region.y+p.y))
 steps.append(run)
event('MOUSEMOVE','NOTHING');event('LEFTMOUSE');event('MOUSEMOVE','NOTHING');event('LEFTMOUSE','RELEASE')
def capture():
 assert tuple(obj.data.vertices[40].co)!=state['before'],'Mouse paint did not change surface'
 output=root/'build/source-displacement';output.mkdir(parents=True,exist_ok=True)
 bpy.ops.screen.screenshot(filepath=str(output/'paint-native.png'))
steps.append(capture)
event('RET');event('RET','RELEASE')
def check():
 scene.export_map(c.scene)
 assert not sd._RUNNING
 assert bpy.ops.ed.undo()=={'FINISHED'}
 restored=bpy.data.objects[name]
 assert max(abs(a-b) for a,b in zip(restored.data.vertices[40].co,state['before']))<1e-6
 print('PASS native displacement painting: mouse stroke, viewport brush cursor, Source export and one-step undo',flush=True)
 bpy.ops.wm.quit_blender()
steps.append(check)
def tick():
 try:
  with c.temp_override(area=area,region=region):
   if steps:steps.pop(0)();return .35
 except Exception:traceback.print_exc();bpy.ops.wm.quit_blender()
bpy.app.timers.register(tick,first_interval=2)
