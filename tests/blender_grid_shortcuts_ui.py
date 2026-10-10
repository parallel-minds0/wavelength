"""Run in a factory-startup Blender UI; exits after grid/keymap assertions."""
import bpy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'addon'))
import wavelength
from wavelength.source import workspace,grid,ui,profiles
wavelength.register()
original=bpy.context.workspace
stage=0
saved_native=[]
out=ROOT/'build/grid-proof';out.mkdir(parents=True,exist_ok=True)
def test():
 global stage,saved_native
 try:
  if stage==0:
   bpy.context.window.workspace=workspace.ensure(bpy.context)
  elif stage==1:
   s=bpy.context.scene.wavelength;s.engine='source_hl2_linux';s.grid_mode='ENGINE';s.grid_step='32'
   view=next(a for a in bpy.context.screen.areas if a.type=='VIEW_3D')
   overlay=view.spaces.active.overlay
   grid.sync_native()
   assert not overlay.show_floor and not overlay.show_ortho_grid
   baseline=(overlay.grid_scale,overlay.grid_subdivisions,overlay.show_floor,overlay.show_ortho_grid)
   assert abs(profiles.display_grid(s)[0]-32*.0254)<1e-6 and profiles.display_grid(s)[1]==8
   with bpy.context.temp_override(area=view,region=next(r for r in view.regions if r.type=='WINDOW')):
    assert ui.WL_OT_grid_step.poll(bpy.context)
    bpy.ops.wavelength.grid_step(direction=-1);assert s.grid_step=='16'
    bpy.ops.wavelength.grid_step(direction=1);assert s.grid_step=='32'
    s.grid_step='1';bpy.ops.wavelength.grid_step(direction=-1);assert s.grid_step=='1'
    s.grid_step='256';bpy.ops.wavelength.grid_step(direction=1);assert s.grid_step=='256'
    s.grid_step='32'
    s.engine='blender';assert profiles.display_grid(s)==(1.0,10)
    bpy.ops.wavelength.grid_step(direction=-1);assert profiles.display_grid(s)==(.5,10)
    bpy.ops.wavelength.grid_step(direction=1);assert profiles.display_grid(s)==(1.0,10)
    s.engine='source_hl2_linux';s.grid_mode='ENGINE';s.grid_step='32'
    bpy.ops.view3d.view_axis(type='TOP')
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete()
   assert baseline==(overlay.grid_scale,overlay.grid_subdivisions,overlay.show_floor,overlay.show_ortho_grid)
   assert [(item.type,item.properties.direction) for km,item in grid._keymaps]==[('LEFT_BRACKET',-1),('RIGHT_BRACKET',1)]
   view.spaces.active.region_3d.view_distance=12
  elif stage==2:
   assert grid._error is None,grid._error
   bpy.ops.screen.screenshot(filepath=str(out/'selected-grid.png'))
   saved_native=list(grid._native.values())
   bpy.context.window.workspace=original
  else:
   grid.sync_native();assert not grid._native
   for space,floor,ortho in saved_native:
    assert (space.overlay.show_floor,space.overlay.show_ortho_grid)==(floor,ortho)
   assert not ui.WL_OT_grid_step.poll(bpy.context)
   wavelength.unregister();assert not grid._keymaps
   (out/'result.txt').write_text('PASS: spacing, bounds, keymap bindings, neutral native settings, workspace scope, cleanup, GPU draw')
   print('PASS GRID SHORTCUTS',flush=True);bpy.ops.wm.quit_blender();return
  stage+=1;return 2
 except Exception:
  import traceback;traceback.print_exc();(out/'result.txt').write_text('FAIL');bpy.ops.wm.quit_blender();return
bpy.app.timers.register(test,first_interval=3)
