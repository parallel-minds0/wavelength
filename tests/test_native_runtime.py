"""Installer must not apply legacy shader recipes to an existing native runtime."""
import unittest
import json
from unittest.mock import patch
from tests import test_lifecycle
from installer.wavelength_installer import lifecycle as life
from installer.wavelength_installer.deployment import prepare


class NativeRuntimeTests(unittest.TestCase):
    setUp = test_lifecycle.LifecycleTests.setUp

    def native_binary(self):
        data = b'\x7fELF' + b'\0' * 32 + b'wavelength_grid_enabled\0wavelength_grid_spacing\0wavelength_grid_subdivisions\0'
        self.blender.write_bytes(data)
        manifest = self.bundle / 'bundle.json'
        manifest.write_text(json.dumps({**json.loads(manifest.read_text()), 'native_grid_abi': 1}))
        return data

    def test_install_repair_remove_adopts_without_rewriting(self):
        original = self.native_binary()
        with patch('installer.wavelength_installer.deployment._startup_probe') as probe:
            result = life.install(self.bundle, self.blender, self.addons, self.state, force=True, require_native=True)
            self.assertEqual(result['native_state'], 'available')
            self.assertEqual(result['native_component'], 'native-grid-abi1')
            self.assertEqual(result['native_ownership'], 'adopted')
            self.assertTrue(probe.call_args.kwargs['native_grid'])
            life.repair(self.bundle, self.state, require_native=True)
            self.assertEqual(self.blender.read_bytes(), original)
            life.remove(self.state)
            self.assertEqual(self.blender.read_bytes(), original)
            self.assertFalse((self.addons / 'wavelength').exists())

    def test_markers_without_working_api_are_not_accepted(self):
        original = self.native_binary()
        with patch('installer.wavelength_installer.deployment._startup_probe', side_effect=ValueError('RNA API missing')):
            with prepare(self.blender, strict=False) as result:
                self.assertEqual(result['native_state'], 'unavailable')
        self.assertEqual(self.blender.read_bytes(), original)

    def test_new_bundle_never_applies_legacy_color_patch(self):
        self.native_binary()
        from tests.native_fixtures import binary
        original = binary()
        self.blender.write_bytes(original)
        result = life.install(self.bundle, self.blender, self.addons, self.state, force=True)
        self.assertEqual(result['native_state'], 'unavailable')
        self.assertEqual(self.blender.read_bytes(), original)
        life.remove(self.state)

    def test_new_bundle_requires_native_without_force(self):
        self.native_binary()
        self.blender.write_bytes(b'unsupported Blender')
        with self.assertRaises(life.NativeRequiredError):
            life.install(self.bundle, self.blender, self.addons, self.state)
        self.assertFalse((self.addons / 'wavelength').exists())
