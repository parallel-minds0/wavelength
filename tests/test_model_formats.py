import sys,struct,io,zipfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'addon'))
from wavelength.source import model_formats,source_assets
from wavelength.source.build.pipeline import Pipeline
import tempfile

class ModelFormatTests(unittest.TestCase):
    def test_vtf_color_orientation_and_dimensions(self):
        payload=model_formats.vtf(2,2,bytes([255,0,0,255]*2+[0,255,0,255]*2))
        _,_,w,h,rgba=source_assets.decode_vtf(payload)
        self.assertEqual((w,h),(2,2));self.assertEqual(list(rgba[:4]),[0,255,0,255])
        with self.assertRaises(ValueError):model_formats.vtf(3,2,b'\0'*24)
    def test_pak_preserves_entries_and_replaces_owned_files(self):
        base=bytearray(1036);base[:4]=b'VBSP';struct.pack_into('<i',base,4,20)
        once=model_formats.pack_bsp(bytes(base),{'maps/test.vmt':b'old','models/wavelength/model.mdl':b'a'})
        twice=model_formats.pack_bsp(once,{'models/wavelength/model.mdl':b'b'})
        offset,size=struct.unpack_from('<2i',twice,8+40*16)
        with zipfile.ZipFile(io.BytesIO(twice[offset:offset+size])) as archive:
            self.assertTrue(all(info.compress_type==zipfile.ZIP_STORED for info in archive.infolist()))
            self.assertEqual(archive.read('maps/test.vmt'),b'old');self.assertEqual(archive.read('models/wavelength/model.mdl'),b'b')
        self.assertEqual(len(once),len(twice))
    def test_repack_repairs_old_deflated_entries(self):
        base=bytearray(1036);base[:4]=b'VBSP';struct.pack_into('<i',base,4,20)
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED) as archive:archive.writestr('models/door.mdl',b'IDST'+b'x'*200)
        payload=stream.getvalue();struct.pack_into('<ii',base,648,len(base),len(payload));base.extend(payload)
        repaired=model_formats.pack_bsp(bytes(base),{})
        offset,size=struct.unpack_from('<ii',repaired,648)
        with zipfile.ZipFile(io.BytesIO(repaired[offset:offset+size])) as archive:
            self.assertEqual(archive.getinfo('models/door.mdl').compress_type,zipfile.ZIP_STORED)
            self.assertEqual(archive.read('models/door.mdl'),b'IDST'+b'x'*200)
    def test_pack_refuses_path_traversal(self):
        base=bytearray(1036);base[:4]=b'VBSP';struct.pack_into('<i',base,4,20)
        with self.assertRaises(ValueError):model_formats.pack_bsp(bytes(base),{'../outside':b'bad'})
    def test_failed_dependency_callback_prevents_map_compiler(self):
        with tempfile.TemporaryDirectory() as root:
            calls=[]
            def fail():raise ValueError('invalid model')
            job=Pipeline([fail,lambda:calls.append(True)],root)
            self.assertEqual(job.poll(),'FAILED');self.assertEqual(calls,[]);self.assertIn('invalid model',job.message)
    def test_timeout_reports_named_stage_and_log(self):
        from unittest.mock import Mock, patch

        with tempfile.TemporaryDirectory() as root:
            process = Mock()
            process.poll.return_value = None
            job = Pipeline([['wrapper', 'vvis.exe']], root, timeout=120, stage_names=['VVIS'])
            with patch('wavelength.source.build.pipeline.subprocess.Popen', return_value=process), patch(
                'wavelength.source.build.pipeline.time.monotonic', side_effect=[0, 121]
            ), patch('wavelength.source.build.pipeline.os.killpg', create=True):
                process.pid = 123
                self.assertEqual(job.poll(), 'RUNNING')
                self.assertEqual(job.poll(), 'FAILED')
            self.assertEqual(job.message, 'VVIS timed out after 120 seconds (stage-1.log)')
            self.assertIsNone(job.log)

    def test_progress_counts_completed_stages_and_names_running_compiler(self):
        from unittest.mock import Mock, patch

        job = Pipeline([lambda: None, ['wrapper', 'vvis.exe']], '.', stage_names=['Prepare', 'VVIS'])
        self.assertEqual(job.progress(), (0.0, 'Preparing build'))
        self.assertEqual(job.poll(), 'RUNNING')
        self.assertEqual(job.progress(), (0.5, 'Completed 1/2 stages'))
        process = Mock()
        process.poll.return_value = None
        job.process = process
        job.index = 2
        job.started = 100
        with patch('wavelength.source.build.pipeline.time.monotonic', return_value=167):
            self.assertEqual(job.progress(), (0.5, 'VVIS (2/2) · 1:07'))
        process.poll.return_value = 0
        job.log = Mock()
        self.assertEqual(job.poll(), 'DONE')
        self.assertEqual(job.progress()[0], 1.0)

    def test_recent_compiler_output_includes_partial_line(self):
        with tempfile.TemporaryDirectory() as directory:
            job = Pipeline([], directory)
            self.assertEqual(job.recent_output(), ())
            job.index = 2
            job.process = object()
            self.assertEqual(job.recent_output(), ())
            (Path(directory) / 'stage-2.log').write_bytes(
                b'old line\n' * 1000 + b'one\ntwo\nthree\nfour\nPortalFlow: 0...1'
            )
            self.assertEqual(job.recent_output(), ('two', 'three', 'four', 'PortalFlow: 0...1'))

    def test_failed_compiler_reports_stage_and_log(self):
        from unittest.mock import Mock, patch

        with tempfile.TemporaryDirectory() as directory:
            command = ['wrapper', 'vrad.exe']
            job = Pipeline([lambda: None, command], directory, stage_names=['Prepare', 'VRAD'])
            process = Mock()
            process.poll.return_value = 7
            with patch('wavelength.source.build.pipeline.subprocess.Popen', return_value=process):
                self.assertEqual(job.poll(), 'RUNNING')
                self.assertEqual(job.poll(), 'RUNNING')
                self.assertEqual(job.poll(), 'FAILED')
            self.assertEqual(job.message, 'VRAD exited with code 7 (stage-2.log)')
            self.assertTrue((Path(directory) / 'stage-2.log').is_file())
            job = Pipeline([command], directory, stage_names=['VRAD'])
            with patch('wavelength.source.build.pipeline.subprocess.Popen', side_effect=OSError('missing wrapper')):
                self.assertEqual(job.poll(), 'FAILED')
            self.assertEqual(job.message, 'Could not start VRAD (stage-1.log): missing wrapper')
