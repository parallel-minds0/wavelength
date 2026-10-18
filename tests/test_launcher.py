import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from wavelength.source import launcher


class SteamDiscoveryTests(unittest.TestCase):
    def test_explicit_launcher_without_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            steam=Path(tmp)/'Steam.exe';steam.touch()
            with patch.object(launcher,'registry_paths',return_value=[]),patch.object(launcher.shutil,'which',return_value=None):
                self.assertEqual(launcher.find_steam(str(steam)),str(steam))

    def test_registry_install_folder_without_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            steam=Path(tmp)/('steam.exe' if launcher.os.name=='nt' else 'steam');steam.touch()
            with patch.object(launcher,'registry_paths',return_value=[tmp]),patch.object(launcher.shutil,'which',return_value=None):
                self.assertEqual(launcher.find_steam(),str(steam))

    def test_game_executable_is_not_treated_as_steam(self):
        with tempfile.TemporaryDirectory() as tmp:
            game=Path(tmp)/'hl2.exe';game.touch()
            steam=Path(tmp)/'Steam.exe';steam.touch()
            with patch.object(launcher,'registry_paths',return_value=[str(steam)]),patch.object(launcher.shutil,'which',return_value=None):
                self.assertEqual(launcher.find_steam(str(game)),str(steam))

    def test_missing_launcher_gives_configuration_action(self):
        with patch.object(launcher,'registry_paths',return_value=[]),patch.object(launcher.shutil,'which',return_value=None),patch.object(Path,'is_file',return_value=False):
            with self.assertRaisesRegex(ValueError,'Game Executable'):launcher.find_steam()
