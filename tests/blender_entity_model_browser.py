import sys,json,time
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'addon'))
import bpy,addon_utils
addon_utils.enable('wavelength',default_set=False)
from wavelength.source import model_browser,asset_index,asset_browser
from wavelength.source.entity import catalog,source_schema,fgd
from wavelength.source.ui import _spawn_point_entity,_entity_creation_defaults
ctx=bpy.context;ctx.preferences.use_preferences_save=False;ctx.workspace['wl_workspace']=True
s=ctx.scene.wavelength;s.engine='source_hl2_windows';s.game_dir=r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life 2\hl2_complete';s.fgd_path=''
folder=root/'build/entity-model-browser';folder.mkdir(exist_ok=True)
s.project_dir=str(folder)
names={n for n,_,_ in catalog.items(s,ctx)}
assert len(names)==461 and {'npc_citizen','prop_physics','prop_ragdoll','filter_activator_class','func_brush'}<=names
assert not {'lua_run','env_skypaint'}&names
assert not {'Angles','Studiomodel','BaseNPC'}&names
assert source_schema.model_fields(s,'prop_physics') and source_schema.model_fields(s,'prop_ragdoll')
assert source_schema.model_fields(s,'env_shooter')[0]['key']=='shootmodel'
assert not source_schema.model_fields(s,'light') and not source_schema.model_fields(s,'func_brush')
assert not any(p['key']=='SetAnimation' for p in source_schema.properties(s,'prop_dynamic'))
print('PASS complete installed HL2 schema includes NPC/filter/move classes; model capability uses inherited property types',flush=True)
prop=_spawn_point_entity(ctx,'prop_physics');original=prop.as_pointer();model_browser.tick()
assert s.asset_browser_section=='MODELS' and model_browser.target()[0]==prop
assert model_browser._queue
deadline=time.monotonic()+30
while model_browser._queue and time.monotonic()<deadline:model_browser.publish_batch()
assert not model_browser._queue
choices=[o for o in bpy.data.objects if o.get('wl_model_choice') and o.asset_data]
assert len(choices)>500 and all(o.asset_data.catalog_id==model_browser.CATALOG for o in choices)
model_browser.assign(ctx,asset_index.record(s.engine,'models/props_c17/oildrum001.mdl'))
assert prop.as_pointer()==original and dict(json.loads(prop['wl_pairs']))['classname']=='prop_physics'
assert len([c for c in prop.children if c.get('wl_model_reference')])==1
assert not prop.get('wl_exclude')
model_browser.assign(ctx,asset_index.record(s.engine,'models/props_junk/wood_crate001a.mdl'))
assert len([c for c in prop.children if c.get('wl_model_reference')])==1
assert len([o for o in ctx.scene.objects if o.get('wl_role')=='ENTITY' and not o.get('wl_exclude')])==1
choice=next(o for o in choices if o.get('wl_source_model')=='models/props_c17/oildrum001.mdl')
asset_browser._BUSY=True
try:
    clone=choice.copy();ctx.collection.objects.link(clone);prop.select_set(False);clone.select_set(True);ctx.view_layer.objects.active=clone;clone_name=clone.name
    ctx.view_layer.update()
finally:asset_browser._BUSY=False
from types import SimpleNamespace
asset_browser.dropped(ctx.scene,SimpleNamespace(updates=[SimpleNamespace(id=clone)]))
assert clone_name not in ctx.scene.objects and ctx.view_layer.objects.active==prop
assert dict(json.loads(prop['wl_pairs']))['model']=='models/props_c17/oildrum001.mdl'
assert len([c for c in prop.children if c.get('wl_model_reference')])==1
print('PASS model assets publish incrementally; choosing models changes the selected physics entity without spawning another entity',flush=True)
print('PASS dropped model asset updates the previous entity target and removes its temporary template',flush=True)
light=_spawn_point_entity(ctx,'light');model_browser.tick();assert s.asset_browser_section!='MODELS'
try:model_browser.assign(ctx,asset_index.record(s.engine,'models/props_junk/wood_crate001a.mdl'))
except ValueError:pass
else:raise AssertionError('Model was assigned to a light')
print('PASS non-model entities leave model context and reject accidental assignment',flush=True)
shooter=_spawn_point_entity(ctx,'env_shooter');model_browser.tick()
assert s.model_browser_field=='shootmodel'
model_browser.assign(ctx,asset_index.record(s.engine,'models/props_junk/wood_crate001a.mdl'))
assert dict(json.loads(shooter['wl_pairs']))['shootmodel']=='models/props_junk/wood_crate001a.mdl'
assert not any(c.get('wl_model_reference') for c in shooter.children)
print('PASS secondary studio properties assign their own key without changing entity class or adding a false body preview',flush=True)
s.engine='source_gmod_windows';s.game_dir=r'C:\Program Files (x86)\Steam\steamapps\common\GarrysMod\garrysmod'
gmod={n for n,_,_ in catalog.items(s,ctx)}
assert len(gmod)==487 and {'lua_run','env_skypaint'}<=gmod
assert source_schema.model_fields(s,'prop_physics') and source_schema.model_fields(s,'prop_ragdoll')
assert all(p['type'].lower().lstrip('*')=='studio' for p in source_schema.model_fields(s,'prop_physics'))
print('PASS GMod uses its own 487-class catalog and extended *studio model fields; no cross-game union',flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(folder/'model-entity-context.blend'))
