"""Port native Source textures after switching profiles, without preview images."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import source_assets,source2_map,source2_dmx
bpy.context.preferences.use_preferences_save=False
s=bpy.context.scene.wavelength
s.engine='source_hl2_windows'
s.game_dir='C:/Program Files (x86)/Steam/steamapps/common/Half-Life 2/hl2_complete'
mat=source_assets.material(s,'brick/brickwall001a')
assert Path(mat.get('wl_source_game','')).resolve()==Path(s.game_dir).resolve(),(mat.get('wl_source_game'),source_assets.__file__)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete()
bpy.ops.mesh.primitive_cube_add()
bpy.context.object.data.materials.append(mat)
s.engine='source2_cs2_windows'
s.game_dir='C:/Program Files (x86)/Steam/steamapps/common/Counter-Strike Global Offensive/game/csgo'
s.compiler_dir=str(Path(s.game_dir).parent/'bin/win64')
root=Path(__file__).resolve().parents[1]/'build/source2-port'
path=root/'maps/port.vmap'
count,warnings=source2_map.export(bpy.context,path)
assert count==1
document=source2_dmx.loads(path.read_text())
geometry=source2_dmx.read_mesh(document.get('world').get('children')[0].get('meshData'))
material=root/geometry[3][0]
assert material.is_file()
images=list(material.parent.glob('*_color.png'));assert images
image=bpy.data.images.load(str(images[0]))
assets=source_assets.library(mat['wl_source_game'])
props=assets.material(mat['wl_texture'])
decoded=source_assets.decode_vtf(assets.read('materials/'+props['$basetexture']+'.vtf'),None)
assert tuple(image.size)==decoded[:2],(tuple(image.size),decoded[:2])
assert mat.get('wl_source2_material') is None,'Export changed the source material'
print('PASS Source 1 original-resolution textures deployed beside VMAP after CS2 profile switch',flush=True)
mat['wl_source_game']='Z:/unavailable-source-game'
mat.pop('wl_source_mounts',None)
try:source2_map.export(bpy.context,root/'maps/strict.vmap')
except ValueError as exc:assert 'original Source 1 game is unavailable' in str(exc)
else:raise AssertionError('Strict export must reject unavailable materials')
count,warnings=source2_map.export(bpy.context,root/'maps/ignored.vmap',ignore_material_errors=True)
assert count==1 and any('placeholder' in warning for warning in warnings)
document=source2_dmx.loads((root/'maps/ignored.vmap').read_text())
geometry=source2_dmx.read_mesh(document.get('world').get('children')[0].get('meshData'))
assert (root/geometry[3][0]).is_file()
assert bpy.ops.wavelength.export_map.get_rna_type().properties.get('ignore_material_errors') is not None
print('PASS optional material-error bypass preserves geometry and writes a placeholder with warnings',flush=True)
from wavelength.source import source2_port_materials
cube=bpy.context.object
original=cube.data.materials[0]
converted,failures=source2_port_materials.convert_scene(bpy.context,root/'prepared',assign=False,source_directory='C:/Program Files (x86)/Steam/steamapps/common/Half-Life 2/hl2_complete')
assert len(converted)==1 and not failures
assert cube.data.materials[0]==original
converted,failures=source2_port_materials.convert_scene(bpy.context,root/'prepared',assign=True,source_directory='C:/Program Files (x86)/Steam/steamapps/common/Half-Life 2/hl2_complete')
assert len(converted)==1 and not failures
new=cube.data.materials[0]
assert new!=original and new.get('wl_source2_material')
assert new['wl_width']==original['wl_width'] and new['wl_height']==original['wl_height'],'Conversion changed brush projection dimensions'
assert original.name in bpy.data.materials
assert any(n.type=='TEX_IMAGE' and n.image for n in new.node_tree.nodes)
assert bpy.ops.wavelength.convert_source2_materials.get_rna_type().properties.get('assign_materials')
print('PASS optional standalone conversion, explicit source folder recovery, assignment and original preservation',flush=True)
import zipfile
destination=root/'relocated/maps/shared.vmap'
count,warnings=source2_map.export(bpy.context,destination,package=True)
assert count==1
assert original.use_fake_user
with zipfile.ZipFile(destination.with_suffix('.project.zip')) as bundle:
    names=bundle.namelist()
    assert 'maps/shared.vmap' in names and 'wavelength-project.json' in names
    assert new['wl_source2_material'] in names
    assert any(name.endswith('_color.png') for name in names)
    assert all(not name.startswith('/') and '..' not in Path(name).parts for name in names)
assert bpy.ops.wavelength.export_map.get_rna_type().properties.get('package_project')
print('PASS relocated prepared materials and portable project ZIP with map, VMAT and texture dependencies',flush=True)
loaded=new.copy();loaded.pop('wl_source2_material',None)
loaded['wl_source_game']='Z:/missing-game';loaded.pop('wl_source_mounts',None)
cube.data.materials[0]=loaded
converted,failures=source2_port_materials.convert_scene(bpy.context,root/'loaded',assign=False)
assert not converted and len(failures)==1
converted,failures=source2_port_materials.convert_scene(bpy.context,root/'loaded',assign=False,use_loaded_textures=True)
assert len(converted)==1 and not failures,failures
assert 'used loaded Blender base-color pixels' in bpy.data.texts['wavelength CS2 Material Conversion'].as_string()
empty=loaded.copy();empty.node_tree.nodes.clear();cube.data.materials[0]=empty
converted,failures=source2_port_materials.convert_scene(bpy.context,root/'empty',assign=False,use_loaded_textures=True)
assert not converted and failures,'Missing pixels must not become a fabricated texture'
print('PASS opt-in loaded texture recovery without game; missing pixels remain failures',flush=True)
from wavelength.source import cross_compile
cube.data.materials[0]=loaded
try:cross_compile.compile_level(bpy.context,root/'maps/cross-strict.vmap','source_hl2_windows','source2_cs2_windows',source_game_dir='Z:/missing-game')
except ValueError as exc:assert 'original Source 1 game is unavailable' in str(exc)
else:raise AssertionError('Missing game fallback must remain optional')
cross_compile.compile_level(bpy.context,root/'maps/cross-loaded.vmap','source_hl2_windows','source2_cs2_windows',source_game_dir='Z:/missing-game',use_loaded_textures=True)
assert (root/'maps/cross-loaded.vmap').is_file()
print('PASS unified cross-compiler forwards optional loaded-texture fallback',flush=True)
