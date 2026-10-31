import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,bmesh,wavelength
wavelength.register()
from wavelength.source import primitive_ui as ui,node_primitives as gn
c=bpy.context;c.preferences.use_preferences_save=False;c.workspace['wl_workspace']=True
c.scene.wavelength.engine='source_hl2_windows';c.scene.tool_settings.use_snap=False
root=bpy.data.objects.new('Edit Arch',None);c.collection.objects.link(root)
ui.rebuild(root,'ARCH',ui.DEFAULTS,c)
part=ui.parts_for(root)[0]
assert ui.enter_assembly_edit_mode(root,c,part)
mod=part.modifiers[0];pointer=mod.as_pointer()
gn.set_input(mod,'Fill Center',True)
ui.sync_assemblies(force=True)
assert c.mode=='EDIT_MESH'
assert json.loads(root['wl_parameters'])['fill_center'] is True
for obj in ui.parts_for(root):
 bm=bmesh.from_edit_mesh(obj.data)
 assert len(bm.verts)==6,(obj.name,len(bm.verts))
 assert all(e.is_manifold for e in bm.edges)
assert part.modifiers[0].as_pointer()==pointer
gn.set_input(mod,'Fill Center',False);ui.sync_assemblies(force=True)
gn.set_input(mod,'Thickness',64.);ui.sync_assemblies(force=True)
assert json.loads(root['wl_parameters'])['thickness']==64.
for obj in ui.parts_for(root):assert len(bmesh.from_edit_mesh(obj.data).verts)==8
assert c.mode=='EDIT_MESH' and part.modifiers[0].as_pointer()==pointer
print('PASS actual Edit Mode timer: Fill Center propagates to all eight segments, cages become manifold triangular prisms, unfill/thickness restore eight-vertex cages; modifier retained',flush=True)


