import sys,unittest,struct,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from wavelength.source import formats,vmf,profiles,source_tools

class SourceTests(unittest.TestCase):
    def fixture(self):
        p=Path(__file__).resolve().parents[1]/'addon/wavelength/environment/maps/minimal_source.vmf'
        doc=vmf.parse(p.read_text())
        for e in doc.entities:
            for b in e.brushes:
                for f in b:f.texture='dev/dev_measuregeneric01b'
        return doc
    def test_vmf_roundtrip_geometry_axes_outputs(self):
        doc=self.fixture()
        doc.entities.append(formats.Entity([('classname','logic_relay'),(vmf.OUTPUT+'OnTrigger','door,Open,,0,-1'),(vmf.OUTPUT+'OnTrigger','light,TurnOn,,1,-1')],[]))
        text=vmf.write(doc);parsed=vmf.parse(text)
        self.assertEqual(len(doc.entities),len(parsed.entities))
        self.assertEqual(parsed.entities[-1].pairs,doc.entities[-1].pairs)
        self.assertEqual(vmf.write(parsed),text)
        self.assertNotIn('"wad"',text)
        for a,b in zip(doc.entities[0].brushes,parsed.entities[0].brushes):
            self.assertEqual(formats.brush_mesh(a),formats.brush_mesh(b))
    def test_reject_displacements(self):
        text=vmf.write(self.fixture()).replace('side\n{','side\n{\ndispinfo\n{\n}\n',1)
        with self.assertRaisesRegex(ValueError,'displacements'):vmf.parse(text)
    def test_profiles(self):
        for name in ('source_hl2_linux','source_hl2_windows'):
            self.assertTrue(profiles.is_source(name));self.assertTrue(profiles.uses_valve_axes(name))
            self.assertEqual(profiles.get(name)['stages'],['vbsp','vvis','vrad'])
            self.assertEqual(profiles.get(name)['steam_app_id'],'220')
    def test_bsp_header_not_goldsrc(self):
        data=b'VBSP'+struct.pack('<i',20)+bytes(1028)
        source_tools.validate_bsp(data)
        with self.assertRaises(ValueError):source_tools.validate_bsp(bytes(1036))
        bad=bytearray(data);struct.pack_into('<ii',bad,8,2000,5)
        with self.assertRaises(ValueError):source_tools.validate_bsp(bad)
    def test_commands_require_gameinfo(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):source_tools.compiler_args('vbsp',folder)
            (Path(folder)/'gameinfo.txt').write_text('GameInfo {}')
            self.assertEqual(source_tools.compiler_args('vbsp',folder),['-game',folder,'level.vmf'])
            self.assertEqual(source_tools.compiler_args('vrad',folder)[-1],'level.bsp')

    def test_combined_runtime_discovery(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);game=root/'hl2';game.mkdir()
            self.assertEqual(source_tools.runtime_game(game),game)
            combined=root/'hl2_complete';combined.mkdir();(combined/'gameinfo.txt').write_text('GameInfo {}')
            self.assertEqual(source_tools.runtime_game(game),combined)

    def test_source_map_basename_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'gameinfo.txt').write_text('GameInfo {}')
            self.assertEqual(source_tools.compiler_args('vbsp',folder,'my_room')[-1],'my_room.vmf')
            self.assertEqual(source_tools.compiler_args('vrad',folder,'my_room')[-1],'my_room.bsp')
            with self.assertRaises(ValueError):source_tools.compiler_args('vbsp',folder,'../escape')

    def test_renamed_embedded_map_rejected(self):
        import io,zipfile
        pak=io.BytesIO()
        with zipfile.ZipFile(pak,'w') as z:z.writestr('materials/maps/original/cubemapdefault.vtf',b'fixture')
        data=bytearray(b'VBSP'+struct.pack('<i',20)+bytes(1028))
        struct.pack_into('<ii',data,8+16*40,len(data),len(pak.getvalue()));data.extend(pak.getvalue())
        source_tools.validate_map_assets(data,'original')
        with self.assertRaisesRegex(ValueError,'Rebuild'):source_tools.validate_map_assets(data,'renamed')
    def test_source_lowercase_filename_required(self):
        with self.assertRaisesRegex(ValueError,'lowercase'):source_tools.validate_map_name('MyRoom')
        self.assertEqual(source_tools.validate_map_name('my_room-1'),'my_room-1')
    def test_invalid_embedded_archive_rejected(self):
        data=bytearray(b'VBSP'+struct.pack('<i',20)+bytes(1028))
        struct.pack_into('<ii',data,8+16*40,len(data),3);data.extend(b'bad')
        with self.assertRaisesRegex(ValueError,'asset archive'):source_tools.validate_map_assets(data,'room')
