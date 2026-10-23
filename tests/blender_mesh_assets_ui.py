import sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import grid,ui,external_library
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.preferences.view.show_splash=False
ctx.workspace['wl_workspace']=True;ctx.workspace['wl_layout_ready']=True
area=next(a for a in ctx.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
folder=Path(__file__).resolve().parents[1]/'build'
steps=[]
def setup():
 ctx.scene.wavelength.engine='godot4';ctx.scene.wavelength.mesh_export_directory=str(folder/'godot-export')
 assert Path(ctx.scene.wavelength.game_executable).is_file()
 assert not grid.engine_enabled(ctx.scene.wavelength) and not ui.WL_PT_build.poll(ctx)
 assert bpy.ops.wavelength.export_mesh_assets.poll()
 area.spaces.active.show_region_ui=True
steps.append(setup)
def panel():next(r for r in area.regions if r.type=='UI').active_panel_category='wavelength'
steps.append(panel)
def godot():
 bpy.ops.screen.screenshot(filepath=str(folder/'godot-export-panel.png'))
 ctx.scene.wavelength.engine='source2_cs2_windows'
 assert grid.engine_enabled(ctx.scene.wavelength) and not ui.WL_PT_build.poll(ctx)
 assert (Path(ctx.scene.wavelength.compiler_dir)/'resourcecompiler.exe').is_file()
 assert external_library._key is None
steps.append(godot)
def source2():
 bpy.ops.screen.screenshot(filepath=str(folder/'cs2-export-panel.png'))
 addon_utils.disable('wavelength',default_set=False);addon_utils.enable('wavelength',default_set=False)
 assert bpy.ops.wavelength.export_mesh_assets.get_rna_type()
 print('PASS mesh profile UI, discovered paths, metric/profile grids, no BSP build and registration lifecycle',flush=True)
 bpy.ops.wm.quit_blender()
steps.append(source2)
def tick():
 try:
  with ctx.temp_override(area=area,region=region):
   if steps:steps.pop(0)();return .8
 except Exception:traceback.print_exc();print('FAIL MESH UI',flush=True);bpy.ops.wm.quit_blender()
bpy.app.timers.register(tick,first_interval=2)
