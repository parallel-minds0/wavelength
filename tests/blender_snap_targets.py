"""User snap targets/masks survive refresh, modes and workspace transitions."""
import sys
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import transform_bridge as bridge,tool_snap,profiles,precision_move,engine_tools
c=bpy.context;c.preferences.use_preferences_save=False;c.workspace['wl_workspace']=True
s=c.scene.wavelength;s.auto_prepare_assets=False;s.engine='source_hl2_windows';s.grid_mode='ENGINE'
a=next(a for a in c.screen.areas if a.type=='VIEW_3D');r=next(r for r in a.regions if r.type=='WINDOW')
ts=c.scene.tool_settings
with c.temp_override(area=a,region=r):
 for target in ({'VERTEX'},{'EDGE'},{'FACE'},{'GRID'},{'INCREMENT'},{'VERTEX','EDGE'}):
  ts.snap_elements=target;ts.use_snap=True
  ts.use_snap_translate=True;ts.use_snap_rotate=False;ts.use_snap_scale=False;ts.use_snap_grid_absolute=False
  for _ in range(10):bridge.sync()
  assert set(ts.snap_elements)==target
  assert not ts.use_snap_rotate and not ts.use_snap_scale and not ts.use_snap_grid_absolute
  grid=bool(target & {'GRID','INCREMENT'})
  assert tool_snap.grid_enabled(c)==grid
  assert profiles.snap_enabled(s,c)==grid
  if not grid:assert profiles.snap_world_value(s,.137,c)==.137
  bpy.ops.object.mode_set(mode='EDIT');bridge.sync();assert set(ts.snap_elements)==target
  bpy.ops.object.mode_set(mode='OBJECT')
  c.workspace['wl_workspace']=False;bridge.sync();assert set(ts.snap_elements)==target
  c.workspace['wl_workspace']=True;bridge.sync();assert set(ts.snap_elements)==target
 ts.snap_elements={'VERTEX'};ts.use_snap=True;ts.use_snap_translate=True
 translate=Mock(return_value={'RUNNING_MODAL'})
 with patch.object(precision_move,'bpy',NS(ops=NS(transform=NS(translate=translate)))):
  assert precision_move.WL_OT_precision_move.invoke(NS(axis='FREE'),c,NS(ctrl=False))=={'FINISHED'}
 translate.assert_called_once_with('INVOKE_DEFAULT',constraint_axis=(False,False,False))
 ts.snap_elements={'GRID'};ts.use_snap=True
 assert tool_snap.grid_enabled(c)
 assert tool_snap.step(c)==profiles.active_grid_step_meters(s)
 ts.use_snap=False
 for _ in range(10):bridge.sync()
 assert not ts.use_snap and not tool_snap.grid_enabled(c)
print('PASS snap targets/masks survive timer, Edit/Object and workspace switches; Vertex uses native movement; Grid uses profile spacing',flush=True)
