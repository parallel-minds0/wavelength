import sys,struct,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from wavelength.source.goldsrc_model import Reader,Assets,transform,combine,apply

class GoldSrcModelTests(unittest.TestCase):
    def test_header_and_bounds_reject_bad_inputs(self):
        with self.assertRaises(ValueError):Reader(b'IDST').header()
        data=bytearray(244);data[:4]=b'IDST';struct.pack_into('<i',data,4,10);struct.pack_into('<i',data,72,244)
        reader=Reader(bytes(data)).header()
        with self.assertRaises(ValueError):reader.block(240,10,12)
        with self.assertRaises(ValueError):reader.block(0,-1,4)
        struct.pack_into('<i',data,4,48)
        with self.assertRaises(ValueError):Reader(bytes(data)).header()
    def test_bone_transforms_preserve_translation_and_direction(self):
        import math
        parent=transform((10,0,0),(0,0,math.pi/2));child=transform((2,0,0),(0,0,0))
        point=apply(combine(parent,child),(1,0,0))
        self.assertAlmostEqual(point[0],10);self.assertAlmostEqual(point[1],3)
        normal=apply(parent,(1,0,0),True);self.assertAlmostEqual(normal[0],0);self.assertAlmostEqual(normal[1],1)
    def test_mod_precedence_pak_and_valve_fallback(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);mod=root/'mod';valve=root/'valve';(mod/'models').mkdir(parents=True);(valve/'models').mkdir(parents=True)
            (valve/'models/base.mdl').write_bytes(b'base');(valve/'models/shared.mdl').write_bytes(b'base shared')
            payload=b'packed';name=b'models/shared.mdl'.ljust(56,b'\0');directory=struct.pack('<56sii',name,12,len(payload))
            (mod/'pak0.pak').write_bytes(b'PACK'+struct.pack('<ii',12+len(payload),64)+payload+directory)
            assets=Assets(mod);self.assertEqual(assets.read('models/shared.mdl'),payload);self.assertEqual(assets.read('models/base.mdl'),b'base')
            (mod/'models/Shared.MDL').write_bytes(b'loose')
            self.assertEqual(assets.read('models/shared.mdl'),b'loose')
            with self.assertRaises(ValueError):assets.read('../outside')
