"""Per-face asset assignment, mapping and held texture/entity sampling."""
exec(compile((__import__('pathlib').Path(__file__).parent/'blender_custom_model_build.py').read_text().split('bpy.ops.mesh.primitive_cube_add')[0],__file__,'exec'))
from wavelength.source import surface_tools,scene,textures,asset_browser
import bmesh
s.engine='goldsrc_windows';s.auto_prepare_assets=False
names=[n for n in textures.all_names(s) if n.lower().startswith('c1a0')][:2];assert len(names)==2
materials=[textures.material(s,n) for n in names]
bpy.ops.mesh.primitive_cube_add();obj=ctx.object;scene.mark_brush(obj);s.texture=names[0]
assert bpy.ops.wavelength.apply_texture()=={'FINISHED'}
before=json.loads(obj.data['wl_faces']);s.texture=names[1]
bpy.ops.object.mode_set(mode='EDIT');bm=bmesh.from_edit_mesh(obj.data);bm.faces.ensure_lookup_table()
for face in bm.faces:face.select_set(False)
bm.faces[0].select_set(True);bmesh.update_edit_mesh(obj.data)
surface_tools.assign_material(ctx,materials[1]);assert obj.mode=='EDIT'
bm=bmesh.from_edit_mesh(obj.data);bm.faces.ensure_lookup_table()
assert sum(obj.data.materials[f.material_index]==materials[1] for f in bm.faces)==1
after=json.loads(obj.data['wl_faces']);assert sum(a['texture']!=before[k]['texture'] for k,a in after.items())==1
assert all(a['projection']==before[k]['projection'] for k,a in after.items())
assert bpy.ops.wavelength.surface_align(action='FIT')=={'FINISHED'} and obj.mode=='EDIT'
bm=bmesh.from_edit_mesh(obj.data);bm.faces.ensure_lookup_table();picked=next(f.index for f in bm.faces if obj.data.materials[f.material_index]==materials[1]);surface_tools.sample(ctx,obj,picked,'TEXTURE')
assert json.loads(ctx.scene['_wl_asset_clipboard'])['path'].casefold()==names[1].casefold(),(ctx.scene['_wl_asset_clipboard'],names)
assert bpy.ops.wavelength.texture_nudge(action='FLIP_U')=={'FINISHED'} and s.texture_scale_u<0
assert any(r['projection'][3]<0 for r in json.loads(obj.data['wl_faces']).values())
bpy.ops.object.mode_set(mode='OBJECT');surface_tools.assign_material(ctx,materials[1])
assert all(obj.data.materials[p.material_index]==materials[1] for p in obj.data.polygons)
entity=_spawn_point_entity(ctx,'monster_scientist');surface_tools.sample(ctx,entity,-1)
assert json.loads(ctx.scene['_wl_asset_clipboard'])['path']=='monster_scientist'
count=len(ctx.scene.objects);assert bpy.ops.wavelength.use_held_asset()=={'FINISHED'};assert len(ctx.scene.objects)>count
print('PASS selected-face material assignment and persistent metadata, preserved mapping, fit, Object Mode whole-brush assignment, texture sampling and held entity class placement',flush=True)
