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
   assert grid.native_available(view.spaces.active)
   assert overlay.show_floor and overlay.show_ortho_grid and overlay.wavelength_grid_enabled
   assert abs(overlay.wavelength_grid_spacing - 32*.0254)<1e-6
   assert overlay.wavelength_grid_subdivisions==8
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
   assert [(km.name,item.type,item.properties.direction) for km,item in grid._keymaps]==[
    (name,key,direction) for name,_ in grid._KEYMAP_SPECS for key,direction in (('LEFT_BRACKET',-1),('RIGHT_BRACKET',1))
   ]
   view.spaces.active.region_3d.view_distance=12
   reg=next(r for r in view.regions if r.type=='WINDOW')
   x,y=reg.x+reg.width//2,reg.y+reg.height//2
   bpy.context.window.event_simulate(type='MOUSEMOVE',value='NOTHING',x=x,y=y)
   bpy.context.window.event_simulate(type='LEFT_BRACKET',value='PRESS',x=x,y=y)
   bpy.context.window.event_simulate(type='LEFT_BRACKET',value='RELEASE',x=x,y=y)
  elif stage==2:
   s=bpy.context.scene.wavelength
   assert s.grid_step=='16',f'Expected 16 after simulated [, got {s.grid_step}'
   view=next(a for a in bpy.context.screen.areas if a.type=='VIEW_3D')
   reg=next(r for r in view.regions if r.type=='WINDOW')
   x,y=reg.x+reg.width//2,reg.y+reg.height//2
   bpy.context.window.event_simulate(type='RIGHT_BRACKET',value='PRESS',x=x,y=y)
   bpy.context.window.event_simulate(type='RIGHT_BRACKET',value='RELEASE',x=x,y=y)
  elif stage==3:
   s=bpy.context.scene.wavelength
   assert s.grid_step=='32',f'Expected 32 after simulated ], got {s.grid_step}'
   assert grid._error is None,grid._error
   bpy.ops.screen.screenshot(filepath=str(out/'selected-grid.png'))
   bpy.ops.wm.save_as_mainfile(filepath=str(out/'native-grid.blend'),check_existing=False)
   assert not grid._native, 'Native state leaked into saved file'
   grid.sync_native()
   saved_native=list(grid._native.values())
   bpy.context.window.workspace=original
  else:
   grid.sync_native();assert not grid._native
   for space,values in saved_native:
    assert tuple(getattr(space.overlay,name) for name in grid._FIELDS)==values
   assert not ui.WL_OT_grid_step.poll(bpy.context)
   wavelength.unregister();assert not grid._keymaps
   (out/'result.txt').write_text('PASS: spacing, bounds, keymap bindings, native RNA settings, workspace scope, cleanup, native grid draw')
   print('PASS GRID SHORTCUTS',flush=True);bpy.ops.wm.quit_blender();return
  stage+=1;return 2
 except Exception:
  import traceback;traceback.print_exc();(out/'result.txt').write_text('FAIL');bpy.ops.wm.quit_blender();return
bpy.app.timers.register(test,first_interval=3)
