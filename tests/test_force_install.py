from contextlib import contextmanager
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from tests import test_lifecycle
from installer.wavelength_installer import lifecycle as life, forced, app
from installer.wavelength_installer.discovery import discover


class ForceTests(unittest.TestCase):
    setUp=test_lifecycle.LifecycleTests.setUp

    @contextmanager
    def native(self,action='patch'):
        @contextmanager
        def prepare(binary,strict=True):
            yield {'native_state':'unavailable' if action=='unavailable' else 'available',
                   'action':action,'patched':b'patched!!','recipe':None,'runtime':None,'reason':'fixture'}
        with patch('installer.wavelength_installer.deployment.prepare',prepare):yield

    def install(self,**kwargs):
        return life.install(self.bundle,self.blender,self.addons,self.state,force=True,**kwargs)

    def test_unknown_binary_installs_python(self):
        data=self.install()
        self.assertEqual(data['native_state'],'unavailable')
        self.assertEqual(data['installation_mode'],'forced')
        self.assertEqual(self.blender.read_bytes(),b'original!')
        life.remove(self.state)
        self.assertFalse((self.addons/'wavelength').exists())
    def test_missing_binary(self):
        self.blender.unlink();self.install();life.remove(self.state)
        self.assertFalse(self.blender.exists())
    def test_require_native_has_no_addon_effect(self):
        with self.assertRaises(life.NativeRequiredError):self.install(require_native=True)
        self.assertFalse((self.addons/'wavelength').exists())
    def test_owned_reinstall_preserves_original(self):
        with self.native():self.install()
        with self.native('keep'):data=self.install()
        self.assertEqual(data['native_ownership'],'owned')
        self.assertEqual((self.state/'original-blender').read_bytes(),b'original!')
        life.remove(self.state)
        self.assertEqual(self.blender.read_bytes(),b'original!')
        self.assertFalse((self.addons/'wavelength').exists())
    def test_adopted_patch_never_written_or_removed(self):
        with self.native('keep'),patch.object(forced,'replace_file',side_effect=AssertionError('unexpected write')):
            data=self.install();life.remove(self.state)
        self.assertEqual(data['native_ownership'],'adopted')
    def test_native_write_failure_keeps_python(self):
        with self.native(),patch.object(forced,'replace_file',side_effect=PermissionError('readonly')):
            data=self.install()
        self.assertEqual(data['native_state'],'unavailable')
        self.assertTrue(data['addon_matches'])
        self.assertEqual(self.blender.read_bytes(),b'original!')
        self.assertFalse((self.addons/'wavelength/experimental-grid.json').exists())
    def test_required_write_failure_rolls_back(self):
        with self.native(),patch.object(forced,'replace_file',side_effect=PermissionError('readonly')):
            with self.assertRaises(life.NativeRequiredError):self.install(require_native=True)
        self.assertFalse((self.addons/'wavelength').exists())
    def test_corrupt_receipt_archived(self):
        self.state.mkdir();(self.state/'receipt.json').write_text('{broken')
        data=self.install()
        self.assertEqual((Path(data['stale_archive'])/'receipt.json').read_text(),'{broken')
    def test_invalid_receipt_status(self):
        self.state.mkdir();(self.state/'receipt.json').write_text('[]')
        self.assertEqual(life.status(self.state)['phase'],'corrupt')
        with self.assertRaises(life.StateError):life.remove(self.state)
    def test_healthy_recover_is_noop(self):
        data=self.install();self.assertEqual(life.recover(self.state)['phase'],'installed')
        self.assertEqual(life.inventory(self.addons/'wavelength'),data['addon_inventory'])
    def test_interrupted_recovery(self):
        with self.native():self.install()
        data=life.read_receipt(self.state);data['phase']='prepared';life.write_json(self.state/'receipt.json',data)
        self.assertEqual(life.recover(self.state)['phase'],'removed')
        self.assertEqual(self.blender.read_bytes(),b'original!')
    def test_external_update_preserved(self):
        with self.native():self.install()
        self.blender.write_bytes(b'new upstream')
        with self.assertRaises(life.StateError):life.remove(self.state)
        self.install();life.remove(self.state)
        self.assertEqual(self.blender.read_bytes(),b'new upstream')
    def test_user_edits_backed_up_on_force(self):
        self.install();addon=self.addons/'wavelength/__init__.py';addon.write_text('my edits')
        with self.assertRaises(life.StateError):life.remove(self.state)
        self.install();life.remove(self.state)
        self.assertEqual(addon.read_text(),'my edits')
    def test_previous_addon_chain(self):
        addon=self.addons/'wavelength';addon.mkdir();(addon/'original').write_text('old')
        self.install();self.install();life.remove(self.state)
        self.assertEqual((addon/'original').read_text(),'old')
    def test_failed_reinstall_keeps_previous_receipt(self):
        self.install();before=(self.state/'receipt.json').read_bytes()
        with self.assertRaises(life.NativeRequiredError):self.install(require_native=True)
        self.assertEqual((self.state/'receipt.json').read_bytes(),before)
        self.assertTrue(life.status(self.state)['addon_matches'])
    def test_missing_owned_binary_not_recreated(self):
        with self.native():self.install()
        self.blender.unlink();life.remove(self.state)
        self.assertFalse(self.blender.exists())
    def test_relocated_target_preserves_old_backup(self):
        with self.native():self.install()
        old=self.blender;self.blender=self.root/'new-blender';self.blender.write_bytes(b'new')
        data=self.install()
        self.assertEqual((Path(data['stale_archive'])/'original-blender').read_bytes(),b'original!')
        self.assertEqual(old.read_bytes(),b'patched!!')
    def test_addon_swap_failure_restores_previous(self):
        self.install();before=life.inventory(self.addons/'wavelength');original=forced.os.replace
        def fail(source,target):
            if Path(source).name=='wavelength' and Path(source).parent.name.startswith('.wl-stage-'):raise OSError('swap failure')
            return original(source,target)
        with patch.object(forced.os,'replace',side_effect=fail):
            with self.assertRaises(OSError):self.install()
        self.assertEqual(life.inventory(self.addons/'wavelength'),before)
    def test_discovery_previous_install(self):
        self.install();self.assertEqual(discover(state=self.state),(self.blender,self.addons))
    def test_discovery_version_folder(self):
        (self.root/'5.2').mkdir()
        with patch('pathlib.Path.home',return_value=self.root),patch.dict('os.environ',{'XDG_CONFIG_HOME':str(self.root/'config')}):
            binary,addons=discover(self.blender)
        self.assertEqual(addons,self.root/'config/blender/5.2/scripts/addons')
    def cli(self,*args):
        output=io.StringIO()
        with patch.object(sys,'argv',['installer','--bundle',str(self.bundle),'--state',str(self.state),*args]),patch('sys.stdout',output):app.main()
        return json.loads(output.getvalue())
    def test_force_cli_no_confirmation(self):
        with patch.object(sys.stdin,'isatty',return_value=False):
            data=self.cli('install','--force','--blender',str(self.blender),'--addons',str(self.addons),'-v')
        self.assertEqual(data['native_state'],'unavailable')
    def test_cli_required_exit4(self):
        with self.assertRaises(SystemExit) as exc:self.cli('install','--force','--require-native','--blender',str(self.blender),'--addons',str(self.addons))
        self.assertEqual(exc.exception.code,4)
    def test_diagnose_readonly(self):
        data=self.cli('-v','diagnose','--blender',str(self.blender))
        self.assertEqual(data['action'],'unavailable');self.assertFalse(self.state.exists())

    def test_interrupted_archive_recovers_ownership(self):
        with self.native():self.install()
        forced.archive(self.state,'interrupted')
        with self.native('keep'):data=self.install()
        self.assertEqual(data['native_ownership'],'owned')
        life.remove(self.state)
        self.assertEqual(self.blender.read_bytes(),b'original!')
    def test_menu_force_without_confirmation(self):
        with patch.object(sys,'argv',['installer']),patch.object(sys.stdin,'isatty',return_value=True),patch('builtins.input',side_effect=['6',str(self.blender),str(self.addons)]),patch.object(app,'install',return_value={'phase':'installed','native_state':'unavailable'}) as install,patch('sys.stdout',io.StringIO()):
            app.main()
        self.assertTrue(install.call_args.kwargs['force'])
    def test_corrupt_recover_exit3(self):
        self.state.mkdir();(self.state/'receipt.json').write_text('null')
        with self.assertRaises(SystemExit) as exc:self.cli('recover')
        self.assertEqual(exc.exception.code,3)
