exec(compile((__import__('pathlib').Path(__file__).parent/'blender_custom_model_build.py').read_text().split('bpy.ops.mesh.primitive_cube_add')[0],__file__,'exec'))
from wavelength.source import goldsrc_import,goldsrc_model,context_policy,model_browser
s.engine='goldsrc_windows'
assets=goldsrc_model.Assets(s.game_dir)
assert goldsrc_model.renderable(assets,'models/player.mdl')
assert not goldsrc_model.renderable(assets,'models/playert.mdl')
assert not goldsrc_model.renderable(assets,'models/scientist01.mdl')
for classname in sorted(goldsrc_import.PLAYER_MARKERS):
    entity=_spawn_point_entity(ctx,classname)
    reference=next(c for c in entity.children if c.get('wl_goldsrc_reference'))
    assert reference.type=='MESH' and reference.data.polygons
    assert context_policy.role(reference,s.engine)=='HELPER'
    assert abs(min(v.co.z for v in reference.data.vertices)+reference.location.z)<1e-5
    assert not dict(json.loads(entity['wl_pairs'])).get('model')
    assert not model_browser.needs_representation(ctx.scene,entity)
print('PASS HL1 player starts/coop/deathmatch/teleport use actual installed player geometry, remain editor helpers and do not write model properties; companion MDLs excluded',flush=True)
