"""Direct installed HL1 MDL entity representations; no glTF dependency."""
exec(compile((__import__('pathlib').Path(__file__).parent/'blender_custom_model_build.py').read_text().split('bpy.ops.mesh.primitive_cube_add')[0],__file__,'exec'))
from wavelength.source import goldsrc_import,goldsrc_model,model_browser
from wavelength.source.entity import models
from mathutils import Vector
s.engine='goldsrc';s.game_dir=r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life\valve'
s.fgd_path=r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life SDK\Hammer Editor\fgd\half-life\halflife.fgd';s.unit_scale=.0254
def visual(entity):
    result=next((c for c in entity.children if c.get('wl_goldsrc_reference')),None)
    assert result is not None,(entity.name,entity.get('wl_model_error'))
    assert result.type=='MESH' and result.data.polygons and result.data.uv_layers
    assert result.scale==Vector((1,1,1)) and result['wl_exclude'] and not result.hide_select
    assert result.data.materials and all(m.use_nodes for m in result.data.materials)
    return result
scientist=_spawn_point_entity(ctx,'monster_scientist');scientist.location=(-1,0,0);reference=visual(scientist)
height=max(v.co.z for v in reference.data.vertices)-min(v.co.z for v in reference.data.vertices)
assert 1.5<height<2,height
clone=_spawn_point_entity(ctx,'monster_scientist');clone.location=(1,0,0);assert visual(clone).data==reference.data
for classname in ('monster_human_grunt','monster_headcrab','weapon_crowbar','item_healthkit'):
    entity=_spawn_point_entity(ctx,classname);visual(entity)
    assert not dict(json.loads(entity['wl_pairs'])).get('model'),'Derived representation must not change map properties'
# A custom body/sequence/skin gets its own decoded variant; the original stays shared.
assets=goldsrc_model.Assets(s.game_dir);variant=goldsrc_model.load(assets,'models/scientist.mdl',body=1)
assert variant['faces'] and 'models/scientistt.mdl' in assets.dependencies
assert any(name.startswith('models/scientist') for name in assets.dependencies)
r=goldsrc_model.Reader(assets.read('models/scientist.mdl')).header()
sequence=next(i for i,p in enumerate(r.block(r.integer(168),r.integer(164),176)) if r.integer(p+156))
goldsrc_model.load(assets,'models/scientist.mdl',sequence=sequence)
assert 'models/scientist01.mdl' in assets.dependencies
legacy=bpy.data.objects.new('Legacy glTF preview',None);ctx.collection.objects.link(legacy)
legacy.parent=scientist;legacy['wl_model_reference']=True
bpy.data.objects.remove(reference,do_unlink=True);model_browser.loaded(None)
while model_browser._representation_queue:model_browser._tick_context()
assert visual(scientist).data==visual(clone).data
assert 'Legacy glTF preview' not in bpy.data.objects
scene_path=folder/'goldsrc-entities.blend';bpy.ops.wm.save_as_mainfile(filepath=str(scene_path));bpy.ops.wm.open_mainfile(filepath=str(scene_path))
assert any(o.get('wl_goldsrc_reference') and o.data.materials for o in bpy.context.scene.objects)
print('PASS installed HL1 direct textured NPC/weapon/item meshes, external textures, bodygroups, shared data, profile scale, recovery and saved references',flush=True)
