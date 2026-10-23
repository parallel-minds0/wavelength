exec(compile((__import__('pathlib').Path(__file__).parent/'blender_goldsrc_entity_models.py').read_text(),__file__,'exec'))
from wavelength.source import model_browser,asset_index
ctx=bpy.context;s=ctx.scene.wavelength;s.auto_prepare_assets=False
model_browser.schedule(ctx,force=True)
while model_browser._queue:model_browser.publish_batch()
choices=[o for o in bpy.data.objects if o.get('wl_model_choice') and o.asset_data]
assert any(o['wl_source_model']=='models/w_crowbar.mdl' for o in choices)
entity=_spawn_point_entity(ctx,'cycler')
assert model_browser.target(ctx)[0]==entity
model_browser.assign(ctx,asset_index.record(s.engine,'models/w_crowbar.mdl'))
assert dict(json.loads(entity['wl_pairs']))['model']=='models/w_crowbar.mdl'
assert any(c.get('wl_goldsrc_reference') and c.data.polygons for c in entity.children)
print('PASS GoldSrc Models catalog indexes the installed game and assigns the selected MDL to a model-capable entity',flush=True)
