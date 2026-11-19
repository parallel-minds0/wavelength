import sys
from pathlib import Path
from types import SimpleNamespace
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'addon'))
import bpy,addon_utils
from mathutils import Vector
from bpy_extras import view3d_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import civ5_cells as cells,context_policy
ctx=bpy.context;ctx.preferences.use_preferences_save=False
ctx.scene.wavelength.auto_prepare_assets=False;ctx.workspace['wl_workspace']=True
path=next(Path(r"C:\Program Files (x86)\Steam\steamapps\common\Sid Meier's Civilization V").rglob('Earth_Duel.Civ5Map'))
area=next(a for a in ctx.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
with ctx.temp_override(area=area,region=region):
 obj=cells.import_map(ctx,path)
 area.spaces.active.show_region_ui=True
 assert ctx.workspace.tools.from_space_view3d_mode('OBJECT').idname=='wavelength.civ5_cells'
def test():
 try:
  with ctx.temp_override(area=area,region=region):
   ctx.region_data.update();i=100
   center=sum((obj.data.vertices[v].co for v in obj.data.polygons[i].vertices),Vector())/6
   xy=view3d_utils.location_3d_to_region_2d(region,ctx.region_data,center)
   event=SimpleNamespace(mouse_region_x=xy.x,mouse_region_y=xy.y,shift=False)
   hit=cells.WL_OT_civ5_pick.hit(None,ctx,event);assert hit==i,(hit,i)
   mock=SimpleNamespace(_seen=set(),hit=lambda c,e:i)
   settings=ctx.scene.wavelength_civ5;settings.mode='SELECT'
   cells.WL_OT_civ5_pick.paint(mock,ctx,event);assert cells.selected(obj)==[i]
   mock._seen.clear();settings.mode='PAINT';settings.field='elevation';settings.elevation='1'
   cells.WL_OT_civ5_pick.paint(mock,ctx,event);assert obj.data.attributes['civ5_elevation'].data[i].value==1
   assert not context_policy.operation_allowed(ctx,'wavelength.primitive')
   assert not context_policy.allows(ctx,'gizmos')
   assert context_policy.operation_allowed(ctx,'wavelength.export_map')
  print('PASS Civ V high-level tool activation, viewport ray selection, painting and profile-specific geometry guards',flush=True)
 except Exception:
  import traceback;traceback.print_exc();print('FAIL Civ V UI',flush=True)
 bpy.ops.wm.quit_blender()
bpy.app.timers.register(test,first_interval=2)
