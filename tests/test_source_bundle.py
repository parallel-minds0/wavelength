import json,unittest,zipfile
from pathlib import Path
from installer.wavelength_installer.source_bundle import bundle_from_source
from installer.wavelength_installer.core import sha256

class SourceBundleTests(unittest.TestCase):
    def test_current_source_is_installable_without_prebuilt_zip(self):
        root=Path(__file__).resolve().parents[1]
        with bundle_from_source(root) as bundle:
            metadata=json.loads((bundle/'bundle.json').read_text())
            archive=bundle/metadata['addon']
            self.assertEqual(sha256(archive),metadata['addon_sha256'])
            with zipfile.ZipFile(archive) as z:
                self.assertIn('wavelength/source/source_assets.py',z.namelist())
                self.assertIn('wavelength/source/build/pipeline.py',z.namelist())
                self.assertFalse(any('__pycache__' in name for name in z.namelist()))
        self.assertFalse(bundle.exists())
    def test_bootstrap_runtime_pin_matches_builder(self):
        root=Path(__file__).resolve().parents[1]
        lock=json.loads((root/'installer/runtime-lock.json').read_text())
        launcher=(root/'wavelength-installer').read_text()
        self.assertIn(lock['sha256'],launcher);self.assertIn(lock['url'],launcher)
