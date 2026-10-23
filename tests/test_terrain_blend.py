import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from wavelength.source import terrain_blend as blend,keyvalues
class TerrainBlendTests(unittest.TestCase):
    def test_two_material_recipe_and_normal_maps(self):
        a={'$basetexture':'materials/BRICK/red.vtf','$surfaceprop':'brick','$bumpmap':'brick/red_normal'}
        b={'$basetexture':'ground/dirt','$bumpmap':'ground/dirt_normal'}
        name,text=blend.recipe(a,b)
        shader,values=keyvalues.parse(text)[0];values=dict(values)
        self.assertEqual(shader,'WorldVertexTransition')
        self.assertEqual(values['$basetexture'],'brick/red');self.assertEqual(values['$basetexture2'],'ground/dirt')
        self.assertEqual(values['$bumpmap2'],'ground/dirt_normal');self.assertEqual(blend.recipe(a,b),(name,text))
    def test_project_and_game_staging_is_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);game=root/'game';game.mkdir();(game/'gameinfo.txt').write_text('GameInfo {}')
            name,text=blend.recipe({'$basetexture':'a'},{'$basetexture':'b'})
            paths=blend.stage(game,root/'project',name,text)
            self.assertEqual(paths,blend.stage(game,root/'project',name,text))
            self.assertTrue(all(p.read_text()==text for p in paths))
            paths[1].write_text('user content')
            with self.assertRaises(ValueError):blend.stage(game,root/'project',name,text)
            self.assertEqual(paths[1].read_text(),'user content')
    def test_invalid_references_and_mismatched_identity_rejected(self):
        for value in ['../outside','a"b','a\nb','/absolute']:
            with self.assertRaises(ValueError):blend.recipe({'$basetexture':value},{'$basetexture':'ok'})
        with self.assertRaises(ValueError):blend.stage('.', '.', 'other/material','text')
