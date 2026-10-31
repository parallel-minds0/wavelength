import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,wavelength
wavelength.register()
from wavelength.source import transform_bridge as bridge,tool_snap,resize_gizmo as rz,profiles
from bl_ui.space_toolsystem_toolbar import VIEW3D_PT_tools_active as Tools
c=bpy.context;c.preferences.use_preferences_save=False;c.workspace['wl_workspace']=True
s=c.scene.wavelength;s.engine='source_hl2_windows';s.grid_mode='ENGINE'
ts=c.scene.tool_settings;ts.use_snap=False;ts.snap_elements={'VERTEX'}
assert tool_snap.grid_enabled(c,SimpleNamespace(ctrl=True),'SCALE')
assert tool_snap.enabled(c,SimpleNamespace(ctrl=True),'ROTATE')
bridge.sync_grid_policy()
assert ts.use_snap and ts.use_snap_translate and ts.use_snap_rotate and ts.use_snap_scale
assert set(ts.snap_elements)=={'GRID'}
a=next(a for a in c.screen.areas if a.type=='VIEW_3D');r=next(r for r in a.regions if r.type=='WINDOW')
bpy.ops.object.mode_set(mode='EDIT')
with c.temp_override(area=a,region=r):
 for name in bridge.NATIVE:
  item=Tools._tool_get_by_id(c,name)[0]
  assert item.widget=='' and not item.keymap and not item.operator,(name,item)
 bpy.ops.wm.tool_set_by_id(name='builtin.move')
 bridge.sync()
 assert c.workspace.tools.from_space_view3d_mode('EDIT_MESH').widget=='', 'Native Edit Mode gizmo still bound'
bpy.ops.object.mode_set(mode='OBJECT')
c.workspace['wl_workspace']=False;bridge.sync_grid_policy()
assert not ts.use_snap and set(ts.snap_elements)=={'VERTEX'}
print('PASS Edit Mode native transform widgets/operators removed; profile grid forced with Ctrl/magnet off; native snap state restored outside wavelength',flush=True)

