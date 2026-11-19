"""Documentation contracts need no Blender, Sphinx, or compiler installation."""
import ast,importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('wl_docs',ROOT/'tools/docs.py')
docs=importlib.util.module_from_spec(spec);spec.loader.exec_module(docs)

class DocumentationTests(unittest.TestCase):
    def test_live_excerpt_requires_unique_ordered_markers(self):
        value='# docs:begin rule\n# Explain why.\nreturn 1\n# docs:end rule'
        self.assertIn('# Explain why.',docs.region(value,'rule'))
        for invalid in (value+'\n'+value,value.replace('# docs:end rule',''),value.replace('begin','end')):
            with self.assertRaises(ValueError):docs.region(invalid,'rule')

    def test_source_reference_cannot_escape_repository(self):
        with self.assertRaises(ValueError):docs.safe_source('../outside.py')
        with self.assertRaises(ValueError):docs.safe_source('missing.py')

    def test_reference_reads_ast_and_preserves_inline_comments_without_import(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'example.py'
            source.write_text('"""Example module."""\nraise RuntimeError("Must never import")\ndef public(value=2):\n    """Return the value."""\n    # An important implementation reason.\n    return value\n')
            stage=root/'stage'
            with patch.object(docs,'ROOT',root),patch.object(docs,'OUT',root/'build'),patch.object(docs,'API',('example.py',)):
                docs.generate_reference(stage,[(source,ast.parse(source.read_text()))])
            self.assertIn('public(value=2)',(stage/'reference/api.md').read_text())
            self.assertIn('Return the value.',(stage/'reference/api.md').read_text())
            viewer=(stage/'_static/code/example.py.html').read_text()
            self.assertIn('important implementation reason',viewer)
            self.assertIn('id="L',viewer)

    def test_sync_preserves_unmanaged_files_and_removes_only_prior_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);stage=root/'stage';stage.mkdir();(stage/'index.md').write_text('# Current')
            destination=root/'addon/wavelength/documentation/handbook';destination.mkdir(parents=True)
            (destination/'old.md').write_text('old');(destination/'personal.md').write_text('keep')
            (destination/'.generated.json').write_text(json.dumps(['old.md']))
            with patch.object(docs,'ROOT',root):docs.sync(stage)
            self.assertFalse((destination/'old.md').exists());self.assertTrue((destination/'personal.md').exists())
            self.assertEqual((destination/'index.md').read_text(),'# Current')

    def test_authored_handbook_contracts(self):
        screenshots,trees=docs.check()
        self.assertGreater(len(trees),80);self.assertGreaterEqual(len(screenshots),3)

    def test_sync_keeps_machine_readable_feature_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);stage=root/'stage';(stage/'reference').mkdir(parents=True)
            (stage/'reference/feature-surface.json').write_text('{"schema":1,"entries":{}}')
            with patch.object(docs,'ROOT',root):docs.sync(stage)
            self.assertTrue((root/'addon/wavelength/documentation/handbook/reference/feature-surface.json').is_file())

    def test_addon_packaging_includes_handbook_metadata(self):
        from installer.wavelength_installer.source_bundle import addon_files
        with tempfile.TemporaryDirectory() as directory:
            addon=Path(directory)
            metadata=('documentation/handbook/.generated.json',
                      'documentation/handbook/reference/feature-surface.json')
            for name in (*metadata, 'documentation/handbook/.private.json'):
                file=addon/name
                file.parent.mkdir(parents=True,exist_ok=True)
                file.write_text('{}')
            self.assertEqual({relative.as_posix() for _,relative in addon_files(addon)},set(metadata))

    def test_prepare_preserves_literal_feature_identifiers(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'authored'
            (source/'reference').mkdir(parents=True);(source/'archive').mkdir()
            literal='# Surface\n\n`WavelengthExportScope`\n'
            (source/'reference/feature-surface.md').write_text(literal)
            (source/'archive/index.md').write_text('# Archive\n')
            with patch.object(docs,'ROOT',root),patch.object(docs,'DOCS',source),patch.object(docs,'OUT',root/'out'),patch.object(docs,'EXTRAS',{}),patch.object(docs,'check',return_value=([],[])),patch.object(docs,'version',return_value='0'):
                stage=docs.prepare(root/'stage')
            self.assertEqual((stage/'reference/feature-surface.md').read_text(),literal)

if __name__=='__main__':unittest.main()
