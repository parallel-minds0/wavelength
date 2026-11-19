"""Snap preference survives synchronization; copies preserve the source transform."""
import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import transform_bridge as bridge,tool_snap,profiles,transform_sync,primitive_ui
c=bpy.context;c.preferences.use_preferences_save=False
c.scene.wavelength.auto_prepare_assets=False;c.workspace['wl_workspace']=True
s=c.scene.wavelength;s.engine='source_hl2_windows';s.grid_mode='ENGINE'
ts=c.scene.tool_settings;ts.use_snap=False;ts.snap_elements={'VERTEX'}
for _ in range(5):bridge.sync_grid_policy()
assert not ts.use_snap
assert not tool_snap.enabled(c) and not tool_snap.grid_enabled(c)
assert profiles.active_snap_step_meters(s,c) is None
assert profiles.snap_world_value(s,.137,c)==.137
assert profiles.snap_world_length(s,.137,context=c)==.137
bpy.ops.wavelength.workspace_toggle(feature='snapping');bridge.sync_grid_policy()
assert ts.use_snap and not tool_snap.grid_enabled(c)
assert set(ts.snap_elements)=={'VERTEX'}
bpy.ops.wavelength.workspace_toggle(feature='snapping')
for _ in range(5):bridge.sync_grid_policy()
assert not ts.use_snap
obj=c.object;obj['wl_role']='BRUSH';obj.location=(.137,.271,.389);c.view_layer.update()
for _ in range(6):transform_sync.tick()
assert abs(obj.location.x-.137)<1e-6
before=obj.matrix_world.copy();c.scene.cursor.location=(100,200,300)
assert bpy.ops.wavelength.duplicate_in_place()=={'FINISHED'}
copy=c.object;assert copy!=obj and copy.data!=obj.data
assert max(abs(a-b) for ra,rb in zip(before,copy.matrix_world) for a,b in zip(ra,rb))<1e-6
bpy.ops.object.select_all(action='DESELECT')
root=bpy.data.objects.new('Test arch',None);c.collection.objects.link(root)
primitive_ui.rebuild(root,'ARCH',primitive_ui.DEFAULTS,c)
root.location=(.137,.271,.389);primitive_ui.select_assembly(root,c,True);c.view_layer.update()
original=[p.matrix_world.copy() for p in primitive_ui.parts_for(root)]
assert bpy.ops.wavelength.duplicate_in_place()=={'FINISHED'}
new=primitive_ui.root_for(c.object);assert new and new!=root
c.view_layer.update()
assert len(primitive_ui.parts_for(new))==len(original)
for matrix,part in zip(original,primitive_ui.parts_for(new)):
 assert max(abs(a-b) for ra,rb in zip(matrix,part.matrix_world) for a,b in zip(ra,rb))<1e-5
key=next(k for km,k in bridge._keys if k.idname=='wavelength.duplicate_in_place')
assert key.type=='D' and key.shift
c.workspace['wl_workspace']=False;bridge.sync_grid_policy()
assert not ts.use_snap and set(ts.snap_elements)=={'VERTEX'}
assert not bridge.WL_OT_duplicate_in_place.poll(c)
print('PASS snap off/on/off, free movement, plain and procedural duplication in place, workspace restoration',flush=True)
