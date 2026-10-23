import sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from wavelength.source.entity import fgd,source_schema


class SourceSchemaTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'bin').mkdir();(self.root/'hl2').mkdir();(self.root/'garrysmod').mkdir()
        (self.root/'bin/base.fgd').write_text('@mapsize(-100,100)\n@BaseClass = Angles [ angles(angle) : "Angles" : "0 0 0" ]\n@BaseClass = Model [ model(*studio) : "Model" spawnflags(flags) = [ 1 : "One" : 1 ] input Skin(integer) : "Skin" output OnDone(void) : "Done" ]\n',encoding='utf-8')
        (self.root/'bin/halflife2.fgd').write_text('@include "base.fgd"\n@PointClass base(Angles,Model) = prop_physics [ spawnflags(flags) = [ 2 : "Two" : 1 ] ]\n@NPCClass base(Angles) = npc_test []\n@SolidClass = func_brush []\n@FilterClass = filter_test []',encoding='utf-8')
        (self.root/'bin/garrysmod.fgd').write_text('@include "halflife2.fgd"\n@PointClass = lua_run []',encoding='utf-8')
    def settings(self,engine='source_hl2_windows'):
        return SimpleNamespace(engine=engine,game_dir=str(self.root/('garrysmod' if 'gmod' in engine else 'hl2')),fgd_path='')
    def test_game_catalogs_are_not_unioned(self):
        hl2=source_schema.definitions(self.settings());gmod=source_schema.definitions(self.settings('source_gmod_windows'))
        self.assertNotIn('lua_run',hl2);self.assertIn('lua_run',gmod)
        self.assertEqual({name for name,_,_ in fgd.entity_classes(hl2)},{'prop_physics','npc_test','func_brush','filter_test'})
    def test_model_inheritance_flags_and_io(self):
        s=self.settings();props={p['key']:p for p in source_schema.properties(s,'prop_physics')}
        self.assertIn('angles',props);self.assertNotIn('Skin',props);self.assertNotIn('OnDone',props)
        self.assertEqual(props['spawnflags']['default'],'3')
        self.assertEqual(source_schema.model_fields(s,'prop_physics')[0]['key'],'model')
        self.assertFalse(source_schema.model_fields(s,'func_brush'))
    def test_included_definition_changes_invalidate_cache(self):
        s=self.settings();source_schema.definitions(s)
        with (self.root/'bin/base.fgd').open('a',encoding='utf-8') as stream:stream.write('\n@PointClass = included_new []')
        self.assertIn('included_new',source_schema.definitions(s))
    def test_missing_game_schema_has_no_shared_starter_fallback(self):
        (self.root/'bin/halflife2.fgd').unlink()
        with self.assertRaises(ValueError):source_schema.definitions(self.settings())
    def test_legacy_game_fgd_encoding(self):
        path=self.root/'legacy.fgd';path.write_bytes('@PointClass = example : "caf\xe9" []'.encode('latin1'))
        self.assertEqual(fgd.load(path)['example']['description'],'caf\xe9')

    def test_entity_representation_is_separate_from_assignable_model(self):
        path=self.root/'representations.fgd'
        path.write_text('@BaseClass studio("models/weapons/w_crowbar.mdl") = Weapon []\n@PointClass base(Weapon) = weapon_crowbar []\n@PointClass base(Weapon) studio("models/custom.mdl") = weapon_custom []\n@PointClass base(Weapon) studio() = dynamic []\n@SolidClass base(Weapon) = func_door []')
        s=self.settings();s.fgd_path=str(path)
        self.assertEqual(source_schema.representation_model(s,'weapon_crowbar'),'models/weapons/w_crowbar.mdl')
        self.assertEqual(source_schema.representation_model(s,'weapon_custom'),'models/custom.mdl')
        self.assertEqual(source_schema.representation_model(s,'weapon_custom',[('model','models/override.mdl')]),'models/override.mdl')
        self.assertFalse(source_schema.representation_model(s,'dynamic'))
        self.assertFalse(source_schema.representation_model(s,'func_door'))
        self.assertFalse(source_schema.model_fields(s,'weapon_crowbar'))

    def test_omitted_defaults_are_empty_and_do_not_consume_next_property(self):
        path=self.root/'empty.fgd'
        path.write_text('@PointClass = door [ targetname(target_source) : "Name" : : "Description" parentname(target_destination) : "Parent" : : "Description" speed(integer) : "Speed" : 100 empty(string) : "Empty" : next(string) : "Next" : "ok" ]')
        props={p['key']:p for p in fgd.properties(fgd.load(path),'door')}
        self.assertEqual(props['targetname']['default'],'')
        self.assertEqual(props['parentname']['default'],'')
        self.assertEqual(props['speed']['default'],'100')
        self.assertEqual(props['empty']['default'],'')
        self.assertEqual(props['next']['default'],'ok')
        settings=self.settings();settings.fgd_path=str(path)
        cleaned=source_schema.export_pairs(settings,[('classname','door'),('targetname',':'),('parentname',':'),('speed','100'),('custom',':')])
        self.assertEqual(cleaned,[('classname','door'),('speed','100'),('custom',':')])
