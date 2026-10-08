import time,threading,unittest
from preview_engine import PreviewEngine

class FakePlayer:
    def __init__(self,*args,**kw): self.closed=False
    def set_size(self,*a): pass
    def set_mute(self,*a): pass
    def set_pause(self,*a): pass
    def get_pts(self): return 0
    def get_metadata(self): return {}
    def get_frame(self): return None,.02
    def close_player(self): self.closed=True

class Tests(unittest.TestCase):
    def test_selection_does_not_wait_for_decoder(self):
        started=threading.Event(); release=threading.Event()
        def factory(*a,**kw):
            started.set(); release.wait(2); return FakePlayer()
        engine=PreviewEngine(factory)
        try:
            engine.open('first.mp4'); self.assertTrue(started.wait(1))
            before=time.monotonic(); latest=engine.open('second.mp4')
            self.assertLess(time.monotonic()-before,.1)
            self.assertEqual(latest,2)
            before=time.monotonic(); engine.close()
            self.assertLess(time.monotonic()-before,.1)
        finally:
            release.set(); engine.close(); engine.thread.join(2)
    def test_latest_selection_skips_intermediate(self):
        started=threading.Event(); release=threading.Event(); opened=[]
        def factory(path,**kw):
            opened.append(path)
            if path=='first':
                started.set(); release.wait(2)
            return FakePlayer()
        engine=PreviewEngine(factory)
        try:
            engine.open('first'); self.assertTrue(started.wait(1))
            engine.open('second'); engine.open('third'); release.set()
            deadline=time.monotonic()+2
            while 'third' not in opened and time.monotonic()<deadline: time.sleep(.01)
            self.assertEqual(opened,['first','third'])
        finally: engine.close(); engine.thread.join(2)

if __name__=='__main__': unittest.main()
