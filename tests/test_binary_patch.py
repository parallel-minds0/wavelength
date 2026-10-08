import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from installer.wavelength_installer.binary_patch import apply_recipe, validate_recipe, restore_copy


def sha(data): return hashlib.sha256(data).hexdigest()


class BinaryPatchTests(unittest.TestCase):
    def recipe(self, original=b'ABCD', before='42', after='58'):
        patched = original[:1] + bytes.fromhex(after) + original[2:]
        return {'schema': 1, 'verified': True, 'input_sha256': sha(original),
                'output_sha256': sha(patched), 'changes': [{'offset': 1, 'before': before, 'after': after}]}

    def test_verified_patch_copy_and_restore(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp); src = base/'blender'; src.write_bytes(b'ABCD')
            recipe = base/'recipe.json'; recipe.write_text(json.dumps(self.recipe()))
            output = apply_recipe(src, recipe, base/'patched')
            self.assertEqual(output.read_bytes(), b'AXCD')
            self.assertEqual(src.read_bytes(), b'ABCD')
            restored = restore_copy(src, output, base/'restored', expected_original_sha256=sha(b'ABCD'))
            self.assertEqual(restored.read_bytes(), b'ABCD')

    def test_reject_unverified(self):
        r = self.recipe(); r['verified'] = False
        with self.assertRaises(ValueError): validate_recipe(r, b'ABCD')

    def test_reject_wrong_hash(self):
        with self.assertRaises(ValueError): validate_recipe(self.recipe(), b'WXYZ')

    def test_reject_wrong_expected_bytes(self):
        with self.assertRaises(ValueError): validate_recipe(self.recipe(before='43'), b'ABCD')

    def test_reject_wrong_output_hash(self):
        r = self.recipe(); r['output_sha256'] = '0'*64
        with self.assertRaises(ValueError): validate_recipe(r, b'ABCD')

    def test_reject_overlaps(self):
        r = self.recipe(); r['changes'].append({'offset':1,'before':'42','after':'59'})
        with self.assertRaises(ValueError): validate_recipe(r, b'ABCD')

    def test_reject_in_place(self):
        with tempfile.TemporaryDirectory() as temp:
            src = Path(temp)/'blender'; src.write_bytes(b'ABCD')
            recipe = Path(temp)/'recipe.json'; recipe.write_text(json.dumps(self.recipe()))
            with self.assertRaises(ValueError): apply_recipe(src, recipe, src)
