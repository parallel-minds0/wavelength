import sys,tempfile,unittest,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from wavelength.source import library_prepare_worker as worker

class LibraryAtomicWriteTests(unittest.TestCase):
    def test_transient_windows_lock_retries_without_losing_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'manifest.json';target.write_text('{"old":true}')
            original=Path.replace;attempts=[]
            def replace(path,destination):
                attempts.append(path)
                if len(attempts)<3:
                    self.assertEqual(json.loads(target.read_text()),{'old':True})
                    raise PermissionError('simulated reader file lock')
                return original(path,destination)
            with patch.object(Path,'replace',replace),patch.object(worker.time,'sleep'):
                worker.write(target,{'state':'READY'})
            self.assertEqual(json.loads(target.read_text()),{'state':'READY'})
            self.assertEqual(len(attempts),3)
            self.assertFalse(list(Path(tmp).glob('*.tmp')))
