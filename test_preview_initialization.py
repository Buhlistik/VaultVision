import threading,time,unittest
from preview_engine import PreviewEngine

class LoadingPlayer:
    def __init__(self):
        self.scanned=threading.Event(); self.calls=[]
    def set_size(self,*args): pass
    def set_mute(self,*args): pass
    def get_metadata(self): return {}
    def get_frame(self): self.scanned.set(); return None,.01
    def set_pause(self,state): self.calls.append(state)
    def get_pts(self): raise AssertionError('Unsafe decoder clock access')
    def close_player(self): pass

class Tests(unittest.TestCase):
    def test_controls_are_ignored_before_first_frame(self):
        player=LoadingPlayer(); engine=PreviewEngine(lambda *a,**kw:player)
        try:
            engine.open('clip'); self.assertTrue(player.scanned.wait(1))
            engine.command('toggle'); engine.command('seek',5)
            time.sleep(.1)
            self.assertEqual(player.calls,[])
            self.assertTrue(engine.thread.is_alive())
        finally: engine.close(); engine.thread.join(1)

if __name__=='__main__': unittest.main()
