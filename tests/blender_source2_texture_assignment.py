"""Texture application to actual VMAP geometry must not enter BSP export."""
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'addon'))
import bpy,bmesh,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import source2_map,source2_assets,asset_placement,surface_tools,textures,asset_browser
# Geometry fixtures use placeholder materials; the unrelated lazy-material
# timer must not try to resolve those test-only paths while modes change.
asset_browser._BUSY=True
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.workspace['wl_workspace']=True
s=ctx.scene.wavelength;s.engine='source2_cs2_windows';s.auto_prepare_assets=False
s.game_dir=r'C:\Program Files (x86)\Steam\steamapps\common\Counter-Strike Global Offensive\game\csgo'
folder=root/'build/source2-texture-assignment';folder.mkdir(parents=True,exist_ok=True);s.project_dir=str(folder)
for obj in list(ctx.scene.objects):bpy.data.objects.remove(obj,do_unlink=True)
def placeholder(settings,name,**kwargs):
 mat=bpy.data.materials.new(name);mat['wl_texture']=name.removeprefix('materials/').removesuffix('.vmat')
 mat['wl_asset_profile']=s.engine;return mat
original=source2_assets.material;source2_assets.material=placeholder
try:source2_map.import_map(ctx,r'C:\Users\user\Projects\port-now\OUT\de_dorms_d.vmap')
finally:source2_assets.material=original
obj=bpy.data.objects.get('Brush.523');assert obj is not None and len(obj.data.polygons)>1
assert obj.data.attributes.get('wl_face_id') is None
for item in ctx.selected_objects:item.select_set(False)
obj.select_set(True);ctx.view_layer.objects.active=obj
chosen=textures.material(s,'anubis/mudbrick02');s.texture=chosen['wl_texture']
before=[tuple(loop.uv) for loop in obj.data.uv_layers['wavelength'].data]
assert bpy.ops.wavelength.apply_texture(material_only=True)=={'FINISHED'}
assert all(obj.data.materials[p.material_index]==chosen for p in obj.data.polygons)
assert before==[tuple(loop.uv) for loop in obj.data.uv_layers['wavelength'].data]
other=placeholder(s,'test/other')
asset_placement.paint(ctx,obj,-1,other,'OBJECT')
bpy.ops.object.mode_set(mode='EDIT');bm=bmesh.from_edit_mesh(obj.data);bm.faces.ensure_lookup_table()
for face in bm.faces:face.select_set(False)
bm.faces[0].select_set(True);bmesh.update_edit_mesh(obj.data)
assert bpy.ops.wavelength.apply_texture(material_only=True)=={'FINISHED'}
bm=bmesh.from_edit_mesh(obj.data)
assert sum(obj.data.materials[f.material_index]==chosen for f in bm.faces)==1
assert ctx.mode=='EDIT_MESH'
ctx.window_manager.wl_texture_apply_scope='AUTO'
asset_placement.paint_drop(ctx,obj,0,other,'SURFACE')
assert all(obj.data.materials[f.material_index]==other for f in bmesh.from_edit_mesh(obj.data).faces)
assert bpy.ops.wavelength.apply_texture(material_only=False)=={'FINISHED'}
bm=bmesh.from_edit_mesh(obj.data);uv=bm.loops.layers.uv['wavelength']
assert any(tuple(loop[uv].uv)!=before[loop.index] for face in bm.faces if face.select for loop in face.loops)
bpy.ops.object.mode_set(mode='OBJECT')
# Direct surface stamps and browser Apply preserve imported corner UVs.
projected=[tuple(loop.uv) for loop in obj.data.uv_layers['wavelength'].data]
asset_placement.paint(ctx,obj,1,chosen,'SURFACE')
assert projected==[tuple(loop.uv) for loop in obj.data.uv_layers['wavelength'].data]
assert obj.data.attributes.get('wl_face_id') is None
print('PASS exact de_dorms_d Brush.523: object/selected-face Apply, mapping, drop/stamp parity and native UV preservation',flush=True)
