import hashlib,json,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from installer.wavelength_installer import lifecycle as life

def digest(b):return hashlib.sha256(b).hexdigest()

class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.bundle=self.root/'bundle';self.bundle.mkdir()
        self.blender=self.root/'blender';self.blender.write_bytes(b'original!');self.blender.chmod(0o755)
        self.addons=self.root/'addons';self.addons.mkdir();self.state=self.root/'state'
        (self.bundle/'patches').mkdir()
        recipe={'schema':1,'verified':True,'input_sha256':digest(b'original!'),'output_sha256':digest(b'patched!!'),
                'changes':[{'offset':0,'before':b'original!'.hex(),'after':b'patched!!'.hex()}]}
        (self.bundle/'patches/recipe.json').write_text(json.dumps(recipe))
        (self.bundle/'patches/manifest.json').write_text(json.dumps({'schema':1,'supported_builds':[{'verified':True,'sha256':digest(b'original!'),'recipe':'recipe.json'}]}))
        archive=self.bundle/'addon.zip'
        with zipfile.ZipFile(archive,'w') as z:z.writestr('wavelength/__init__.py','new addon')
        (self.bundle/'bundle.json').write_text(json.dumps({'version':'test','addon':'addon.zip','addon_sha256':life.sha256(archive)}))
    def install(self):return life.install(self.bundle,self.blender,self.addons,self.state)
    def test_paired_install_remove_restores_previous(self):
        old=self.addons/'wavelength';old.mkdir();(old/'__init__.py').write_text('old addon')
        self.assertEqual(self.install()['phase'],'installed')
        self.assertEqual(self.blender.read_bytes(),b'patched!!')
        self.assertTrue(life.status(self.state)['addon_matches'])
        self.assertEqual(life.remove(self.state)['phase'],'removed')
        self.assertEqual(self.blender.read_bytes(),b'original!')
        self.assertEqual((old/'__init__.py').read_text(),'old addon')
        self.assertEqual(life.remove(self.state)['phase'],'removed')
    def test_fresh_removal(self):
        self.install();life.remove(self.state);self.assertFalse((self.addons/'wavelength').exists())
    def test_unsupported_build_touches_nothing(self):
        self.blender.write_bytes(b'unknown')
        with self.assertRaisesRegex(ValueError,'No verified'):self.install()
        self.assertFalse(self.state.exists());self.assertFalse((self.addons/'wavelength').exists())
    def test_user_edits_prevent_removal(self):
        self.install();(self.addons/'wavelength/__init__.py').write_text('user edited')
        with self.assertRaisesRegex(ValueError,'discard edits'):life.remove(self.state)
        self.assertEqual(self.blender.read_bytes(),b'patched!!')
    def test_external_blender_update_preserved(self):
        self.install();self.blender.write_bytes(b'new Blender version')
        with self.assertRaisesRegex(ValueError,'Blender changed'):life.remove(self.state)
        self.assertEqual(self.blender.read_bytes(),b'new Blender version')
    def test_failure_after_native_write_rolls_back(self):
        actual=life.os.replace
        def fail_addon(source,target):
            if Path(source).name=='wavelength':raise OSError('simulated deployment error')
            return actual(source,target)
        with patch.object(life.os,'replace',side_effect=fail_addon):
            with self.assertRaisesRegex(OSError,'simulated'):self.install()
        self.assertEqual(self.blender.read_bytes(),b'original!')
        self.assertFalse((self.addons/'wavelength').exists())
    def test_prepared_receipt_recovery(self):
        self.install();p=self.state/'receipt.json';d=json.loads(p.read_text());d['phase']='prepared';life.write_json(p,d)
        life.remove(self.state);self.assertEqual(self.blender.read_bytes(),b'original!')
    def test_corrupt_backup_preserves_installed_files(self):
        self.install();(self.state/'original-blender').write_bytes(b'bad')
        with self.assertRaisesRegex(ValueError,'backup is damaged'):life.remove(self.state)
        self.assertEqual(self.blender.read_bytes(),b'patched!!')
