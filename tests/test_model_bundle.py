import sys,tempfile,unittest,zipfile,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from wavelength.source import model_bundle,model_pipeline


class ModelBundleTests(unittest.TestCase):
    def test_verified_roundtrip_and_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'model.wlmodel'
            model_bundle.write(path,{'asset.blend':b'BLENDER fixture','images/color.png':b'pixels'},{'editable':'asset.blend','collection':'model'})
            target=Path(directory)/'out';model_bundle.extract(path,target)
            self.assertEqual((target/'images/color.png').read_bytes(),b'pixels')
            with zipfile.ZipFile(path) as archive:entries={n:archive.read(n) for n in archive.namelist()}
            entries['images/color.png']=b'changed'
            with zipfile.ZipFile(path,'w') as archive:
                for name,data in entries.items():archive.writestr(name,data)
            with self.assertRaisesRegex(ValueError,'checksum'):model_bundle.extract(path,Path(directory)/'bad')

    def test_paths_and_route_stubs(self):
        for name in ('../outside','/outside','C:/outside','a/../../outside'):
            with self.assertRaises(ValueError):model_bundle.safe_path(name)
        with self.assertRaisesRegex(ValueError,'not implemented'):model_pipeline.route('unknown','unknown')
        key=('test','other');model_pipeline.register_route(*key,'fixture')
        self.assertEqual(model_pipeline.route(*key),'fixture')
