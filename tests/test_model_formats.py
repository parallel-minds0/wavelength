import sys,struct,io,zipfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from wavelength.source import model_formats,source_assets
from wavelength.source.build.pipeline import Pipeline
import tempfile

class ModelFormatTests(unittest.TestCase):
    def test_vtf_color_orientation_and_dimensions(self):
        payload=model_formats.vtf(2,2,bytes([255,0,0,255]*2+[0,255,0,255]*2))
        _,_,w,h,rgba=source_assets.decode_vtf(payload)
        self.assertEqual((w,h),(2,2));self.assertEqual(list(rgba[:4]),[0,255,0,255])
        with self.assertRaises(ValueError):model_formats.vtf(3,2,b'\0'*24)
    def test_pak_preserves_entries_and_replaces_owned_files(self):
        base=bytearray(1036);base[:4]=b'VBSP';struct.pack_into('<i',base,4,20)
        once=model_formats.pack_bsp(bytes(base),{'maps/test.vmt':b'old','models/wavelength/model.mdl':b'a'})
        twice=model_formats.pack_bsp(once,{'models/wavelength/model.mdl':b'b'})
        offset,size=struct.unpack_from('<2i',twice,8+40*16)
        with zipfile.ZipFile(io.BytesIO(twice[offset:offset+size])) as archive:
            self.assertTrue(all(info.compress_type==zipfile.ZIP_STORED for info in archive.infolist()))
            self.assertEqual(archive.read('maps/test.vmt'),b'old');self.assertEqual(archive.read('models/wavelength/model.mdl'),b'b')
        self.assertEqual(len(once),len(twice))
    def test_repack_repairs_old_deflated_entries(self):
        base=bytearray(1036);base[:4]=b'VBSP';struct.pack_into('<i',base,4,20)
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED) as archive:archive.writestr('models/door.mdl',b'IDST'+b'x'*200)
        payload=stream.getvalue();struct.pack_into('<ii',base,648,len(base),len(payload));base.extend(payload)
        repaired=model_formats.pack_bsp(bytes(base),{})
        offset,size=struct.unpack_from('<ii',repaired,648)
        with zipfile.ZipFile(io.BytesIO(repaired[offset:offset+size])) as archive:
            self.assertEqual(archive.getinfo('models/door.mdl').compress_type,zipfile.ZIP_STORED)
            self.assertEqual(archive.read('models/door.mdl'),b'IDST'+b'x'*200)
    def test_pack_refuses_path_traversal(self):
        base=bytearray(1036);base[:4]=b'VBSP';struct.pack_into('<i',base,4,20)
        with self.assertRaises(ValueError):model_formats.pack_bsp(bytes(base),{'../outside':b'bad'})
    def test_failed_dependency_callback_prevents_map_compiler(self):
        with tempfile.TemporaryDirectory() as root:
            calls=[]
            def fail():raise ValueError('invalid model')
            job=Pipeline([fail,lambda:calls.append(True)],root)
            self.assertEqual(job.poll(),'FAILED');self.assertEqual(calls,[]);self.assertIn('invalid model',job.message)
