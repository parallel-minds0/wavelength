import sys,traceback
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
c=bpy.context;c.preferences.use_preferences_save=False;c.preferences.view.show_splash=False
c.scene.wavelength.auto_prepare_assets=False;c.workspace['wl_workspace']=True
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.mesh.primitive_cube_add();obj=c.object;obj.name='Object export checkbox'
area=next(a for a in c.screen.areas if a.type=='OUTLINER');space=area.spaces.active
space.show_restrict_column_enable=True;space.show_restrict_column_select=False;space.show_restrict_column_viewport=False;space.show_restrict_column_render=True;space.show_restrict_column_hide=True
region=next(r for r in area.regions if r.type=='WINDOW')
with c.temp_override(area=area,region=region):bpy.ops.outliner.show_hierarchy()
print('OUTLINER REGION',region.x,region.y,region.width,region.height,'UI SCALE',c.preferences.system.ui_scale,flush=True)

unit=20*c.preferences.system.ui_scale
x=int(region.x+region.width-2.9*unit);y=int(region.y+region.height-2.5*unit)
steps=[lambda:c.window.event_simulate(type='MOUSEMOVE',value='NOTHING',x=x,y=y),
       lambda:c.window.event_simulate(type='LEFTMOUSE',value='PRESS',x=x,y=y),
       lambda:c.window.event_simulate(type='LEFTMOUSE',value='RELEASE',x=x,y=y)]
def finish():
 from wavelength.source.export_scope import Scope
 assert obj.hide_render,'Native checkbox click did not disable inclusion'
 assert not Scope(c.scene).includes(obj)
 bpy.ops.screen.screenshot(filepath=str(root.parent/'native-export-checkboxes.png'))
 print('PASS native Outliner object checkbox clicked and inclusion disabled',flush=True)
 bpy.ops.wm.quit_blender()
steps.append(finish)
def tick():
 try:
  if steps:steps.pop(0)();return .25
 except Exception:traceback.print_exc();bpy.ops.wm.quit_blender()
bpy.app.timers.register(tick,first_interval=3)
