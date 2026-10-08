import tempfile
import unittest
from pathlib import Path
from installer.wavelength_installer.renderer_probe import probe_renderer, write_probe

class RendererProbeTests(unittest.TestCase):
    def test_elf_grid_marker_and_sha(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"blender"
            blob=bytearray(80)
            blob[:6]=b"\x7fELF\x02\x01"
            blob[18:20]=(62).to_bytes(2,"little")
            p.write_bytes(blob + b"grid_frag gridSteps")
            result=probe_renderer(p)
            self.assertEqual(result['architecture'], 'x86_64')
            self.assertEqual(result['container'], 'ELF64')
            self.assertFalse(result['verified_renderer_hook'])
            self.assertEqual(result['grid_marker_offsets']['grid_frag'], [80])
            report=Path(d)/"report.json"
            write_probe(p, report)
            with self.assertRaises(FileExistsError): write_probe(p, report)

    def test_unknown_binary_is_never_verified(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"random";p.write_bytes(b"not a Blender binary")
            self.assertEqual(probe_renderer(p)['container'], 'unknown')
            self.assertFalse(probe_renderer(p)['verified_renderer_hook'])
