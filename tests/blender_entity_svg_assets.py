exec(compile((__import__('pathlib').Path(__file__).parent/'blender_custom_model_build.py').read_text().split('bpy.ops.mesh.primitive_cube_add')[0],__file__,'exec'))
from wavelength.source.entity import icons
from wavelength.source import context_policy,model_browser,studio_model,source_assets
assert len(icons._manifest())>=44
for engine,names in [('goldsrc_windows',['light','info_target','path_corner','ambient_generic']),('source_hl2_windows',['light','info_target','logic_relay','env_soundscape'])]:
    s.engine=engine
    for classname in names:
        entity=_spawn_point_entity(ctx,classname)
        children=[c for c in entity.children if c.get('wl_entity_icon_reference')]
        assert children,(engine,classname,entity.get('wl_model_error'))
        assert all(c.type=='CURVE' and context_policy.role(c,engine)=='HELPER' for c in children)
        assert not model_browser.needs_representation(ctx.scene,entity)
assets=source_assets.Assets(s.game_dir)
assert not studio_model.renderable(assets,'models/advisor_animations.mdl')
assert studio_model.renderable(assets,'models/weapons/w_crowbar.mdl')
from wavelength.source.entity import source_schema
for classname,(old,new) in source_schema.LEGACY_MODELS.items():
    entity=_spawn_point_entity(ctx,classname)
    assert any(c.get('wl_model_reference') for c in entity.children),(classname,entity.get('wl_model_error'))
    actual=source_schema.representation_model(s,classname,json.loads(entity['wl_pairs']))
    assert actual.lower()==new.lower(),(classname,actual,new)
    assert dict(source_schema.export_pairs(s,[('classname',classname),('model',old)]))['model']==new
print('PASS packaged SVG mapping, HL1/HL2 in-world helper curves, stable representation lifecycle and animation-only Source MDL exclusion',flush=True)
