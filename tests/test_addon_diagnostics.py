import importlib.util
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'addon/wavelength/source/diagnostics.py'
spec = importlib.util.spec_from_file_location('wl_diagnostics_test', SOURCE)
diagnostics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostics)


class LoggingTests(unittest.TestCase):
    def tearDown(self):
        diagnostics.stop()

    def test_error_trace_persists_after_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            diagnostics.start(directory, 'test')
            try:
                raise ValueError('Missing compiler')
            except ValueError as exc:
                message = diagnostics.error('Build', exc)
            self.assertIn('Diagnostics > View Log', message)
            diagnostics.stop()
            diagnostics.start(directory, 'test')
            contents = diagnostics.read()
            self.assertIn('Traceback', contents)
            self.assertIn('Missing compiler', contents)
            self.assertEqual(contents.count('Missing compiler [Error'), 1)
            diagnostics.stop()

    def test_rotation_is_bounded_and_unregister_closes_file(self):
        with tempfile.TemporaryDirectory() as directory:
            diagnostics.start(directory)
            diagnostics._handler.maxBytes = 200
            for i in range(20):
                diagnostics.logger.info('%s %s', i, 'x' * 150)
            diagnostics.stop()
            self.assertLessEqual(len(list(Path(directory).glob('wavelength.log*'))), 4)
            Path(directory, 'wavelength.log').unlink()
