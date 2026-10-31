import bpy,sys,json,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
import wavelength
wavelength.register()
from wavelength.source import model_browser as mb,asset_loading,asset_index
from wavelength.source.entity import models
c=bpy.context;c.preferences.use_preferences_save=False;c.workspace['wl_workspace']=True
s=c.scene.wavelength;s.engine='source_hl2_windows';s.game_dir=r'C:\Program Files (x86)\Steam\steamapps\common\Half-Life 2\hl2_complete';s.fgd_path=''
c.scene['wl_source_blender_rendering']=True
entity=bpy.data.objects.new('Model replacement',None);c.collection.objects.link(entity)
first='models/props_c17/oildrum001.mdl';second='models/props_junk/wood_crate001a.mdl'
entity['wl_role']='ENTITY';entity['wl_pairs']=json.dumps([['classname','prop_dynamic'],['model',first]])
assert models.attach_reference(entity)
old=next(o for o in entity.children if o.get('wl_model_reference'))
assert old.type=='MESH'
old.select_set(True);c.view_layer.objects.active=old
mb.assign(c,asset_index.record(s.engine,second))
assert old.name in bpy.data.objects,'Old preview deleted before replacement ready'
assert entity.get('wl_representation_pending')
start=time.monotonic()
while asset_loading._waiting:
 asset_loading.tick();time.sleep(.03)
 assert time.monotonic()-start<60
refs=[o for o in entity.children if o.get('wl_model_reference')]
assert len(refs)==1 and refs[0].type=='MESH' and refs[0]['wl_source_model']==second
assert c.view_layer.objects.active==entity
mb.watch_model(c.scene,entity)
values=json.loads(entity['wl_pairs']);entity['wl_pairs']=json.dumps([[k,first if k=='model' else v] for k,v in values])
mb.watch_model(c.scene,entity)
assert entity.get('wl_representation_pending')
# Rapid edits leave exactly the newest waiter for this entity.
entity['wl_pairs']=json.dumps([[k,second if k=='model' else v] for k,v in values]);mb.watch_model(c.scene,entity)
assert sum(waiter[1]==entity for key,waiter in asset_loading._waiting)==1
start=time.monotonic()
while asset_loading._waiting:
 asset_loading.tick();time.sleep(.03)
 assert time.monotonic()-start<60
refs=[o for o in entity.children if o.get('wl_model_reference')]
assert len(refs)==1 and refs[0].type=='MESH' and refs[0]['wl_source_model']==second
last=refs[0]
entity['wl_pairs']=json.dumps([['classname','prop_dynamic'],['model','models/does_not_exist.mdl']])
asset_loading.entity(c.scene,entity)
start=time.monotonic()
while asset_loading._waiting:
 asset_loading.tick();time.sleep(.03)
 assert time.monotonic()-start<60
assert last.name in bpy.data.objects and entity.get('wl_model_error')
assert not entity.get('wl_representation_pending')
asset_loading.clear()
print('PASS prepared Source model replacements remain real meshes; old model retained until ready; selected-child deletion transfers active entity; property edits autoqueue; rapid requests coalesce',flush=True)

