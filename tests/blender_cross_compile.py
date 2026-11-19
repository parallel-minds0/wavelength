"""Cross-compile the real Source 1 map without switching its authoring profile."""
import sys,json,collections,zipfile,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import vmf,scene,cross_compile,source2_dmx,source2_map
s=bpy.context.scene.wavelength;s.engine='source_hl2_windows';s.unit_scale=.0254
s.game_dir='C:/Program Files (x86)/Steam/steamapps/common/Half-Life 2/hl2_complete'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete()
doc=vmf.parse(Path('C:/Users/user/Projects/port-now/a-mazing_d.vmf').read_text(encoding='utf-8-sig'))
scene.import_map(bpy.context.scene,doc,defer_assets=False)
spawns=[o for o in bpy.context.scene.objects if o.get('wl_role')=='ENTITY' and dict(json.loads(o.get('wl_pairs','[]'))).get('classname')=='info_player_terrorist']
spawns[0].location.x+=.254;spawns[0].rotation_euler.z=.5
expected_origin=tuple(v/.0254 for v in spawns[0].matrix_world.translation)
bpy.context.view_layer.update()
before={o.name:(tuple(tuple(r) for r in o.matrix_world),o.get('wl_pairs')) for o in bpy.context.scene.objects}
root=Path(__file__).resolve().parents[1]/'build/cross-compile';path=root/'maps/a-mazing.vmap'
count,warnings=cross_compile.compile_level(bpy.context,path,'source_hl2_windows','source2_cs2_windows',package=True)
assert s.engine=='source_hl2_windows' and 'Half-Life 2' in s.game_dir
document=source2_dmx.loads(path.read_text());world=document.get('world')
entities=[c for c in world.get('children') if c.kind=='CMapEntity']
classes=collections.Counter(e.get('entity_properties').get('classname') for e in entities)
assert classes['info_player_terrorist']==9 and classes['info_player_counterterrorist']==9,classes
assert classes['func_buyzone']==2 and classes['func_bomb_target']==2,classes
assert not classes['prop_static'] and not classes['prop_door_rotating']
for e in entities:
 if e.get('entity_properties').get('classname') in {'func_buyzone','func_bomb_target'}:assert e.get('children')
moved=next(e for e in entities if e.get('name')==spawns[0].name)
actual=moved.get('origin');expected=tuple(v/.0254 for v in spawns[0].matrix_world.translation)
assert max(abs(a-b) for a,b in zip(actual,expected))<.001
assert abs(moved.get('angles')[1]-math.degrees(.5))<.001
report=json.loads(path.with_suffix('.crosscompile.json').read_text())
assert any(e['status']=='manual' and e['source_class']=='prop_static' and e['source_pairs'] for e in report['entities'])
with zipfile.ZipFile(path.with_suffix('.project.zip')) as bundle:assert 'maps/a-mazing.crosscompile.json' in bundle.namelist()
assert before=={o.name:(tuple(tuple(r) for r in o.matrix_world),o.get('wl_pairs')) for o in bpy.context.scene.objects}
assert bpy.ops.wavelength.cross_compile.get_rna_type().properties.get('target_profile')
assert bpy.ops.wavelength.cross_compile('EXEC_DEFAULT',filepath=str(root/'maps/operator.vmap'),source_profile='source_hl2_windows',target_profile='source2_cs2_windows')=={'FINISHED'}
from wavelength.source import profile_ui,profile_store,mesh_assets
store=profile_store.Store(root/'test-profiles')
profile=store.save({'schema':2,'id':'4b1023d1-2c54-4456-a339-50d498ec71b5','name':'Cross compile target test','parent':'source2_cs2_windows','settings':{**mesh_assets.defaults('source2_cs2_windows'),'grid_step':16}})
original_store=profile_ui.store;profile_ui.store=lambda:store
try:
 custom=root/'maps/inherited.vmap'
 cross_compile.compile_level(bpy.context,custom,'source_hl2_windows',profile['id'])
 assert json.loads(custom.with_suffix('.crosscompile.json').read_text())['target_profile']==profile['id']
 assert source2_dmx.loads(custom.read_text()).get('gridspacing')==16
finally:profile_ui.store=original_store
for material in bpy.data.materials:
 if material.get('wl_asset_profile','').startswith('source_'):
  material.pop('wl_source_game',None);material.pop('wl_source_mounts',None)
s.engine='source2_cs2_windows'
s.game_dir=mesh_assets.defaults('source2_cs2_windows')['game_dir']
s.compiler_dir=mesh_assets.defaults('source2_cs2_windows')['compiler_dir']
cross_compile.compile_level(bpy.context,root/'maps/recovered-source.vmap','source_hl2_windows','source2_cs2_windows')
assert (root/'maps/recovered-source.vmap').is_file()
assert bpy.ops.wavelength.cross_compile.get_rna_type().properties.get('use_loaded_textures')
from types import SimpleNamespace
from wavelength.source import ui
class Layout:
 def __init__(self):self.operators=[]
 def operator(self,name,**kwargs):self.operators.append(name);return SimpleNamespace()
 def row(self,**kwargs):return self
 def prop(self,*args,**kwargs):pass
layout=Layout();ui.WL_PT_project.draw(SimpleNamespace(layout=layout),bpy.context)
assert 'wavelength.cross_compile' in layout.operators
assert 'wavelength.convert_source2_materials' not in layout.operators and 'wavelength.repair_source2_projection' not in layout.operators
print('PASS cross-profile dispatch, 18 spawns, four brush entities, edited poses, report/package, unchanged source scene',count,dict(classes),flush=True)
