import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import vmf,formats,scene,source2_port_materials as port,editor
s=bpy.context.scene.wavelength;s.engine='source_hl2_windows';s.unit_scale=.0254
s.game_dir='C:/Program Files (x86)/Steam/steamapps/common/Half-Life 2/hl2_complete'
doc=vmf.parse(Path('C:/Users/user/Projects/port-now/a-mazing_d.vmf').read_text(encoding='utf-8-sig'))
world=next(e for e in doc.entities if dict(e.pairs).get('classname')=='worldspawn')
scene.import_map(bpy.context.scene,formats.Map([formats.Entity([('classname','worldspawn')],[world.brushes[0]])]),defer_assets=False)
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH' and o.data.get('wl_faces'))
before=[tuple(d.uv) for d in obj.data.uv_layers['wavelength'].data]
root=Path(__file__).resolve().parents[1]/'build/projection-repair'
converted,failures=port.convert_scene(bpy.context,root,assign=True)
assert converted and not failures,failures
editor.apply_uv(obj,s.engine)
after=[tuple(d.uv) for d in obj.data.uv_layers['wavelength'].data]
assert before==after,(before,after)
for mat in converted.values():mat['wl_width']=64;mat['wl_height']=64
editor.apply_uv(obj,s.engine)
assert [tuple(d.uv) for d in obj.data.uv_layers['wavelength'].data]!=before
from wavelength.source import cross_compile,source2_dmx
broken=[tuple(d.uv) for d in obj.data.uv_layers['wavelength'].data]
output=root/'maps/automatic.vmap'
cross_compile.compile_level(bpy.context,output,'source_hl2_windows','source2_cs2_windows')
document=source2_dmx.loads(output.read_text())
child=next(c for c in document.get('world').get('children') if c.kind=='CMapMesh' and c.get('name')==obj.name)
uvs=source2_dmx.read_mesh(child.get('meshData'))[2]
expected=[(u,1-v) for u,v in before]
assert max(abs(a-b) for actual,wanted in zip([p for face in uvs for p in face],expected) for a,b in zip(actual,wanted))<.00001
assert broken==[tuple(d.uv) for d in obj.data.uv_layers['wavelength'].data],'Export repair mutated source UVs'
assert port.repair_projection(bpy.context)>0
assert [tuple(d.uv) for d in obj.data.uv_layers['wavelength'].data]==before
print('PASS real a-mazing brush conversion preserves UV tiling; repair restores prior broken conversions',flush=True)
