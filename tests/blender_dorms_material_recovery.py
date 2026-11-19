import sys,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import scene,vmf,native_source,render_support,source2_port_materials,source2_map,cross_compile,editor,source_assets,profile_ui,textures,source2_dmx,mesh_assets
s=bpy.context.scene.wavelength;s.auto_prepare_assets=False;s.engine='source_csgo_legacy_windows'
s.game_dir='C:/Program Files (x86)/Steam/steamapps/common/Counter-Strike Global Offensive/csgo'
s.unit_scale=.0254
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete()
doc=vmf.parse(Path('C:/Users/user/Projects/port-now/de_dorms_d.vmf').read_text(encoding='utf-8-sig'))
scene.import_map(bpy.context.scene,doc,defer_assets=False)
materials={m for o in bpy.context.scene.objects if o.type=='MESH' for m in o.data.materials if m and m.get('wl_texture')}
assert len(materials)==63
assert all(m.get('wl_source_cache_key') for m in materials),[m.name for m in materials if not m.get('wl_source_cache_key')]
original_uvs={o.name:[tuple(d.uv) for d in o.data.uv_layers.active.data] for o in bpy.context.scene.objects if o.type=='MESH' and o.data.get('wl_faces') and any(m and (m.get('wl_width',64)!=64 or m.get('wl_height',64)!=64) for m in o.data.materials)}
# Reproduce a saved map's failed placeholder state without changing texture IDs.
for m in materials:
 m.pop('wl_source_cache_key',None);m.pop('wl_source_native_material',None);m['wl_asset_error']='Old missing material'
 m['wl_width']=64;m['wl_height']=64
for name in original_uvs:editor.apply_uv(bpy.context.scene.objects[name],s.engine)
with patch.object(render_support,'prepare',return_value=False):
 assert native_source.recover_missing_materials(bpy.context.scene)==63
assert all(m.get('wl_source_native_material') and not m.get('wl_asset_error') for m in materials)
for name,expected in original_uvs.items():
 actual=[tuple(d.uv) for d in bpy.context.scene.objects[name].data.uv_layers.active.data]
 assert max(abs(a-b) for x,y in zip(actual,expected) for a,b in zip(x,y))<.0001,name
assert native_source.recover_missing_materials(bpy.context.scene)==0,'Must not repeatedly rebuild healed materials'
clip=next(m for m in materials if m['wl_texture']=='tools/toolsclip_concrete')
warnings=[];assert source2_port_materials.tool_material(clip,warnings)=='materials/tools/toolsclip.vmat'
assert warnings and 'surface-specific' in warnings[0]
clip.pop('wl_source_cache_key',None);clip.pop('wl_source_native_material',None)
with patch.object(render_support,'prepare',return_value=False):native_source.migrate(bpy.context.scene)
assert clip.get('wl_source_native_material')=='tools/toolsclip_concrete'
clip.pop('wl_source_cache_key',None);clip.pop('wl_source_native_material',None)
with patch.object(render_support,'prepare',return_value=False),patch.object(textures,'refresh'):
 profile_ui.apply(bpy.context,profile_ui.store().get('source_csgo_legacy_windows'))
assert clip.get('wl_source_native_material')=='tools/toolsclip_concrete','Profile application did not retry placeholders'
bpy.context.scene['wl_source_blender_rendering']=True
for name in ('plaster/urban_plasterwall_05f','de_nuke/nuke_metalfloor_01','concrete/baggage_concretefloora'):
 mat=next(m for m in materials if m['wl_texture']==name)
 source_assets.material(s,name,target_mat=mat)
 assert any(n.type=='TEX_IMAGE' and n.image and n.image.has_data for n in mat.node_tree.nodes),name
output=Path(__file__).resolve().parents[1]/'build/dorms-recovery/maps/de_dorms.vmap'
count,warnings=cross_compile.compile_level(bpy.context,output,'source_csgo_legacy_windows','source2_cs2_windows')
assert count>0 and 'materials/tools/toolsclip.vmat' in output.read_text()
assert any('toolsclip_concrete' in w and 'surface-specific' in w for w in warnings)
assert not any('placeholder' in w for w in warnings)
root=source2_dmx.loads(output.read_text());children=root.get('world').get('children')
exported={c.get('name'):c for c in children if c.kind=='CMapMesh'}
details=[o for o in bpy.context.scene.objects if o.type=='MESH' and dict(json.loads(o.get('wl_entity_pairs','[]'))).get('classname')=='func_detail']
assert len(details)==85 and all(o.name in exported and exported[o.name].get('visexclude') for o in details)
world=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.data.get('wl_faces') and not o.get('wl_entity_id')]
assert len(world)==492 and all(o.name in exported for o in world),'Lost structural or utility brushes'
assert not any(c.kind=='CMapEntity' and dict((k,v) for k,(_,v) in c.get('entity_properties').attrs.items()).get('classname')=='func_detail' for c in children)
checked=0
for obj in world+details:
    data=exported[obj.name].get('meshData');_,faces,corners,_,_=source2_dmx.read_mesh(data)
    records=json.loads(obj.data['wl_faces']);ids=obj.data.attributes['wl_face_id']
    scales=source2_dmx.stream_data(data,'faceData','textureScale:0')
    axis_u=source2_dmx.stream_data(data,'faceData','textureAxisU:0');axis_v=source2_dmx.stream_data(data,'faceData','textureAxisV:0')
    for face in obj.data.polygons:
        record=records[str(ids.data[face.index].value)]
        assert all(abs(a-b)<1e-5 for a,b in zip(scales[face.index],record['projection'][3:])),obj.name
        assert max(abs(a-b) for actual,wanted in zip((axis_u[face.index],axis_v[face.index]),record['axes']) for a,b in zip(actual,wanted))<1e-5,obj.name
    expected=[(uv.uv.x,1-uv.uv.y) for uv in obj.data.uv_layers.active.data]
    actual=[uv for face in corners for uv in face]
    assert max(abs(a-b) for x,y in zip(actual,expected) for a,b in zip(x,y))<.0001,obj.name
    checked+=len(faces)
# Explicit exclusions still win over automatic utility inclusion.
utility=next(o for o in world if o not in mesh_assets.candidates(bpy.context))
utility.hide_render=True
assert utility not in mesh_assets.candidates(bpy.context,include_brush_utilities=True)
utility.hide_render=False
print('PASS dorms: all materials, 85 VIS-excluded detail brushes, 492 world/utility brushes, native face projection and',checked,'UV faces; export meshes',count,flush=True)
