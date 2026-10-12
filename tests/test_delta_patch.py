import bz2
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from installer.wavelength_installer.delta_patch import apply, prepare_bytes
from installer.wavelength_installer import lifecycle
from tests import test_lifecycle


def number(n):
    return (abs(n) | ((1 << 63) if n < 0 else 0)).to_bytes(8, 'little')


def fixture(old=b'original!', new=b'patched!!'):
    controls=bz2.compress(number(len(new))+number(0)+number(0))
    diff=bz2.compress(bytes((b-old[i]) & 255 for i,b in enumerate(new)))
    data=b'BSDIFF40'+number(len(controls))+number(len(diff))+number(len(new))+controls+diff+bz2.compress(b'')
    sha=lambda b:hashlib.sha256(b).hexdigest()
    entry={'platform':'linux-x86_64','input_sha256':sha(old),'output_sha256':sha(new),'patch_sha256':sha(data),'output_size':len(new),'file':'test.bsdiff'}
    return data,entry


class DeltaTests(unittest.TestCase):
    def test_round_trip_and_wrong_input(self):
        data,entry=fixture()
        self.assertEqual(apply(b'original!',data,entry),b'patched!!')
        with self.assertRaisesRegex(ValueError,'does not match'):apply(b'wrong',data,entry)
        with self.assertRaisesRegex(ValueError,'checksum'):apply(b'original!',data+b'x',entry)

    def test_corrupt_bounds_rejected_even_with_matching_patch_digest(self):
        data,entry=fixture()
        data=data[:24]+number(2**40)+data[32:]
        entry['patch_sha256']=hashlib.sha256(data).hexdigest()
        with self.assertRaisesRegex(ValueError,'header'):apply(b'original!',data,entry)

    def test_output_hash_verified(self):
        data,entry=fixture();entry['output_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'checksum'):apply(b'original!',data,entry)


class PairedPatchTests(unittest.TestCase):
    setUp=test_lifecycle.LifecycleTests.setUp

    def prepare_bundle(self):
        data,entry=fixture()
        folder=self.bundle/'patches/native';folder.mkdir()
        (folder/'test.bsdiff').write_bytes(data)
        (folder/'manifest.json').write_text(json.dumps({'schema':1,'patches':[entry]}))
        manifest=self.bundle/'bundle.json'
        manifest.write_text(json.dumps({**json.loads(manifest.read_text()),'native_grid_abi':1,'native_policy':'required'}))

    def test_force_applies_native_and_remove_restores_original(self):
        self.prepare_bundle()
        with patch('installer.wavelength_installer.delta_patch.host_platform',return_value='linux-x86_64'),patch('installer.wavelength_installer.deployment._startup_probe') as probe:
            result=lifecycle.install(self.bundle,self.blender,self.addons,self.state,force=True)
            self.assertEqual(result['native_state'],'available')
            self.assertEqual(result['native_ownership'],'owned')
            self.assertEqual(self.blender.read_bytes(),b'patched!!')
            self.assertTrue(probe.call_args.kwargs['native_grid'])
            lifecycle.remove(self.state)
            self.assertEqual(self.blender.read_bytes(),b'original!')

    def test_force_does_not_install_python_when_native_is_missing(self):
        self.prepare_bundle();self.blender.write_bytes(b'unknown')
        with self.assertRaises(lifecycle.NativeRequiredError):
            lifecycle.install(self.bundle,self.blender,self.addons,self.state,force=True)
        self.assertFalse((self.addons/'wavelength').exists())
        self.assertEqual(self.blender.read_bytes(),b'unknown')

    def test_failed_startup_leaves_original_and_addon_alone(self):
        self.prepare_bundle()
        with patch('installer.wavelength_installer.delta_patch.host_platform',return_value='linux-x86_64'),patch('installer.wavelength_installer.deployment._startup_probe',side_effect=ValueError('startup failed')):
            with self.assertRaises(lifecycle.NativeRequiredError):
                lifecycle.install(self.bundle,self.blender,self.addons,self.state,force=True)
        self.assertFalse((self.addons/'wavelength').exists())
        self.assertEqual(self.blender.read_bytes(),b'original!')

class WindowsDeltaSelectionTests(unittest.TestCase):
    def test_windows_payload_selection_without_executing_it(self):
        data,entry=fixture();entry['platform']='windows-x86_64'
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'test.bsdiff').write_bytes(data)
            (root/'manifest.json').write_text(json.dumps({'schema':1,'patches':[entry]}))
            with patch('installer.wavelength_installer.delta_patch.host_platform',return_value='windows-x86_64'):
                result,metadata=prepare_bytes(b'original!',root)
                self.assertEqual(result,b'patched!!')
                self.assertEqual(metadata['platform'],'windows-x86_64')
            with patch('installer.wavelength_installer.delta_patch.host_platform',return_value='linux-x86_64'):
                with self.assertRaisesRegex(ValueError,'No native patch matches'):
                    prepare_bytes(b'original!',root)

class NativeDiagnosisTests(unittest.TestCase):
    def test_windows_native_fingerprints_are_reported_without_a_linux_shader_probe(self):
        from installer.wavelength_installer.delta_patch import diagnose
        data,entry=fixture();entry['platform']='windows-x86_64'
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);binary=root/'blender.exe'
            (root/'manifest.json').write_text(json.dumps({'schema':1,'patches':[entry]}))
            binary.write_bytes(b'original!')
            self.assertEqual(diagnose(binary,root)['native_state'],'patch-available')
            binary.write_bytes(b'patched!!')
            result=diagnose(binary,root)
            self.assertEqual(result['state'],'patched')
            self.assertFalse(result['runtime_verified'])
            binary.write_bytes(b'foreign executable')
            self.assertEqual(diagnose(binary,root)['state'],'unsupported')
