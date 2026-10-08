import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
from obs_launcher import launch_obs,OBS_EXE
from clip_gallery import ClipGallery

class Tests(unittest.TestCase):
    def test_launch_flags_and_working_directory(self):
        with patch('psutil.process_iter',return_value=[]), patch('pathlib.Path.is_file',return_value=True), patch('obs_launcher.subprocess.Popen') as popen:
            self.assertTrue(launch_obs())
            args,kwargs=popen.call_args
            self.assertEqual(args[0],[str(OBS_EXE),'--startreplaybuffer','--minimize-to-tray'])
            self.assertEqual(kwargs['cwd'],str(OBS_EXE.parent))
    def test_existing_obs_is_reused(self):
        proc=Mock(); proc.info={'name':'obs64.exe'}
        with patch('psutil.process_iter',return_value=[proc]), patch('obs_launcher.subprocess.Popen') as popen:
            self.assertFalse(launch_obs()); popen.assert_not_called()
    def test_saved_clip_index_and_deduplication(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'clip.mp4'; path.write_bytes(b'fixture')
            gallery=ClipGallery.__new__(ClipGallery)
            gallery.records=[]; gallery.index=Path(folder)/'clips.json'
            gallery.refresh=Mock(); gallery.say=Mock()
            gallery.add(str(path),'Kill'); gallery.add(str(path),'Kill')
            self.assertEqual(len(gallery.records),1)
            self.assertTrue(gallery.index.is_file())
    def test_missing_clip_is_ignored(self):
        gallery=ClipGallery.__new__(ClipGallery); gallery.records=[]; gallery.refresh=Mock()
        gallery.add('/missing/clip.mp4')
        self.assertEqual(gallery.records,[])

if __name__=='__main__': unittest.main()
