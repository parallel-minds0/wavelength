import sys,unittest,struct,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from wavelength.source import formats,vmf,profiles,source_tools

class SourceTests(unittest.TestCase):
    def test_unit_axes_preserve_uvs_and_lightmap_scale(self):
        doc=self.fixture();face=doc.entities[0].brushes[0][0]
        face.axes=[[0,4,0,17],[4,0,0,-31]];face.projection=[0,0,0,1,1]
        face.vmf={**(face.vmf or {}),'lightmapscale':'9'}
        exported=vmf.parse(vmf.write(doc)).entities[0].brushes[0][0]
        self.assertEqual(exported.projection[3:],[.25,.25])
        self.assertEqual(exported.vmf['lightmapscale'],'9')
        self.assertEqual(face.axes,[[0,4,0,17],[4,0,0,-31]])
        for index in range(2):
            self.assertAlmostEqual(sum(x*x for x in exported.axes[index][:3]),1)
            for point in ((0,0,0),(8712,9336,40),(-500,202,3)):
                def uv(f):return sum(f.axes[index][i]*point[i] for i in range(3))/f.projection[3+index]+f.axes[index][3]
                self.assertAlmostEqual(uv(face),uv(exported))
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
    def test_hammer_escape_delimited_connections(self):
        doc=self.fixture()
        value='light_break\x1bTurnOff\x1b\x1b1.65\x1b-1'
        doc.entities.append(formats.Entity([('classname','logic_relay'),
            ('literal',r'\u001b'+'\x1b'+r'\u001b'),
            (vmf.OUTPUT+'OnTrigger',value),(vmf.OUTPUT+'OnTrigger',value)],[]))
        text=vmf.write(doc)
        self.assertNotIn(value,text)
        self.assertIn(value.replace('\x1b',','),text)
        expected=[(k,v.replace('\x1b',',') if k.startswith(vmf.OUTPUT) else v)
                  for k,v in doc.entities[-1].pairs]
        self.assertEqual(vmf.parse(text).entities[-1].pairs,expected)
        self.assertEqual(doc.entities[-1].pairs[-1][1],value)

    def test_extended_connection_parameter_is_not_corrupted(self):
        doc=self.fixture();value='target\x1bSetValue\x1ba,b\x1b0\x1b-1'
        doc.entities.append(formats.Entity([('classname','logic_relay'),
            (vmf.OUTPUT+'OnTrigger',value)],[]))
        self.assertEqual(vmf.parse(vmf.write(doc)).entities[-1].pairs[-1][1],value)

    def test_hammer_plus_editor_blocks(self):
        text=vmf.write(self.fixture())
        expected=vmf.parse(text)
        metadata='\n'.join(name+'\n{\n"enabled" "0"\n}\n' for name in vmf.EDITOR_ROOTS if name.endswith('_plus'))
        text=text.replace('world\n{','world\n{\ngroup\n{\n"id" "123"\neditor\n{\n"color" "1 2 3"\n}\n}\n',1)
        actual=vmf.parse(metadata+text)
        self.assertEqual(actual.entities,expected.entities)
        with self.assertRaisesRegex(ValueError,'Unsupported VMF root'):
            vmf.parse('unknown_gameplay_data\n{\n}\n'+text)

    def test_reject_malformed_displacements(self):
        text=vmf.write(self.fixture()).replace('side\n{','side\n{\ndispinfo\n{\n}\n',1)
        with self.assertRaisesRegex(ValueError,'displacement'):vmf.parse(text)
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
