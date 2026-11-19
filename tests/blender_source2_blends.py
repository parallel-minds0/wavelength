"""Native two-layer materials, blend weights, source invariance and packaging."""
import sys,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import source_assets,cross_compile,source2_map,source2_dmx,keyvalues,mesh_assets
bpy.context.preferences.use_preferences_save=False
s=bpy.context.scene.wavelength;s.auto_prepare_assets=False;s.engine='source_csgo_legacy_windows'
s.game_dir='C:/Program Files (x86)/Steam/steamapps/common/Counter-Strike Global Offensive/csgo'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete()
mesh=bpy.data.meshes.new('blend');mesh.from_pydata([(0,0,0),(1,0,0),(1,1,0),(0,1,0)],[],[(0,1,2,3)])
obj=bpy.data.objects.new('blend',mesh);bpy.context.scene.collection.objects.link(obj)
uv=mesh.uv_layers.new();uv.data.foreach_set('uv',[0,0,1,0,1,1,0,1])
mesh.attributes.new('wl_terrain_blend','FLOAT','POINT').data.foreach_set('value',[0,.25,.75,1])
material=source_assets.material(s,'asphalt/hr_conc_a_damage_e');mesh.materials.append(material)
root=Path(__file__).resolve().parents[1]/'build/source2-blends';path=root/'maps/blends.vmap'
count,warnings=cross_compile.compile_level(bpy.context,path,s.engine,'source2_cs2_windows',package=True)
document=source2_dmx.loads(path.read_text());node=document.get('world').get('children')[0];data=node.get('meshData')
assert source2_dmx.corner_blend_weights(data)==[[0,.25,.75,1]]
relative=data.get('materials')[0]
props=keyvalues.values(keyvalues.child(keyvalues.parse((root/relative).read_text()),'Layer0'))
assert props['shader']=='csgo_lightmappedgeneric.vfx' and props['f_layers']=='1'
for key in ('texturelayer1color','texturelayer2color','texturelayer1normal','texturelayer2normal','textureblendmodulation'):assert (root/props[key]).is_file(),key
assert obj.data==mesh and mesh.materials[0]==material
with zipfile.ZipFile(path.with_suffix('.project.zip')) as bundle:
 assert props['texturelayer2color'] in bundle.namelist() and props['textureblendmodulation'] in bundle.namelist()
s.engine='source2_cs2_windows';defaults=mesh_assets.defaults(s.engine);s.game_dir=defaults['game_dir'];s.compiler_dir=defaults['compiler_dir']
source2_map.import_map(bpy.context,path)
imported=list(bpy.context.scene.collection.children)[-1].objects[0]
assert list(imported.data.attributes['wl_terrain_blend'].data[i].value for i in range(4))==[0,.25,.75,1]
bpy.ops.object.select_all(action='DESELECT');imported.select_set(True)
source2_map.export(bpy.context,root/'maps/roundtrip.vmap',selected=True)
roundtrip=source2_dmx.loads((root/'maps/roundtrip.vmap').read_text()).get('world').get('children')[0].get('meshData')
assert source2_dmx.corner_blend_weights(roundtrip)==[[0,.25,.75,1]]
print('PASS native Source 2 blend material layers, normals, modulation, vertex weights, import/export roundtrip and package',relative,flush=True)
