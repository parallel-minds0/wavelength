"""Interactive native-shader experiment; only use with blender-grid-test."""
import bpy,sys,os
from pathlib import Path
from mathutils import Quaternion
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'addon'))
import wavelength
wavelength.register()
from wavelength.source import grid
# Experimental shader reads this native step hierarchy. Production remains unchanged.
grid._NATIVE_SUBDIVISIONS=10
bpy.context.preferences.view.show_splash=False
bpy.context.scene.unit_settings.system='NONE'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
s=bpy.context.scene.wavelength;s.engine=os.environ.get('WL_GRID_ENGINE','goldsrc');s.grid_mode='ENGINE';s.grid_step='16'
s.status='EXPERIMENTAL native shader grid — original Blender unchanged'
for area in bpy.context.screen.areas:
 if area.type=='VIEW_3D':
  area.spaces.active.show_region_ui=True
  area.spaces.active.region_3d.view_distance=5
  with bpy.context.temp_override(area=area,region=next(r for r in area.regions if r.type=='WINDOW')):
   bpy.ops.view3d.view_axis(type='TOP')
OUTPUT=ROOT/('build/grid-viewport-baseline' if os.environ.get('WL_GRID_BASELINE')=='1' else 'build/grid-viewport-test');OUTPUT.mkdir(exist_ok=True)
count=0
views=[('TOP','16'),('TOP','32'),('FRONT','16'),('RIGHT','16'),('PERSP','16'),('FAR','16')]
def capture():
 global count
 bpy.ops.screen.screenshot(filepath=str(OUTPUT/f'{count}-{views[count][0]}-{views[count][1]}.png'))
 print('GRID_TEST_CAPTURE',views[count],flush=True)
 count+=1
 if count==len(views):
  (OUTPUT/'complete.txt').write_text('Screenshots captured; inspect images and shader log before accepting.\n')
  if os.environ.get('WL_GRID_TEST_QUIT')=='1':bpy.ops.wm.quit_blender()
  return None
 view,step=views[count];s.grid_step=step
 for area in bpy.context.screen.areas:
  if area.type!='VIEW_3D':continue
  with bpy.context.temp_override(area=area,region=next(r for r in area.regions if r.type=='WINDOW')):
   if view in {'PERSP','FAR'}:
    area.spaces.active.region_3d.view_rotation=Quaternion((.88,.3,.15,.3)).normalized()
    area.spaces.active.region_3d.view_perspective='PERSP'
    if view=='FAR':area.spaces.active.region_3d.view_distance=500
   else:bpy.ops.view3d.view_axis(type=view)
  area.tag_redraw()
 return 2.0
# Auto-capture only in test mode. Interactive launch stays at the initial top view.
if os.environ.get('WL_GRID_CAPTURE')=='1':bpy.app.timers.register(capture,first_interval=6.0)
