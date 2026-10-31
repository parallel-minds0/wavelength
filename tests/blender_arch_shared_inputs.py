"""Editing one Arch modifier updates all brush segments and final output."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,wavelength
wavelength.register()
from wavelength.source import primitive_ui as ui,node_primitives as gn
c=bpy.context;c.preferences.use_preferences_save=False;c.workspace['wl_workspace']=True
c.scene.wavelength.engine='source_hl2_windows';c.scene.tool_settings.use_snap=False
root=bpy.data.objects.new('Shared Arch',None);c.collection.objects.link(root)
ui.rebuild(root,'ARCH',ui.DEFAULTS,c)
parts=ui.parts_for(root);c.view_layer.objects.active=parts[-1]
live=parts[-1];modifier_pointer=live.modifiers[0].as_pointer();mesh_pointer=live.data.as_pointer()
gn.set_input(parts[-1].modifiers[0],'Radius',192.)
assert ui.sync_arch_inputs(root,c)
assert live.modifiers[0].as_pointer()==modifier_pointer
assert live.data.as_pointer()==mesh_pointer,'Scalar drag rebuilt mesh datablocks'
assert json.loads(root['wl_parameters'])['radius']==192.
def value(modifier,name):
 socket=next(s for s in modifier.node_group.interface.items_tree if s.item_type=='SOCKET' and s.in_out=='INPUT' and s.name==name)
 return getattr(modifier.properties.inputs,socket.identifier).value if hasattr(modifier,'properties') else modifier[socket.identifier]
assert all(value(o.modifiers[0],'Radius')==192. for o in ui.parts_for(root))
parts=ui.parts_for(root);c.view_layer.objects.active=parts[-1]
gn.set_input(parts[-1].modifiers[0],'Segments',5)
assert ui.sync_arch_inputs(root,c)
assert len(ui.parts_for(root))==5
assert live in ui.parts_for(root) and live.modifiers[0].as_pointer()==modifier_pointer,'Count reduction invalidated the active field'
assert [value(o.modifiers[0],'Part Index') for o in ui.parts_for(root)]==list(range(5))
assert not ui.sync_arch_inputs(root,c),'Unchanged assembly regenerated'
parts=ui.parts_for(root);gn.set_input(parts[0].modifiers[0],'Depth',96.)
# Finalize must flush an input change even before the synchronization timer runs.
result=ui.finalize(root,c)
assert len(result)==5 and all(o.parent is None and not o.modifiers for o in result)
print('PASS shared Arch Radius, segment count decrease, per-part index, no-op idle sync, pending Depth edit before finalization',flush=True)
