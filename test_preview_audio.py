import time,unittest
from preview_engine import PreviewEngine
from test_preview_seeking import Player,until

class AudioPlayer(Player):
    def __init__(self): super().__init__(); self.volume=None; self.muted=None
    def set_volume(self,value): self.volume=value
    def set_mute(self,value): self.muted=value

class AudioTests(unittest.TestCase):
    def test_mute_stays_silent_when_slider_changes_and_restores_volume(self):
        player=AudioPlayer(); engine=PreviewEngine(lambda *a,**kw:player)
        try:
            engine.open('fixture'); until(lambda:bool(player.pauses))
            engine.command('toggle'); until(lambda:player.pauses[-1] is False)
            engine.command('mute',True); until(lambda:player.volume==0)
            self.assertTrue(player.muted)
            engine.command('volume',.35); time.sleep(.03)
            self.assertEqual(player.volume,0)
            engine.command('seek',20); until(lambda:player.seeks==[20]); time.sleep(.03)
            self.assertEqual(player.volume,0)
            engine.command('mute',False); until(lambda:player.volume==.35)
            self.assertFalse(player.muted)
        finally: engine.close(); engine.thread.join(2)
