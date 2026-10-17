"""Headless checks of add-on log lifecycle and UI operator registration."""
import sys
import tempfile
from pathlib import Path
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'addon'))
import wavelength
from wavelength.source import diagnostics, ui

wavelength.register()
with tempfile.TemporaryDirectory() as directory:
    diagnostics.start(directory, bpy.app.version_string)
    class FailingOperation(ui.SafeOperator):
        bl_idname = 'wavelength.test_failure'
        def run(self, context):
            raise RuntimeError('Diagnostic smoke failure')
        def report(self, levels, message):
            assert 'Error ' in message
    assert FailingOperation().execute(bpy.context) == {'CANCELLED'}
    assert 'Diagnostic smoke failure' in diagnostics.read()
    destination = Path(directory) / 'export.log'
    assert bpy.ops.wavelength.export_log(filepath=str(destination)) == {'FINISHED'}
    assert 'Traceback' in destination.read_text()
    assert bpy.ops.wavelength.view_log.get_rna_type().identifier
    wavelength.unregister()
    assert diagnostics._handler is None
print('WAVELENGTH_DIAGNOSTICS_OK')
