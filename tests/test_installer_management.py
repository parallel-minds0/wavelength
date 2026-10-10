import io,itertools,json,shutil,sys,unittest
from pathlib import Path
from unittest.mock import patch
from tests import test_lifecycle
digest=test_lifecycle.digest
from tests.native_fixtures import binary
from installer.wavelength_installer import lifecycle as life,experimental as e,management as m,instances,app

class ManagementTests(unittest.TestCase):
    setUp=test_lifecycle.LifecycleTests.setUp
    def install(self,**kw):return life.install(self.bundle,self.blender,self.addons,self.state,**kw)
    def synthetic(self):
        original=binary();self.blender.write_bytes(original)
        recipe,patched=e.build_recipe(original);recipe['verified']=True
        (self.bundle/'patches/recipe.json').write_text(json.dumps(recipe))
        (self.bundle/'patches/manifest.json').write_text(json.dumps({'schema':1,'supported_builds':[{'verified':True,'sha256':digest(original),'recipe':'recipe.json'}]}))
        return original
    def version(self,value):
        p=self.bundle/'bundle.json';data=json.loads(p.read_text());data['version']=value;p.write_text(json.dumps(data))
    def test_replace_all_modes_versions_preserves_pristine(self):
        original=self.synthetic()
        manifest=self.bundle/'patches/manifest.json';verified=manifest.read_text()
        with patch('installer.wavelength_installer.deployment._startup_probe'):
            for before,after in itertools.product((False,True),repeat=2):
                with self.subTest(before=before,after=after):
                    manifest.write_text('{"supported_builds":[]}' if before else verified)
                    self.version('2');self.install(allow_unverified=before,confirm_experimental=before)
                    for version in ('3','1','1'):
                        manifest.write_text('{"supported_builds":[]}' if after else verified)
                        self.version(version);data=self.install(allow_unverified=after,confirm_experimental=after)
                        self.assertEqual(data['version'],version)
                        self.assertEqual((self.state/'original-blender').read_bytes(),original)
                    life.uninstall(self.state);self.assertEqual(self.blender.read_bytes(),original)
    def test_replace_prepared_and_removing(self):
        for phase in ('prepared','removing'):
            self.install();data=life.read_receipt(self.state);data['phase']=phase;life.write_json(self.state/'receipt.json',data)
            self.assertEqual(self.install()['phase'],'installed')
            life.remove(self.state);self.assertEqual(self.blender.read_bytes(),b'original!')
    def test_edited_replace_stops_without_mutation(self):
        self.install();(self.addons/'wavelength/__init__.py').write_text('edited')
        before=m.tree_snapshot(self.root)
        with self.assertRaises(life.StateError):self.install()
        self.assertEqual(before,m.tree_snapshot(self.root))
        self.install(force=True)
        self.assertTrue(list((self.state/'backups').glob('addon-edits-*')))
    def test_side_by_side_independent(self):
        first=self.install();second=self.install(existing='side-by-side')
        child=Path(second['state']);copy=Path(second['blender'])
        self.assertNotEqual(first['addon'],second['addon']);self.assertTrue(copy.exists())
        with self.assertRaisesRegex(life.StateError,'--instance'):instances.select(self.state)
        self.assertEqual(instances.select(self.state,second['instance_id']),child)
        # Replacing default must not archive its child instance.
        life.install(self.bundle,self.blender,self.addons,self.state,instance='default')
        self.assertTrue((child/'receipt.json').exists())
        life.uninstall(child);self.assertFalse(copy.exists());self.assertEqual(self.blender.read_bytes(),b'patched!!')
        self.assertTrue(Path(first['addon']).exists());life.uninstall(self.state)
        self.assertEqual(self.blender.read_bytes(),b'original!')
    def test_remove_default_first_leaves_child(self):
        self.install();second=self.install(existing='side-by-side');child=Path(second['state'])
        life.uninstall(self.state);self.assertEqual(life.status(child)['phase'],'installed')
        self.assertTrue(Path(second['blender']).exists());life.uninstall(child)
    def test_side_by_side_fallback_does_not_touch_parent(self):
        self.blender.write_bytes(b'#!/bin/sh\nexit 0');before=self.blender.read_bytes()
        data=self.install(force=True,existing='side-by-side')
        self.assertEqual(data['native_state'],'unavailable');self.assertEqual(self.blender.read_bytes(),before)
        life.uninstall(Path(data['state']));self.assertEqual(self.blender.read_bytes(),before)
    def test_abort_unchanged(self):
        self.install();before=m.tree_snapshot(self.root)
        self.assertEqual(self.install(existing='abort')['phase'],'cancelled')
        self.assertEqual(before,m.tree_snapshot(self.root))
    def test_structural_uninstall_all_layouts(self):
        with patch('installer.wavelength_installer.deployment._startup_probe'):
            for shared,v,f in itertools.product((False,True),('original','current','legacy'),('original','current','legacy')):
                if v==f=='original':continue
                with self.subTest(shared=shared,v=v,f=f):
                    self.blender.write_bytes(binary(v,f,shared));self.install(force=True)
                    result=life.uninstall(self.state)
                    self.assertEqual(e.analyze(self.blender.read_bytes())['state'],'pristine')
                    self.assertEqual(result['native_restoration'],'structural')
    def test_full_cleanup_and_keep_state(self):
        self.install();life.uninstall(self.state);self.assertFalse(self.state.exists())
        self.install();life.uninstall(self.state,keep_state=True)
        self.assertEqual(life.read_receipt(self.state)['phase'],'removed')
        self.assertEqual({p.name for p in self.state.iterdir()},{'lock','receipt.json'})
        life.uninstall(self.state);self.assertFalse(self.state.exists())
    def test_runtime_inventory_cleanup_preserves_foreign(self):
        for edited in (False,True):
            self.install();runtime=self.state/'runtime-test';runtime.mkdir();(runtime/'file').write_text('owned')
            data=life.read_receipt(self.state);data.update(runtime_dir=str(runtime),runtime_inventory=m.tree_snapshot(runtime));life.write_json(self.state/'receipt.json',data)
            if edited:(runtime/'foreign').write_text('user file')
            life.uninstall(self.state);self.assertEqual(runtime.exists(),edited)
    def test_uninstall_failure_rolls_back(self):
        self.install();before=self.blender.read_bytes();original=m.os.replace
        def fail(src,dst):
            if Path(src)==self.addons/'wavelength':raise OSError('failure')
            return original(src,dst)
        with patch.object(m.os,'replace',side_effect=fail):
            with self.assertRaises(OSError):life.uninstall(self.state)
        self.assertEqual(self.blender.read_bytes(),before);self.assertTrue(life.status(self.state)['addon_matches'])
    def test_repair_healthy_noop_and_empty(self):
        self.assertIn('install',life.repair(self.bundle,self.state)['summary'])
        self.install();before=m.tree_snapshot(self.root)
        self.assertIn('healthy',life.repair(self.bundle,self.state)['summary']);self.assertEqual(before,m.tree_snapshot(self.root))
    def test_repair_missing_edited_addon(self):
        for edited in (False,True):
            self.install();addon=self.addons/'wavelength'
            if edited:(addon/'__init__.py').write_text('my edits')
            else:shutil.rmtree(addon)
            result=life.repair(self.bundle,self.state);self.assertTrue(result['addon_matches'])
            if edited:self.assertTrue(list((self.state/'backups').glob('addon-edits-*')))
            life.remove(self.state);self.assertFalse(addon.exists());self.assertEqual(self.blender.read_bytes(),b'original!')
    def test_repair_native_states(self):
        original=self.synthetic()
        with patch('installer.wavelength_installer.deployment._startup_probe'):
            for v,f in [('original','original'),('current','original'),('legacy','legacy')]:
                self.install(allow_unverified=True,confirm_experimental=True);self.blender.write_bytes(binary(v,f))
                result=life.repair(self.bundle,self.state)
                self.assertEqual(e.analyze(self.blender.read_bytes())['state'],'patched')
                life.remove(self.state);self.assertEqual(self.blender.read_bytes(),original)
    def test_repair_corrupt_and_external(self):
        self.install();(self.state/'receipt.json').write_text('{bad')
        with self.assertRaises(life.StateError):life.repair(self.bundle,self.state)
        data=life.repair(self.bundle,self.state,blender=self.blender,addons=self.addons,force=True)
        self.assertEqual(data['phase'],'installed');self.assertTrue(list((self.state/'stale').glob('*')))
    def test_noninteractive_cli_never_prompts(self):
        self.install()
        with patch.object(sys,'argv',['installer','--bundle',str(self.bundle),'--state',str(self.state),'install','--blender',str(self.blender),'--addons',str(self.addons),'--existing','replace','--yes']),patch.object(sys.stdin,'isatty',return_value=False),patch('builtins.input',side_effect=AssertionError('prompt')),patch('sys.stdout',io.StringIO()):app.main()
        self.assertTrue(life.status(self.state)['addon_matches'])
    def test_repair_experimental_probe_failure_reverts_fully(self):
        original=self.synthetic();(self.bundle/'patches/manifest.json').write_text('{"supported_builds":[]}')
        with patch('installer.wavelength_installer.deployment._startup_probe'):
            self.install(allow_unverified=True,confirm_experimental=True)
        self.blender.write_bytes(binary('legacy','original'))
        before=m.tree_snapshot(self.root)
        with patch('installer.wavelength_installer.deployment._startup_probe',side_effect=ValueError('probe failed')):
            with self.assertRaises(life.NativeRequiredError):life.repair(self.bundle,self.state,require_native=True)
            self.assertEqual(m.tree_snapshot(self.root),before)
            result=life.repair(self.bundle,self.state)
        self.assertEqual(result['native_state'],'unavailable')
        self.assertEqual(e.analyze(self.blender.read_bytes())['state'],'pristine')
        life.uninstall(self.state);self.assertEqual(self.blender.read_bytes(),original)
    def test_repair_prepared(self):
        self.install();data=life.read_receipt(self.state);data['phase']='prepared';life.write_json(self.state/'receipt.json',data)
        self.assertTrue(life.repair(self.bundle,self.state)['addon_matches'])
        life.uninstall(self.state);self.assertEqual(self.blender.read_bytes(),b'original!')
    def test_recover_removal_journal(self):
        self.install();data=life.read_receipt(self.state);journal=self.state/'removal-test';journal.mkdir()
        life.write_json(journal/'receipt.json',data);shutil.copy2(self.blender,journal/'blender')
        shutil.copytree(self.addons/'wavelength',journal/'addon')
        transaction={**data,'phase':'removing','removal_journal':journal.name,'removal_addon_before':data['addon_inventory'],'removal_output_sha256':digest(b'original!')}
        life.write_json(self.state/'receipt.json',transaction);self.blender.write_bytes(b'original!');shutil.rmtree(self.addons/'wavelength')
        result=life.recover(self.state);self.assertTrue(result['addon_matches']);self.assertEqual(self.blender.read_bytes(),b'patched!!')
        life.uninstall(self.state)
    def test_native_preparation_race_preserves_external_update(self):
        self.install();from contextlib import contextmanager
        actual=m.native_plan
        @contextmanager
        def race(*a,**kw):
            with actual(*a,**kw) as prepared:
                self.blender.write_bytes(b'external');yield prepared
        with patch.object(m,'native_plan',race):
            with self.assertRaises(life.StateError):self.install()
        self.assertEqual(self.blender.read_bytes(),b'external')
    def test_runtime_launcher_is_restored_and_removed(self):
        from contextlib import contextmanager
        from installer.wavelength_installer import deployment
        runtime=self.root/'fixture-runtime';runtime.mkdir();(runtime/'blender').write_bytes(binary('current','current'));(runtime/'AppRun').write_text('#!/bin/sh\n')
        @contextmanager
        def prepare(*args,**kw):yield {'native_state':'available','action':'patch','patched':b'payload','recipe':None,'runtime':runtime}
        with patch.object(deployment,'prepare',prepare):
            data=self.install(force=True);data=self.install(force=True)
        paths=[Path(x['runtime_dir']) for x in data['managed_runtimes']]+[Path(data['runtime_dir'])]
        self.assertTrue(all(p.exists() for p in paths));life.uninstall(self.state)
        self.assertEqual(self.blender.read_bytes(),b'original!');self.assertFalse(any(p.exists() for p in paths))
    def test_cli_ambiguous_exit3_and_selected_status(self):
        self.install();child=self.install(existing='side-by-side')
        for extra,expected in [([],3),(['--instance',child['instance_id']],None)]:
            with patch.object(sys,'argv',['installer','--state',str(self.state),'status',*extra]),patch.object(sys.stdin,'isatty',return_value=False),patch('sys.stdout',io.StringIO()):
                if expected:
                    with self.assertRaises(SystemExit) as caught:app.main()
                    self.assertEqual(caught.exception.code,expected)
                else:app.main()
    def test_force_repair_external_binary_keeps_external_original(self):
        self.install();self.blender.write_bytes(b'new upstream')
        life.repair(self.bundle,self.state,force=True);life.uninstall(self.state)
        self.assertEqual(self.blender.read_bytes(),b'new upstream')
    def test_empty_addon_repaired(self):
        self.install();(self.addons/'wavelength/__init__.py').unlink()
        self.assertTrue(life.repair(self.bundle,self.state)['addon_matches'])
    def test_repair_missing_independent_copy(self):
        self.install();data=self.install(existing='side-by-side');copy=Path(data['blender']);copy.unlink()
        result=life.repair(self.bundle,Path(data['state']))
        self.assertTrue(result['native_matches']);self.assertEqual(self.blender.read_bytes(),b'patched!!')
        life.uninstall(Path(data['state']));self.assertFalse(copy.exists())
