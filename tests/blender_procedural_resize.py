import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,wavelength
from mathutils import Vector
wavelength.register()
from wavelength.source import primitive_ui as ui,resize_gizmo as rz
c=bpy.context;c.preferences.use_preferences_save=False;c.workspace['wl_workspace']=True
c.scene.wavelength.engine='source_hl2_windows';c.scene.wavelength.grid_mode='ENGINE';c.scene.tool_settings.use_snap=False
root=bpy.data.objects.new('Procedural handles',None);c.collection.objects.link(root)
ui.rebuild(root,'ARCH',ui.DEFAULTS,c);c.view_layer.objects.active=ui.parts_for(root)[0]
c.view_layer.update()
assert rz._brush(c) is None,'Shape gizmos leaked into Object Mode'
assert ui.enter_assembly_edit_mode(root,c,c.object)
assert c.mode=='EDIT_MESH'
assert rz._brush(c)==root
area=next(a for a in c.screen.areas if a.type=='VIEW_3D')
region=next(r for r in area.regions if r.type=='WINDOW')
with c.temp_override(area=area,region=region):
 for tool in ('builtin.select_box','builtin.move','builtin.rotate','builtin.scale'):
  bpy.ops.wm.tool_set_by_id(name=tool)
  assert rz.WL_GGT_engine_resize.poll(c),('Missing shape handles',tool)
class Handle:
 is_modal=True
 def target_set_handler(self,name,get,set):self.setter=set
class Handles:
 def new(self,kind):return Handle()
group=SimpleNamespace(gizmos=Handles())
rz.WL_GGT_engine_resize.setup(group,c)
# Refresh first with the fake handles outside a drag.
for handle,state in group._handles:handle.is_modal=False
rz.WL_GGT_engine_resize.refresh(group,c)
handle,state=group._handles[1] # +X boundary
baseline=root.matrix_world.copy();low,high=rz._local_bounds(root)
left=(baseline@Vector((low[0],0,0))).x
handle.is_modal=True
from wavelength.source import profiles
step=profiles.active_grid_step_meters(c.scene.wavelength)
base_right=(baseline@Vector((high[0],0,0))).x
handle.setter(step*1.2)
c.view_layer.update()
assert abs((root.matrix_world@Vector((low[0],0,0))).x-left)<1e-5
assert abs((root.matrix_world@Vector((high[0],0,0))).x-round((base_right+step*1.2)/step)*step)<1e-5
handle.setter(step*2.2);c.view_layer.update()
assert abs((root.matrix_world@Vector((high[0],0,0))).x-round((base_right+step*2.2)/step)*step)<1e-5
assert c.mode=='EDIT_MESH'
assert all(o.modifiers and o.modifiers[0].show_in_editmode for o in ui.parts_for(root))
assert root['wl_procedural_state']=='PROCEDURAL'
handle.is_modal=False
rz._pending_origins.clear()
print('PASS pre-finalization Arch handles: visible target, evaluated assembly bounds, fixed opposite side, stable drag baseline, live modifiers retained',flush=True)


