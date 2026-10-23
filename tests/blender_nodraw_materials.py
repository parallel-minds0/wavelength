exec(compile((__import__('pathlib').Path(__file__).parent/'blender_custom_model_build.py').read_text().split('bpy.ops.mesh.primitive_cube_add')[0],__file__,'exec'))
from wavelength.source import textures,asset_browser,scene,formats,context_policy
s.engine='goldsrc_windows'
assert any(Path(path).name.lower()=='sdhlt.wad' for path in textures.sources(s))
assert any(n.casefold()=='null' for n in textures.all_names(s,'nodraw'))
mat=asset_browser.publish_material_fast(s,'NULL');assert 'nodraw' in mat.name.lower() and mat.preview.image_size[0]>0
mat=textures.material(s,'nodraw');assert mat['wl_texture'].casefold()=='null'
bpy.ops.mesh.primitive_cube_add();obj=ctx.object;scene.mark_brush(obj);s.texture='nodraw'
assert bpy.ops.wavelength.apply_texture()=={'FINISHED'}
assert s.texture=='NULL' and all(f.texture=='NULL' for f in scene.brush_from_object(obj,s.engine))
assert context_policy.role(obj,s.engine)=='HELPER'
folder=root/'build/nodraw';folder.mkdir(exist_ok=True)
document=scene.export_map(ctx.scene);textures.build_wad(s,document,folder,ctx.scene.objects)
assert 'null' in textures.Wad(folder/'textures.wad').entries
s.engine='source_hl2_windows';s.texture='nodraw'
mat=asset_browser.publish_material_fast(s,'tools/toolsnodraw');assert mat.preview.image_size[0]>0
mat=textures.material(s,'nodraw');assert mat['wl_texture']=='tools/toolsnodraw' and mat.get('wl_realized')
assert bpy.ops.wavelength.apply_texture()=={'FINISHED'}
assert all(f.texture=='tools/toolsnodraw' for f in scene.brush_from_object(obj,s.engine))
print('PASS HL1 compiler WAD discovery, searchable NULL/nodraw preview, canonical assignment and export WAD; HL2 actual toolsnodraw preview and shader realization',flush=True)
