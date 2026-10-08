import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'installer'))
from wavelength_installer.core import discover_compilers, discover_python_runtimes, patch_compatibility


class Milestone3Tests(unittest.TestCase):
    def test_bundled_compiler_priority(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            compiler = root / 'third-party/compilers/linux-x86_64/g++'
            compiler.parent.mkdir(parents=True)
            compiler.write_text('#!/bin/sh\nexit 0\n')
            compiler.chmod(0o755)
            self.assertEqual(discover_compilers(root)[0], str(compiler.resolve()))

    def test_bundled_python_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp) / 'third-party/python/linux-x86_64/python3'
            runtime.parent.mkdir(parents=True)
            runtime.write_text('#!/bin/sh\nexit 0\n')
            runtime.chmod(0o755)
            self.assertEqual(discover_python_runtimes(tmp), [str(runtime.resolve())])

    def test_appimage_is_not_a_renderer_executable(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / 'blender.AppImage'
            binary.write_bytes(b'\x7fELF' + bytes(4) + b'AI\x02' + bytes(10))
            result = patch_compatibility(binary)
            self.assertEqual(result['target_kind'], 'appimage-container')
            self.assertTrue(result['payload_inspection_required'])
            self.assertFalse(result['patch_supported'])

    def test_unknown_binary_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / 'blender'
            binary.write_bytes(b'not blender')
            result = patch_compatibility(binary)
            self.assertFalse(result['patch_supported'])
            self.assertIsNone(result['patch_id'])

if __name__ == '__main__':
    unittest.main()
