import unittest,tempfile,struct,zlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from wavelength.source import source_assets as assets,keyvalues,vmf,formats
from tests import test_source

class AssetTests(unittest.TestCase):
    def test_keyvalues_paths_duplicates_and_truncation(self):
        self.assertEqual(keyvalues.parse('root { "path" "foo\\bar" x 1 x 2 }'),[('root',[('path','foo\\bar'),('x','1'),('x','2')])])
        for text in ('root { key }','"unterminated','root {'):
            with self.assertRaises(ValueError):keyvalues.parse(text)
    def test_vpk_embedded_preload_and_crc(self):
        data=b'abcdef';pre=data[:2];payload=data[2:]
        entry=struct.pack('<IHHIIH',zlib.crc32(data),len(pre),0x7fff,0,len(payload),65535)+pre
        tree=b'vmt\0materials/test\0wall\0'+entry+b'\0\0\0'
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'test_dir.vpk';path.write_bytes(struct.pack('<III',0x55aa1234,1,len(tree))+tree+payload)
            vpk=assets.VPK(path);self.assertEqual(vpk.read('materials/test/wall.vmt'),data)
            path.write_bytes(path.read_bytes()[:-1]+b'x')
            with self.assertRaisesRegex(ValueError,'CRC'):vpk.read('materials/test/wall.vmt')
    def vtf(self,fmt,pixels,w=4,h=4):
        header=bytearray(80);header[:4]=b'VTF\0';struct.pack_into('<III',header,4,7,2,80)
        struct.pack_into('<HHIH',header,16,w,h,0,1);struct.pack_into('<I',header,52,fmt);header[56]=1;struct.pack_into('<H',header,63,1)
        return bytes(header)+pixels
    def test_vtf_dxt1_red_and_dxt5_alpha(self):
        red=struct.pack('<HHI',0xf800,0,0)
        w,h,pw,ph,rgba=assets.decode_vtf(self.vtf(13,red));self.assertEqual(rgba,bytes([255,0,0,255])*16)
        alpha=bytes([128,0])+bytes(6)
        self.assertEqual(assets.decode_vtf(self.vtf(15,alpha+red))[-1],bytes([255,0,0,128])*16)
    def test_vtf_rgba_orientation_and_bounds(self):
        pixels=bytes([255,0,0,255,0,255,0,255])
        self.assertEqual(assets.decode_vtf(self.vtf(0,pixels,1,2))[-1],pixels[4:]+pixels[:4])
        with self.assertRaises(ValueError):assets.decode_vtf(self.vtf(13,b''))
        with self.assertRaises(ValueError):assets.asset_path('../secrets')
    def test_gameinfo_order_and_vmt_patch(self):
        with tempfile.TemporaryDirectory() as folder:
            game=Path(folder)/'hl2';game.mkdir();(game/'materials').mkdir()
            (game/'gameinfo.txt').write_text('GameInfo { FileSystem { SearchPaths { game "|gameinfo_path|." } } }')
            (game/'materials/base.vmt').write_text('LightmappedGeneric { "$basetexture" "brick/red" "$surfaceprop" "brick" }')
            (game/'materials/child.vmt').write_text('patch { include "materials/base.vmt" replace { "$basetexture" "brick/blue" } insert { "$surfaceprop" "metal" } }')
            lib=assets.Assets(game);self.assertEqual(lib.material('child')['$basetexture'],'brick/blue');self.assertEqual(lib.material('child')['$surfaceprop'],'brick')
            self.assertEqual(lib.materials(),['base','child'])
    def test_side_references_remap_and_reject_ambiguity(self):
        doc=test_source.SourceTests().fixture();face=doc.entities[0].brushes[0][0];face.vmf={'id':'900'}
        doc.entities.append(formats.Entity([('classname','info_overlay'),('sides','900')],[]))
        result=vmf.parse(vmf.write(doc));newid=result.entities[0].brushes[0][0].vmf['id']
        self.assertEqual(dict(result.entities[-1].pairs)['sides'],newid)
        doc.entities[0].brushes[0][1].vmf={'id':'900'}
        with self.assertRaisesRegex(ValueError,'ambiguous'):vmf.write(doc)
