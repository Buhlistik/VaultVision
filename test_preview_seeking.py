import threading,time,unittest
from preview_engine import PreviewEngine


class Pixels:
    def get_size(self): return (2,1)
    def to_bytearray(self): return [bytearray([0,0,0]*2)]


class Player:
    def __init__(self):
        self.pauses=[]; self.seeks=[]; self.position=0.
        self.frame_block=threading.Event(); self.frame_block.set()
        self.entered=threading.Event()
    def set_size(self,*a): pass
    def set_mute(self,*a): pass
    def set_volume(self,*a): pass
    def set_pause(self,value): self.pauses.append(value)
    def get_metadata(self): return {'duration':60}
    def seek(self,value,**kwargs): self.seeks.append(value); self.position=value
    def get_frame(self):
        self.entered.set(); self.frame_block.wait(2)
        return (Pixels(),self.position),.01
    def close_player(self): pass


def until(check):
    deadline=time.monotonic()+2
    while not check():
        if time.monotonic()>deadline: raise AssertionError('Decoder did not respond')
        time.sleep(.005)


class SeekTests(unittest.TestCase):
    def setup_engine(self):
        player=Player(); engine=PreviewEngine(lambda *a,**kw:player)
        engine.open('clip')
        until(lambda: bool(player.pauses))
        return player,engine

    def test_play_after_seek_is_not_overridden_by_preview(self):
        player,engine=self.setup_engine()
        try:
            player.frame_block.clear(); player.entered.clear()
            engine.command('seek',20)
            self.assertTrue(player.entered.wait(1))
            engine.command('toggle')
            player.frame_block.set()
            until(lambda: player.pauses[-1] is False and len(player.pauses)>=3)
            self.assertFalse(player.pauses[-1])
        finally: player.frame_block.set(); engine.close(); engine.thread.join(2)

    def test_seek_preserves_playing_state(self):
        player,engine=self.setup_engine()
        try:
            engine.command('toggle')
            until(lambda: player.pauses[-1] is False)
            engine.command('seek',30)
            until(lambda: player.seeks==[30])
            time.sleep(.05)
            self.assertFalse(player.pauses[-1])
        finally: engine.close(); engine.thread.join(2)

    def test_queued_seeks_keep_only_latest(self):
        player,engine=self.setup_engine()
        try:
            player.frame_block.clear(); player.entered.clear()
            engine.command('toggle')
            self.assertTrue(player.entered.wait(1))
            for value in range(10,50): engine.command('seek',value)
            player.frame_block.set()
            until(lambda: bool(player.seeks))
            self.assertEqual(player.seeks,[49])
        finally: player.frame_block.set(); engine.close(); engine.thread.join(2)


if __name__=='__main__': unittest.main()
