"""Tests the compiled ABI without requiring Blender."""
import math
import sys
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'installer'))
from wavelength_installer.core import build_native, discover_compilers, patch_blender
from wavelength_installer.native_bridge import NativeGrid

@unittest.skipUnless(discover_compilers(), 'No C++ compiler installed')
class NativeBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.library = build_native(ROOT / 'native', cls.temp.name)
        cls.grid = NativeGrid(cls.library)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_engine_units(self):
        step = 16 * 0.0254
        self.assertTrue(self.grid.is_highlight_line(32 * 0.0254, step))
        self.assertFalse(self.grid.is_highlight_line(24 * 0.0254, step))

    def test_offset_origin_and_disable(self):
        self.assertTrue(self.grid.is_highlight_line(1.25, 0.5, origin_meters=0.25))
        self.assertFalse(self.grid.is_highlight_line(1.25, 0.5, origin_meters=0.25, enabled=False))

    def test_invalid_input(self):
        self.assertFalse(self.grid.is_highlight_line(math.nan, 0.5))
        self.assertFalse(self.grid.is_highlight_line(1, 0))

    def test_patching_refuses(self):
        with self.assertRaises(NotImplementedError):
            patch_blender()
