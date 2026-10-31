"""Progress remains readable while Windows holds the destination against rename."""
import ctypes,json,os,sys,tempfile,threading,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from wavelength.source import worker_status


class WorkerStatusTests(unittest.TestCase):
    def test_partial_record_keeps_last_complete_state(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'status.jsonl'
            self.assertIsNone(worker_status.latest(path))
            worker_status.publish(path,dict(state='PARSING'))
            with path.open('ab') as stream:stream.write(b'{"state":')
            self.assertEqual(worker_status.latest(path),dict(state='PARSING'))

    def test_concurrent_reader_writer(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'status.jsonl';errors=[];stop=threading.Event()
            def read():
                while not stop.is_set():
                    try:
                        value=worker_status.latest(path)
                        if value is not None:self.assertIn('sequence',value)
                    except Exception as exc:errors.append(exc);stop.set()
            thread=threading.Thread(target=read);thread.start()
            try:
                for sequence in range(200):worker_status.publish(path,dict(sequence=sequence))
            finally:stop.set();thread.join()
            self.assertFalse(errors,errors)
            self.assertEqual(worker_status.latest(path),dict(sequence=199))

    @unittest.skipUnless(os.name=='nt','Windows file sharing test')
    def test_reader_denying_delete_still_allows_progress(self):
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p]
        kernel.CreateFileW.restype=ctypes.c_void_p
        kernel.CloseHandle.argtypes=[ctypes.c_void_p]
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'status.jsonl';worker_status.publish(path,dict(state='PARSING'))
            handle=kernel.CreateFileW(str(path),0x80000000,3,None,3,0,None)
            self.assertNotEqual(handle,ctypes.c_void_p(-1).value)
            try:
                replacement=Path(folder)/'status.tmp';replacement.write_text('{}')
                with self.assertRaises(PermissionError):replacement.replace(path)
                worker_status.publish(path,dict(state='READY'))
                self.assertEqual(worker_status.latest(path),dict(state='READY'))
            finally:kernel.CloseHandle(handle)


if __name__=='__main__':unittest.main()
