import json,queue,sys,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from app import App
from clip_gallery import ClipGallery
from game_state import GameGate

class ControlsTests(unittest.TestCase):
    def paused_app(self):
        a=App.__new__(App)
        a.worker=Mock(); a.worker.is_alive.return_value=True
        a.stop=threading.Event(); a.user_paused=False; a.say=Mock()
        return a
    def test_pause_stays_paused_even_before_first_auto_start(self):
        a=self.paused_app(); a.toggle_monitoring()
        self.assertTrue(a.user_paused); self.assertTrue(a.stop.is_set())
        a.obs_ready=True; a.auto_started=False; a.obs_password=''
        a.password=Mock(); a.password.get.return_value=''
        a.tesseract=Mock(); a.tesseract.get.return_value=sys.executable
        a.saved_clips=queue.Queue(); a.messages=queue.Queue(); a.root=Mock()
        a.start=Mock(); a.entries=[]; a.manual_busy=threading.Event()
        a.game_armed=False; a.phase='Waiting'; a.phase_detail=''
        a.last_scan=0; a.scan_count=0; a.last_saved=''; a.pending_save_at=None; a.notice=''; a.notice_until=0
        for name in ('start_button','save_button','status_label','phase_label','detail_label','heartbeat_label','saved_label','ocr_button'):
            setattr(a,name,Mock())
        a.poll(); a.start.assert_not_called()
    def test_resume_is_explicit(self):
        a=self.paused_app(); a.worker.is_alive.return_value=False
        a.user_paused=True; a.start=Mock()
        a.toggle_monitoring()
        self.assertFalse(a.user_paused); a.start.assert_called_once()
    def test_manual_save_while_paused_uses_own_connection(self):
        a=self.paused_app(); a.stop.set(); a.obs_ready=True
        a.manual=threading.Event(); a.manual_busy=threading.Event()
        a.password=Mock(); a.password.get.return_value='fixture'
        a.clip_labels=queue.Queue()
        connection=Mock()
        with patch('app.OBS',return_value=connection),patch('app.threading.Thread') as thread:
            a.manual_save()
            thread.call_args.kwargs['target']()
        connection.request.assert_called_once_with('SaveReplayBuffer')
        connection.close.assert_called_once()
        self.assertFalse(a.manual_busy.is_set())
    def test_no_timed_hud_loss_disarm(self):
        gate=GameGate(missing_seconds=None)
        for t in range(3): gate.update('Player',True,False,t)
        for t in (3,100,10000): self.assertTrue(gate.update('',False,False,t)[0])
        gate.update('',False,True,10001)
        gate.update('',False,False,20000)
        self.assertTrue(gate.spectating)
        gate.update('',False,False,20001,lobby=True)
        gate.update('',False,False,20002,lobby=True)
        self.assertFalse(gate.spectating)

class ClipNameTests(unittest.TestCase):
    def test_rename_persists_without_changing_video(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'clip.mp4'; path.write_bytes(b'video fixture')
            g=ClipGallery.__new__(ClipGallery)
            g.records=[{'path':str(path),'label':'Kill'}]
            g.index=Path(folder)/'clips.json'; g.refresh=Mock(); g.say=Mock()
            self.assertTrue(g.set_clip_title(0,'My best kill'))
            self.assertEqual(json.loads(g.index.read_text())[0]['title'],'My best kill')
            self.assertEqual(path.read_bytes(),b'video fixture')
            with self.assertRaises(ValueError): g.set_clip_title(0,'')
    def test_failed_rename_keeps_old_name(self):
        g=ClipGallery.__new__(ClipGallery)
        g.records=[{'path':'fixture','title':'Old name'}]
        g.persist_records=Mock(return_value=False); g.refresh=Mock()
        self.assertFalse(g.set_clip_title(0,'New name'))
        self.assertEqual(g.records[0]['title'],'Old name')
        g.refresh.assert_not_called()
    def test_fullscreen_seek_uses_same_decoder_and_clamps(self):
        g=ClipGallery.__new__(ClipGallery)
        g.path='fixture'; g.duration=60; g.position=58
        g.engine=Mock(); g.draw_progress=Mock()
        g.skip(5); g.engine.command.assert_called_with('seek',60)
        g.position=2; g.skip(-5); g.engine.command.assert_called_with('seek',0)

@unittest.skipUnless(sys.platform=='win32','Windows Tk integration')
class WindowsUITests(unittest.TestCase):
    def test_status_controls_and_fullscreen_share_existing_decoder(self):
        import tkinter as tk
        from PIL import Image
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as folder:
            root=tk.Tk(); root.withdraw()
            callback_errors=[]
            root.report_callback_exception=lambda *args:callback_errors.append(args)
            engine=SimpleNamespace(frames=queue.Queue(),command=Mock(),close=Mock())
            with patch('app.App.watch_obs'),patch('clip_gallery.PreviewEngine',return_value=engine),patch.dict('os.environ',{'LOCALAPPDATA':folder}):
                app=App(root)
                try:
                    app.poll(); root.update_idletasks()
                    self.assertFalse(hasattr(app,'log'))
                    self.assertFalse(hasattr(app,'hud_timeout'))
                    self.assertFalse(hasattr(app,'name'))
                    gallery=app.gallery; gallery.path='fixture'; gallery.image=Image.new('RGB',(16,9))
                    original=gallery.engine
                    gallery.toggle_fullscreen(); root.update()
                    self.assertIs(gallery.engine,original)
                    self.assertIsNotNone(gallery.fullscreen_window)
                    gallery.exit_fullscreen(); root.update_idletasks()
                    self.assertIsNone(gallery.fullscreen_window)
                    self.assertEqual(callback_errors,[])
                finally:
                    app.gallery.close(); root.destroy()
                    for handler in list(app.activity_logger.handlers):
                        handler.close(); app.activity_logger.removeHandler(handler)
