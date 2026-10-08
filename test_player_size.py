import threading,time,unittest
from unittest.mock import Mock,patch
from PIL import Image
from preview_engine import PreviewEngine
from clip_gallery import ClipGallery

class Player:
    def __init__(self): self.sizes=[]; self.pauses=[]
    def set_size(self,*args): self.sizes.append(args)
    def set_mute(self,*args): pass
    def set_volume(self,*args): pass
    def set_pause(self,*args): self.pauses.append(args)
    def get_frame(self): return None,.01
    def get_metadata(self): return {}
    def close_player(self): pass

class ResizeTests(unittest.TestCase):
    def test_render_enlarges_preview_to_fullscreen_viewport(self):
        g=ClipGallery.__new__(ClipGallery)
        g.image=Image.new('RGB',(640,360))
        target=Mock(); target.winfo_width.return_value=1920; target.winfo_height.return_value=1080
        g.full_screen=target
        with patch('clip_gallery.ImageTk.PhotoImage') as photo:
            g.render()
            self.assertEqual(photo.call_args.args[0].size,(1920,1080))
    def test_aspect_ratio_is_preserved(self):
        g=ClipGallery.__new__(ClipGallery); g.image=Image.new('RGB',(1920,1080))
        target=Mock(); target.winfo_width.return_value=900; target.winfo_height.return_value=600
        g.full_screen=None; g.screen=target
        with patch('clip_gallery.ImageTk.PhotoImage') as photo:
            g.render()
            self.assertEqual(photo.call_args.args[0].size,(900,506))
    def test_decoder_receives_current_viewport_size(self):
        player=Player(); engine=PreviewEngine(lambda *args,**kwargs:player)
        try:
            engine.command('size',1920); engine.open('fixture')
            deadline=time.monotonic()+2
            while not player.sizes and time.monotonic()<deadline: time.sleep(.005)
            self.assertEqual(player.sizes[-1],(1920,-1))
            engine.command('size',960)
            while player.sizes[-1]!=(960,-1) and time.monotonic()<deadline: time.sleep(.005)
            self.assertEqual(player.sizes[-1],(960,-1))
        finally: engine.close(); engine.thread.join(2)
