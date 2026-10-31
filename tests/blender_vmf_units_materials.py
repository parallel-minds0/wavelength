"""VMF native-unit round trips and Source material/UV realization."""
import sys,tempfile,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,wavelength
from mathutils import Vector
wavelength.register()
from wavelength.source import vmf,formats,scene,profiles,model_formats
root=Path(__file__).resolve().parents[1]
c=bpy.context;s=c.scene.wavelength
with tempfile.TemporaryDirectory() as temp:
 folder=Path(temp);game=folder/'game';(game/'materials/test').mkdir(parents=True)
 (game/'gameinfo.txt').write_text('GameInfo { FileSystem { SearchPaths { game "|gameinfo_path|." } } }')
 (game/'materials/test/wall.vmt').write_text('LightmappedGeneric { "$basetexture" "test/wall" }')
 (game/'materials/test/wall.vtf').write_bytes(model_formats.vtf(4,4,bytes([30,100,200,255])*16))
 doc=vmf.parse((root/'addon/wavelength/environment/maps/minimal_source.vmf').read_text())
 for e in doc.entities:
  for b in e.brushes:
   for f in b:f.texture='test/wall'
 doc.entities.append(formats.Entity([('classname','info_target'),('origin','128 -64 192')],[]))
 path=folder/'units.vmf';path.write_text(vmf.write(doc))
 s.engine='source_hl2_windows';s.game_dir=str(game);s.engine='blender'
 assert profiles.unit_meters(s)==1
 assert bpy.ops.wavelength.import_map(filepath=str(path))=={'FINISHED'}
 assert s.engine=='source_hl2_windows' and s.game_dir==str(game)
 unit=profiles.unit_meters(s)
 expected=[v for e in doc.entities for b in e.brushes for v in formats.brush_mesh(b)[0]]
 brushes=[o for o in c.scene.objects if o.get('wl_role')=='BRUSH']
 actual=[tuple(o.matrix_world@v.co/unit) for o in brushes for v in o.data.vertices]
 for axis in range(3):
  assert abs(min(v[axis] for v in actual)-min(v[axis] for v in expected))<1e-3
  assert abs(max(v[axis] for v in actual)-max(v[axis] for v in expected))<1e-3
 for obj in brushes:
  assert abs(obj['wl_unit_meters']-unit)<1e-9
  uv=obj.data.uv_layers['wavelength']
  assert uv and len({tuple(v.uv) for v in uv.data})>1
  for mat in obj.data.materials:
   assert mat.get('wl_realized') and mat['wl_width']==4 and mat['wl_height']==4
   assert any(n.type=='TEX_IMAGE' and n.image for n in mat.node_tree.nodes)
 target=next(o for o in c.scene.objects if o.get('wl_role')=='ENTITY' and dict(json.loads(o['wl_pairs'])).get('classname')=='info_target')
 assert (target.location-Vector((128,-64,192))*unit).length<1e-5
 def bounds(document):
  pts=[v for e in document.entities for b in e.brushes for v in formats.brush_mesh(b)[0]]
  return [(min(v[i] for v in pts),max(v[i] for v in pts)) for i in range(3)]
 exported=scene.export_map(c.scene)
 for before,after in zip(bounds(doc),bounds(exported)):
  assert max(abs(a-b) for a,b in zip(before,after))<1e-3,(before,after)
 out=vmf.parse(vmf.write(exported))
 assert bounds(out)==bounds(exported)
 assert dict(next(e for e in out.entities if dict(e.pairs).get('classname')=='info_target').pairs)['origin']=='128 -64 192'
 # Changing the authoring grid/unit setting must not rescale existing export data.
 s.unit_scale=unit*2
 assert bounds(scene.export_map(c.scene))==bounds(exported)
 print('PASS VMF: profile before import, Source materials and UVs, internal profile scale, native brush/entity export units, stored-unit stability',flush=True)
