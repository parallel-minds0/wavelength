"""Actual FGD-defined Source entity world meshes, independent of model fields."""
exec(compile((__import__('pathlib').Path(__file__).parent/'blender_custom_model_build.py').read_text().split('bpy.ops.mesh.primitive_cube_add')[0],__file__,'exec'))
from wavelength.source.entity import source_schema,browser
from wavelength.source import model_browser,asset_index
def check(entity,path):
    children=[c for c in entity.children if c.get('wl_model_reference')]
    assert len(children)==1 and children[0].type=='MESH' and children[0].data.polygons
    assert children[0]['wl_source_model'].lower()==path.lower()
    assert children[0]['wl_exclude'] and not children[0].hide_select
    assert not dict(json.loads(entity['wl_pairs'])).get('model'),'Implicit preview must not change engine properties'
    return children[0]
crowbar=_spawn_point_entity(ctx,'weapon_crowbar')
visual=check(crowbar,'models/weapons/w_crowbar.mdl')
crowbar.select_set(False);visual.select_set(True);ctx.view_layer.objects.active=visual;model_browser._tick_context()
assert ctx.view_layer.objects.active==crowbar,'Selecting a fixed-model preview must select its entity'
other=_spawn_point_entity(ctx,'weapon_crowbar');assert check(other,'models/weapons/w_crowbar.mdl').data==visual.data
check(_spawn_point_entity(ctx,'weapon_pistol'),'models/weapons/w_pistol.mdl')
check(_spawn_point_entity(ctx,'item_healthkit'),'models/items/healthkit.mdl')
assert not source_schema.model_fields(s,'weapon_crowbar')
# Reload recovery uses the same FGD resolver without adding properties.
bpy.data.objects.remove(visual,do_unlink=True);model_browser.loaded(None)
while model_browser._representation_queue:model_browser._tick_context()
check(crowbar,'models/weapons/w_crowbar.mdl')
print('PASS actual crowbar/pistol/healthkit viewport geometry, shared meshes, no fake model properties, and missing-reference recovery',flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(folder/'entity-world-models.blend'))
