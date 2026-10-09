import json,struct,sys,unittest
from unittest.mock import patch
from pathlib import Path
from contextlib import contextmanager
from tests import test_lifecycle
from installer.wavelength_installer import experimental,app
from installer.wavelength_installer.binary_patch import validate_recipe,digest

class ExperimentalTests(test_lifecycle.LifecycleTests):
    def install(self):
        (self.bundle/'patches/manifest.json').write_text('{"schema":1,"supported_builds":[]}')
        recipe=json.loads((self.bundle/'patches/recipe.json').read_text())
        recipe.update(verified=False,experimental=True,native_component='test-native')
        @contextmanager
        def prepare(binary):
            yield {'recipe':recipe,'patched':validate_recipe(recipe,binary.read_bytes(),allow_unverified=True),'runtime':None,'limitations':'test'}
        with patch('installer.wavelength_installer.deployment.prepare',prepare):
            return self._install()
    def _install(self,confirmed=True):
        from installer.wavelength_installer.lifecycle import install
        return install(self.bundle,self.blender,self.addons,self.state,allow_unverified=True,confirm_experimental=confirmed)
    def test_unsupported_build_touches_nothing(self):
        self.blender.write_bytes(b'unknown')
        with self.assertRaisesRegex(ValueError,'mismatch'):self.install()
        self.assertFalse(self.state.exists())
    def test_confirmation_required(self):
        with self.assertRaisesRegex(ValueError,'confirmation'):self._install(False)
        self.assertFalse(self.state.exists())
    def test_receipt_marks_experimental(self):
        data=self.install();self.assertEqual(data['installation_mode'],'experimental')
        self.assertEqual(data['native_component'],'test-native')
        self.assertTrue((self.addons/'wavelength/experimental-grid.json').is_file())
    def test_cli_requires_explicit_acceptance(self):
        with patch.object(sys,'argv',['installer','install','--blender',str(self.blender),'--addons',str(self.addons),'--allow-unverified']),patch.object(sys.stdin,'isatty',return_value=False):
            with self.assertRaises(SystemExit) as exc:app.main()
        self.assertEqual(exc.exception.code,1);self.assertFalse(self.state.exists())

class GeneratorTests(unittest.TestCase):
    def test_wrong_format_and_appimage_refused(self):
        for data in (b'not an ELF',b'\x7fELF'+bytes(4)+b'AI\x02'+bytes(100)):
            with self.assertRaises(ValueError):experimental.generate(data)
    def test_unverified_preserves_byte_hash_and_overlap_checks(self):
        r={'schema':1,'verified':False,'experimental':True,'input_sha256':digest(b'ab'),'output_sha256':digest(b'ac'),'changes':[{'offset':1,'before':'62','after':'63'}]}
        self.assertEqual(validate_recipe(r,b'ab',allow_unverified=True),b'ac')
        with self.assertRaises(ValueError):validate_recipe(r,b'ab')
        with self.assertRaises(ValueError):validate_recipe(r,b'xx',allow_unverified=True)
        r['changes']*=2
        with self.assertRaisesRegex(ValueError,'Overlapping'):validate_recipe(r,b'ab',allow_unverified=True)
    def test_unknown_hash_uses_complete_shader_fingerprints(self):
        vertex=b'line.P = step_offs + step_size * line.P;'
        fragment=b'out_color = mix(theme.colors.grid, theme.colors.grid_emphasis, vertex_out_flat.emphasis);'
        shaders=[b'    '*300+needle+b'\n' for needle in (vertex,fragment)]
        header=bytearray(128);header[:6]=b'\x7fELF\x02\x01';struct.pack_into('<H',header,18,62)
        struct.pack_into('<Q',header,32,64);struct.pack_into('<Q',header,40,80)
        for offset,value in ((54,8),(56,1),(58,8),(60,1)):struct.pack_into('<H',header,offset,value)
        data=bytes(header)+b'\0'.join(shaders)+b'\0'
        with patch.object(experimental,'SHADER_HASHES',[digest(s) for s in shaders]):
            recipe,result=experimental.generate(data)
            self.assertNotEqual(result,data);self.assertEqual(len(result),len(data));self.assertFalse(recipe['verified'])
            changed=data.replace(b'line.P =',b'line.X =',1)
            with self.assertRaises(ValueError):experimental.generate(changed)
