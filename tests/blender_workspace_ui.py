import bpy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'addon'))
import wavelength
from wavelength.source import workspace,grid
bpy.context.preferences.view.show_splash=False
wavelength.register()
original=bpy.context.workspace
baseline=[a.type for a in bpy.context.screen.areas]
stage=0
out=ROOT/'build/workspace-proof';out.mkdir(parents=True,exist_ok=True)
def test():
 global stage
 try:
  if stage==0:
   ws=workspace.ensure(bpy.context);assert ws and ws!=original
   assert workspace.ensure(bpy.context)==ws
   assert baseline==[a.type for a in bpy.context.screen.areas]
   bpy.context.window.workspace=ws
  elif stage==1:
   assert workspace.active()
   assert any(a.type=='FILE_BROWSER' and a.ui_type=='ASSETS' for a in bpy.context.screen.areas)
   s=bpy.context.scene.wavelength;s.engine='source_hl2_linux';s.grid_mode='ENGINE'
   view=next(a for a in bpy.context.screen.areas if a.type=='VIEW_3D');overlay=view.spaces.active.overlay
   native=(overlay.show_floor,overlay.show_ortho_grid,overlay.grid_scale,overlay.grid_subdivisions)
   grid.update(s,bpy.context);assert native==(overlay.show_floor,overlay.show_ortho_grid,overlay.grid_scale,overlay.grid_subdivisions)
   with bpy.context.temp_override(area=view,region=next(r for r in view.regions if r.type=='WINDOW')):bpy.ops.view3d.view_axis(type='TOP')
   view.spaces.active.region_3d.view_distance=12
   bpy.ops.wavelength.primitive(kind='STAIRS')
  elif stage==2:
   assert grid._error is None,grid._error
   bpy.ops.screen.screenshot(filepath=str(out/'workspace.png'))
   bpy.context.window.workspace=original
  else:
   assert not workspace.active()
   assert baseline==[a.type for a in bpy.context.screen.areas]
   print('PASS WORKSPACE: created once, native assets, native grid unchanged, other layout preserved',flush=True)
   bpy.ops.wm.quit_blender();return
  stage+=1;return 2
 except Exception:
  import traceback;traceback.print_exc();print('FAIL WORKSPACE',flush=True);bpy.ops.wm.quit_blender();return
bpy.app.timers.register(test,first_interval=3)
