"""Surface preservation fails loudly; it does not pretend to verify behavior."""
import importlib.util,tempfile,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('wl_features',ROOT/'tools/feature_inventory.py')
features=importlib.util.module_from_spec(spec);spec.loader.exec_module(features)


class FeatureInventoryTests(unittest.TestCase):
    def fixture(self,folder):
        root=Path(folder);docs=root/'documentation';docs.mkdir()
        (docs/'FEATURES.md').write_text('| WL-TEST-001 | Implemented behavior |\n',encoding='utf-8')
        source=root/'addon/wavelength/source/ui.py';source.parent.mkdir(parents=True)
        source.write_text('raise RuntimeError("Must not import")\nclass Example:\n bl_idname="wavelength.example"\n enabled: BoolProperty(default=True)\n def _private(self):\n  return 1\n',encoding='utf-8')
        return root,docs,source

    def test_static_inventory_includes_private_ui_and_settings_without_import(self):
        with tempfile.TemporaryDirectory() as folder:
            root,docs,source=self.fixture(folder);entries=features.capture(root)
            self.assertTrue(any(e['name']=='Example._private' for e in entries.values()))
            self.assertTrue(any(e['kind']=='setting' and e['name']=='Example.enabled' for e in entries.values()))
            self.assertTrue(any(e['kind']=='ui' and e['name']=='Example.bl_idname' for e in entries.values()))

    def test_changed_body_and_removed_operator_require_review_and_retain_history(self):
        with tempfile.TemporaryDirectory() as folder:
            root,docs,source=self.fixture(folder)
            features.update(root,docs,['WL-TEST-001'],'Initial fixture')
            features.check(root,docs)
            source.write_text(source.read_text().replace('return 1','return 2'),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'Feature inventory changed'):features.check(root,docs)
            source.write_text('def replacement():\n return 2\n',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'Feature inventory changed'):features.check(root,docs)
            delta=features.update(root,docs,['WL-TEST-001'],'Explicit replacement; fixture behavior checked')
            self.assertTrue(delta['removed'])
            self.assertIn('Example.bl_idname',(docs/'developer/feature-changes.md').read_text())
            features.check(root,docs)

    def test_acceptance_requires_known_feature_reason_and_retained_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            root,docs,source=self.fixture(folder)
            with self.assertRaises(ValueError):features.update(root,docs,[],'')
            with self.assertRaisesRegex(ValueError,'Unknown feature'):features.update(root,docs,['WL-UNKNOWN-001'],'test')
            features.update(root,docs,['WL-TEST-001'],'Initial fixture')
            (docs/'FEATURES.md').write_text('| WL-OTHER-001 | replacement |\n',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'Do not delete feature IDs'):features.update(root,docs,['WL-OTHER-001'],'Removal must retain the old row')

    def test_repository_surface_matches_reviewed_baseline(self):features.check(ROOT)

    def test_review_history_cannot_be_rewritten_to_hide_prior_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            root,docs,source=self.fixture(folder)
            features.update(root,docs,['WL-TEST-001'],'Initial fixture')
            (docs/'developer/feature-changes.md').write_text('# Replacement history\n')
            with self.assertRaisesRegex(ValueError,'rewritten or truncated'):features.check(root,docs)
            with self.assertRaisesRegex(ValueError,'rewritten or truncated'):features.update(root,docs,['WL-TEST-001'],'Cannot approve lost history')


if __name__=='__main__':unittest.main()
