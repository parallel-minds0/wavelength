import itertools
import struct
import unittest
from installer.wavelength_installer import experimental as e


from tests.native_fixtures import binary


class NativeStates(unittest.TestCase):
    def test_all_states_converge_separate_and_shared(self):
        for shared,v,f in itertools.product((False,True),('original','current','legacy'),('original','current','legacy')):
            with self.subTest(shared=shared,vertex=v,fragment=f):
                data=binary(v,f,shared);analysis=e.analyze(data)
                self.assertNotEqual(analysis['action'],'unavailable',analysis)
                recipe,patched=e.build_recipe(data,analysis)
                self.assertEqual(len(patched),len(data))
                self.assertEqual(e.analyze(patched)['action'],'keep')
                self.assertEqual(e.build_recipe(patched),(None,patched))
                if v==f=='current':self.assertIsNone(recipe)
                elif shared:self.assertEqual(len(recipe['changes']),1)
    def test_unknown_rejected(self):
        for shared in (False,True):
            for v,f in [('unknown','current'),('current','unknown')]:
                self.assertEqual(e.analyze(binary(v,f,shared))['action'],'unavailable')
    def test_insufficient_capacity(self):
        self.assertEqual(e.analyze(binary(capacity=0))['action'],'unavailable')
    def test_duplicate_identity_rejected(self):
        data=binary()+b'VERTEX_SHADER_CREATE_INFO(overlay_grid_next)\0'
        self.assertEqual(e.analyze(data)['action'],'unavailable')
    def test_truncated_tables_rejected(self):
        self.assertEqual(e.analyze(binary()[:70])['action'],'unavailable')

    def test_startup_failure_strict_and_lenient(self):
        import tempfile, subprocess
        from pathlib import Path
        from unittest.mock import patch
        from installer.wavelength_installer.deployment import prepare
        from installer.wavelength_installer.lifecycle import NativeRequiredError
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'blender';target.write_bytes(binary());target.chmod(0o755)
            before=target.read_bytes()
            with patch('installer.wavelength_installer.deployment.subprocess.run',side_effect=subprocess.CalledProcessError(1,'fixture')):
                with prepare(target,strict=False) as result:self.assertEqual(result['native_state'],'unavailable')
                with self.assertRaises(NativeRequiredError):
                    with prepare(target):pass
            self.assertEqual(target.read_bytes(),before)
            self.assertFalse(list(Path(folder).glob('.wl-probe-*')))
