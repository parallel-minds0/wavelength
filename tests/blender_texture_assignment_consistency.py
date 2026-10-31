"""Browser Apply and viewport paint agree on selected faces and object scope."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,bmesh,wavelength
wavelength.register()
from wavelength.source import surface_tools,asset_placement
c=bpy.context;c.preferences.use_preferences_save=False;c.workspace['wl_workspace']=True
c.scene.wavelength.engine='blender';c.scene.wavelength.texture='deliberately different held texture'
c.window_manager.wl_texture_apply_scope='AUTO'
bpy.ops.mesh.primitive_cube_add();obj=c.object
mats=[bpy.data.materials.new(n) for n in ('Original','Chosen')]
obj.data.materials.append(mats[0])
bpy.ops.object.mode_set(mode='EDIT');bm=bmesh.from_edit_mesh(obj.data);bm.faces.ensure_lookup_table()
for f in bm.faces:f.select_set(False)
bm.faces[0].select_set(True);bm.faces[3].select_set(True);bmesh.update_edit_mesh(obj.data)
surface_tools.assign_material(c,mats[1])
bm=bmesh.from_edit_mesh(obj.data)
assert sum(obj.data.materials[f.material_index]==mats[1] for f in bm.faces)==2
assert c.mode=='EDIT_MESH'
c.window_manager.wl_texture_apply_scope='OBJECT'
surface_tools.assign_material(c,mats[0])
assert all(obj.data.materials[f.material_index]==mats[0] for f in bmesh.from_edit_mesh(obj.data).faces)
c.window_manager.wl_texture_apply_scope='AUTO'
asset_placement.paint_drop(c,obj,1,mats[1],'SURFACE')
assert sum(obj.data.materials[f.material_index]==mats[1] for f in bmesh.from_edit_mesh(obj.data).faces)==2
bpy.ops.object.mode_set(mode='OBJECT');surface_tools.assign_material(c,mats[1])
assert all(obj.data.materials[f.material_index]==mats[1] for f in obj.data.polygons)
print('PASS supplied browser material, selected faces, edit-mode Object override, drop parity, plain mesh Object mode',flush=True)
