import sys,unittest,tempfile,struct,zlib
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from wavelength.source import profiles,profile_store,source_tools,cross_compile,source_assets


class LegacyProfileTests(unittest.TestCase):
    def test_legacy_profile_is_source1_and_preserves_enum_numbers(self):
        profile=profiles.get('source_csgo_legacy_windows')
        self.assertEqual(profile['parent'],'source_windows')
        self.assertTrue(profiles.is_source('source_csgo_legacy_windows'))
        self.assertEqual(profile['game_folder'],'csgo')
        self.assertEqual(profile['bsp_version'],21)
        self.assertFalse(profile['build_supported'])
        self.assertEqual(profiles.PROFILE_ORDER[-1],'source_csgo_legacy_windows')
        self.assertEqual(profiles.PROFILE_ORDER.index('civ5'),12)
        self.assertEqual(profiles.PROFILE_ORDER.index('source2_cs2_windows'),10)
        self.assertEqual(cross_compile.profile_family('source_csgo_legacy_windows'),'source')
        profile_store.validate({'name':'My legacy install','settings':{'engine':'source_csgo_legacy_windows'}})

    def test_discovery_keeps_legacy_assets_separate_from_cs2(self):
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory);root=home/'.local/share/Steam/steamapps/common/Counter-Strike Global Offensive'
            (root/'csgo').mkdir(parents=True);(root/'csgo/gameinfo.txt').touch()
            (root/'csgo.exe').touch();(root/'bin').mkdir()
            fgd=root/'game/csgo/import_scripts/bin/csgo.fgd';fgd.parent.mkdir(parents=True);fgd.touch()
            with patch.object(Path,'home',return_value=home),patch.object(source_tools.os,'environ',{'PROGRAMFILES(X86)':str(home/'missing')}):
                result=source_tools.defaults('windows',engine='source_csgo_legacy_windows')
            self.assertEqual(Path(result['game_dir']),root/'csgo')
            self.assertEqual(Path(result['game_executable']),root/'csgo.exe')
            self.assertEqual(Path(result['fgd_path']),fgd)

    def test_directory_searchpath_mounts_vpks_and_keeps_loose_override(self):
        with tempfile.TemporaryDirectory() as directory:
            game=Path(directory)/'csgo';game.mkdir()
            (game/'gameinfo.txt').write_text('GameInfo { FileSystem { SearchPaths { Game "|gameinfo_path|." } } }')
            data=b'LightmappedGeneric { "$basetexture" "packed" }'
            entry=struct.pack('<IHHIIH',zlib.crc32(data),0,0x7fff,0,len(data),65535)
            tree=b'vmt\0materials/test\0wall\0'+entry+b'\0\0\0'
            (game/'pak01_dir.vpk').write_bytes(struct.pack('<III',0x55aa1234,1,len(tree))+tree+data)
            assets=source_assets.Assets(game)
            self.assertEqual(assets.materials(),['test/wall'])
            self.assertEqual(assets.material('test/wall')['$basetexture'],'packed')
            (game/'materials/test').mkdir(parents=True)
            (game/'materials/test/wall.vmt').write_text('LightmappedGeneric { "$basetexture" "loose" }')
            self.assertEqual(source_assets.Assets(game).material('test/wall')['$basetexture'],'loose')


if __name__=='__main__':unittest.main()
