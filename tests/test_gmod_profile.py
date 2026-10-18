import sys,unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from wavelength.source import profiles,source_tools,profile_store


class GmodProfileTests(unittest.TestCase):
    def test_source_profile_has_correct_steam_app(self):
        profile=profiles.get('source_gmod_windows')
        self.assertTrue(profiles.is_source('source_gmod_windows'))
        self.assertEqual(profile['steam_app_id'],'4000')
        self.assertEqual(profile['stages'],['vbsp','vvis','vrad'])
        profile_store.validate({'name':'Gmod','settings':{'engine':'source_gmod_windows'}})

    def test_defaults_find_gmod_tools_and_fgd(self):
        with tempfile.TemporaryDirectory() as temporary:
            home=Path(temporary);root=home/'.local/share/Steam/steamapps/common/GarrysMod'
            game=root/'garrysmod';game.mkdir(parents=True);(game/'gameinfo.txt').touch()
            tool=root/'bin/win64';tool.mkdir(parents=True);(tool/'vbsp.exe').touch()
            (root/'bin/garrysmod.fgd').touch()
            with patch.object(Path,'home',return_value=home),patch.object(source_tools.os,'environ',{'PROGRAMFILES(X86)':str(home/'missing')}):
                settings=source_tools.defaults('windows',engine='source_gmod_windows')
            self.assertEqual(Path(settings['game_dir']),game)
            self.assertEqual(Path(settings['compiler_dir']),tool)
            self.assertEqual(Path(settings['fgd_path']),root/'bin/garrysmod.fgd')
            self.assertIn('+map',json.loads(settings['launch_args']))
