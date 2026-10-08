import tempfile
import unittest
from pathlib import Path
from installer.wavelength_installer.grid_source_probe import GRID_FILES, probe_source

class GridSourceProbeTests(unittest.TestCase):
    def test_missing_source_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            result = probe_source(d)
            self.assertFalse(result["complete"])
            self.assertFalse(result["renderer_patch_verified"])
    def test_source_anchors_and_hashes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            contents = {"cpp":"grid_ubo_ grid_ps_ grid_flag", "vertex":"grid_iter level",
                        "fragment":"theme.colors.grid out_color", "shared":"OVERLAY_GridData steps"}
            for kind, rel in GRID_FILES.items():
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(contents[kind])
            result = probe_source(root)
            self.assertTrue(result["complete"])
            self.assertEqual(len(result["files"]["fragment"]["sha256"]), 64)
            self.assertFalse(result["renderer_patch_verified"])
