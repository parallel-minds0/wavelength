import sys,collections
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import vmf,scene,source2_map,source2_dmx,source2_port_materials,geometry
s=bpy.context.scene.wavelength;s.engine='source_hl2_windows';s.unit_scale=.0254
s.game_dir='C:/Program Files (x86)/Steam/steamapps/common/Half-Life 2/hl2_complete'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete()
doc=vmf.parse(Path('C:/Users/user/Projects/port-now/a-mazing_d.vmf').read_text(encoding='utf-8-sig'))
scene.import_map(bpy.context.scene,doc,defer_assets=False)
s.engine='source2_cs2_windows';s.game_dir='C:/Program Files (x86)/Steam/steamapps/common/Counter-Strike Global Offensive/game/csgo'
s.compiler_dir=str(Path(s.game_dir).parent/'bin/win64')
root=Path(__file__).resolve().parents[1]/'build/source2-tool-port'
path=root/'maps/a-mazing.vmap'
count,warnings=source2_map.export(bpy.context,path)
document=source2_dmx.loads(path.read_text());materials=collections.Counter();points=[]
for child in document.get('world').get('children'):
 if child.kind!='CMapMesh':continue
 verts,faces,uvs,mats,indices=source2_dmx.read_mesh(child.get('meshData'))
 geometry.validate(verts,faces);points.extend(verts)
 materials.update(mats[i] for i in indices)
assert materials['materials/tools/toolsskybox.vmat']>0
hint=next(c for c in document.get('world').get('children') if c.kind=='CMapEntity' and c.get('entity_properties').get('classname')=='visibility_hint')
assert hint.get('entity_properties').get('classname')=='visibility_hint'
assert hint.get('entity_properties').get('hintType')=='8'
mins=list(map(float,hint.get('entity_properties').get('box_mins').split()))
maxs=list(map(float,hint.get('entity_properties').get('box_maxs').split()))
assert all(mins[i]<min(p[i] for p in points) and maxs[i]>max(p[i] for p in points) for i in range(3))
count_native,_=source2_map.export(bpy.context,root/'maps/native.vmap',visibility='NATIVE')
native=source2_dmx.loads((root/'maps/native.vmap').read_text())
assert count_native==count and not any(c.kind=='CMapEntity' and c.get('entity_properties').get('classname')=='visibility_hint' for c in native.get('world').get('children'))
assert bpy.ops.wavelength.export_map.get_rna_type().properties['visibility_quality'].default=='LOWER64'
trigger=bpy.data.materials.new('trigger mapping test');trigger['wl_texture']='tools/toolstrigger'
assert source2_port_materials.tool_material(trigger)=='materials/tools/toolstrigger.vmat'
assert not any('toolsskybox' in p.name or 'toolstrigger' in p.name for p in root.rglob('*.png'))
# Previously converted tool materials must recover native compiler semantics.
original=next(m for m in bpy.data.materials if m.get('wl_texture')=='tools/toolsskybox')
old=bpy.data.materials.new('old converted sky');old['wl_texture']='wavelength/old/sky';old['wl_source2_material']='materials/wavelength/old/sky.vmat';old['wl_source1_original']=original.name
assert source2_port_materials.tool_material(old)=='materials/tools/toolsskybox.vmat'
print('PASS real map export: native tool materials, closed consistent mesh topology, legacy converted tool recovery',count,dict(materials),flush=True)
print('BOUNDS',[[min(p[i] for p in points) for i in range(3)],[max(p[i] for p in points) for i in range(3)]],flush=True)
