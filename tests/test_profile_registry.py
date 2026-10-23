import json,sys,tempfile,unittest,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from wavelength.source.profile_registry import Templates,TEMPLATES
from wavelength.source.profile_store import Store,validate

class RegistryTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.store=Store(self.temp.name)
 def tearDown(self):self.temp.cleanup()
 def make(self,name,parent='source_hl2_windows',**settings):
  return self.store.save({'schema':2,'name':name,'parent':parent,'settings':settings})
 def test_game_templates_inherit_source_without_inheriting_hl2(self):
  self.assertIn('source',TEMPLATES.lineage('source_gmod_windows'))
  self.assertNotIn('source_hl2_windows',TEMPLATES.lineage('source_gmod_windows'))
  value=TEMPLATES.resolve('source_gmod_windows')
  self.assertEqual((value['family'],value['format'],value['steam_app_id']),('source','vmf','4000'))
 def test_template_results_are_independent_copies(self):
  value=TEMPLATES.resolve('source_gmod_windows');value['stages'].clear()
  self.assertEqual(TEMPLATES.resolve('source_gmod_windows')['stages'],['vbsp','vvis','vrad'])
 def test_builtins_cannot_be_removed_or_overwritten(self):
  for identity in ('source','source_hl2_windows','godot4'):
   with self.assertRaises(ValueError):self.store.remove(identity)
   with self.assertRaises(ValueError):self.store.save({'schema':2,'id':identity,'name':'Overwrite','parent':'blender','settings':{}})
 def test_child_overrides_and_parent_edits(self):
  parent=self.make('Parent',game_dir='one',grid_step='16')
  child=self.make('Child',parent['id'],grid_step='8')
  raw=self.store.raw(parent['id']);raw['settings']['game_dir']='two';self.store.save(raw)
  resolved=self.store.get(child['id'])
  self.assertEqual(resolved['settings']['game_dir'],'two');self.assertEqual(resolved['settings']['grid_step'],'8')
  self.assertNotIn('game_dir',self.store.raw(child['id'])['settings'])
 def test_dependent_parent_removal_is_blocked(self):
  parent=self.make('Parent');child=self.make('Child',parent['id'])
  with self.assertRaisesRegex(ValueError,'dependent'):self.store.remove(parent['id'])
  self.store.remove(child['id']);self.store.remove(parent['id']);self.assertEqual(self.store.all(),[])
 def test_cycle_rejected_before_parent_file_changes(self):
  parent=self.make('Parent');child=self.make('Child',parent['id']);original=self.store.raw(parent['id'])
  modified=dict(original,parent=child['id'])
  with self.assertRaisesRegex(ValueError,'cycle'):self.store.save(modified)
  self.assertEqual(self.store.raw(parent['id']),original)
 def test_missing_parent_rejected(self):
  with self.assertRaisesRegex(ValueError,'Missing'):self.make('Orphan',str(uuid.uuid4()))
  self.assertEqual(self.store.all(),[])
 def test_legacy_snapshot_migrates_without_changing_uuid_or_settings(self):
  identity=str(uuid.uuid4());value={'schema':1,'id':identity,'name':'Legacy','settings':{'engine':'goldsrc_windows','game_dir':'old'}}
  result=self.store.save(value)
  self.assertEqual(result['id'],identity);self.assertEqual(result['parent'],'goldsrc_windows');self.assertEqual(result['settings']['game_dir'],'old')
 def test_portable_bundle_registers_custom_ancestors(self):
  parent=self.make('Parent',game_dir='custom');child=self.make('Child',parent['id'],grid_step='8')
  bundle=self.store.bundle(child['id'])
  with tempfile.TemporaryDirectory() as folder:
   other=Store(folder);result=other.register(bundle)
   self.assertEqual(len(other.all()),2);self.assertEqual(result['settings']['game_dir'],'custom')
 def test_invalid_bundle_writes_nothing(self):
  good=validate({'schema':2,'name':'Good','parent':'godot4','settings':{}})
  bad=validate({'schema':2,'name':'Bad','parent':str(uuid.uuid4()),'settings':{}})
  with self.assertRaises(ValueError):self.store.register({'schema':2,'profiles':[good,bad],'active':good['id']})
  self.assertEqual(self.store.all(),[])
 def test_parent_backend_cannot_be_silently_replaced(self):
  with self.assertRaisesRegex(ValueError,'backend'):self.make('Wrong',engine='godot4')
 def test_template_cycles_rejected(self):
  path=Path(self.temp.name)/'templates.json';path.write_text(json.dumps({'schema':1,'templates':{'a':{'parent':'b'},'b':{'parent':'a'}}}))
  with self.assertRaisesRegex(ValueError,'cycle'):Templates(path)
if __name__=='__main__':unittest.main()
