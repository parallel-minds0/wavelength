import sys,bpy,bmesh
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import wavelength
wavelength.register()
from wavelength.source import transform_bridge as bridge
from bl_ui.space_toolsystem_toolbar import VIEW3D_PT_tools_active as Tools
c=bpy.context;c.preferences.use_preferences_save=False;c.workspace['wl_workspace']=True
s=c.scene.wavelength;s.engine='source_hl2_windows';s.grid_mode='ENGINE'
area=next(a for a in c.screen.areas if a.type=='VIEW_3D');region=next(r for r in area.regions if r.type=='WINDOW')
bpy.ops.object.mode_set(mode='EDIT')
with c.temp_override(area=area,region=region):
 for index,kind in enumerate(('VERT','EDGE','FACE')):
  c.scene.tool_settings.mesh_select_mode=tuple(i==index for i in range(3))
  bm=bmesh.from_edit_mesh(c.object.data)
  for seq in (bm.faces,bm.edges,bm.verts):
   for element in seq:element.select_set(False)
  bmesh.update_edit_mesh(c.object.data)
  assert not bridge.edit_selection_available(c)
  for name in ('builtin.move','builtin.rotate','builtin.scale'):
   assert not Tools._tool_get_by_id(c,name)[0].widget
  seq=(bm.verts,bm.edges,bm.faces)[index];seq.ensure_lookup_table();seq[0].select_set(True)
  bmesh.update_edit_mesh(c.object.data)
  assert bridge.edit_selection_available(c)
  for name in ('builtin.move','builtin.rotate','builtin.scale'):
   item=Tools._tool_get_by_id(c,name)[0]
   assert item.widget and item.operator.startswith('transform.'),(kind,name,item)
   bpy.ops.wm.tool_set_by_id(name=name)
   bridge.sync()
   assert c.workspace.tools.from_space_view3d_mode('EDIT_MESH').widget
 print('PASS vertex/edge/face selection restores native transform tools; no selection hides them; runtime bindings follow selection changes',flush=True)
