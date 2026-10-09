import importlib.util,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('sync_editions',Path(__file__).resolve().parents[1]/'tools/sync_editions.py');sync=importlib.util.module_from_spec(spec);spec.loader.exec_module(sync)
class SyncTests(unittest.TestCase):
 def test_preserve_pro_and_detect_drift(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);source=root/'free';target=root/'pro';(source/'addon').mkdir(parents=True);(source/'addon/shared.py').write_text('one')
   with patch.object(sync.subprocess,'check_output',return_value='abc'):
    sync.sync(source,target);(target/'pro').mkdir();(target/'pro/private.py').write_text('private');(source/'addon/shared.py').write_text('two');sync.sync(source,target)
    self.assertEqual((target/'pro/private.py').read_text(),'private');self.assertEqual((target/'addon/shared.py').read_text(),'two')
    (target/'addon/shared.py').write_text('pro edit');(source/'addon/shared.py').write_text('three')
    with self.assertRaises(ValueError):sync.sync(source,target)
 def test_no_pro_source_leaks(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);(root/'addon/pro').mkdir(parents=True);(root/'addon/pro/private.py').write_text('secret');(root/'addon/free.py').write_text('free')
   self.assertEqual([p.name for p in sync.source_files(root)],['free.py'])
