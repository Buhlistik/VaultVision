"""One worker owns the decoder; Tk only receives the latest display frame."""
import queue
import threading
from PIL import Image

class PreviewEngine:
    def __init__(self,factory=None):
        self.commands=queue.Queue(); self.frames=queue.Queue(maxsize=1)
        self.stop=threading.Event(); self.generation=0; self.factory=factory
        self.thread=threading.Thread(target=self._run,daemon=True); self.thread.start()
    def open(self,path):
        self.generation+=1
        self.commands.put(('open',self.generation,path))
        return self.generation
    def command(self,kind,value=None):
        self.commands.put((kind,self.generation,value))
    def close(self): self.stop.set()
    def publish(self,value):
        try: self.frames.get_nowait()
        except queue.Empty: pass
        try: self.frames.put_nowait(value)
        except queue.Full: pass
    def _run(self):
        player=None; token=0; first=False; paused=True; duration=0.; eof=False; muted=False
        try:
            while not self.stop.is_set():
                commands=[]
                while True:
                    try: commands.append(self.commands.get_nowait())
                    except queue.Empty: break
                # Only the newest selection is worth opening.
                opens=[i for i,c in enumerate(commands) if c[0]=='open']
                if opens: commands=commands[opens[-1]:]
                for kind,generation,value in commands:
                    try:
                        if kind=='open':
                            if generation!=self.generation: continue
                            if player: player.close_player(); player=None
                            token=generation
                            if self.factory: factory=self.factory
                            else:
                                from ffpyplayer.player import MediaPlayer
                                factory=MediaPlayer
                            player=factory(value,ff_opts={'out_fmt':'rgb24','volume':0.7})
                            player.set_size(640,-1); player.set_mute(True)
                            first=True; paused=False; duration=0.; eof=False
                        elif player and generation==token:
                            if kind=='toggle':
                                if eof: player.seek(0,relative=False); eof=False
                                paused=not paused; player.set_pause(paused)
                                self.publish((token,'state',(None,player.get_pts(),duration,paused)))
                            elif kind=='seek':
                                player.seek(float(value),relative=False); eof=False
                                player.set_pause(False); first=True
                            elif kind=='restart':
                                player.seek(0,relative=False); player.set_pause(False)
                                paused=False; first=False; eof=False
                            elif kind=='mute':
                                muted=bool(value); player.set_mute(muted)
                    except Exception as exc:
                        self.publish((generation,'error',str(exc)))
                        if player: player.close_player(); player=None
                if not player or (paused and not first):
                    self.stop.wait(.04); continue
                try:
                    frame,wait=player.get_frame()
                    duration=float(player.get_metadata().get('duration',0) or 0)
                    if wait=='eof':
                        eof=True; paused=True
                        self.publish((token,'state',(None,duration,duration,True))); continue
                    if frame:
                        pixels,pts=frame
                        image=Image.frombytes('RGB',pixels.get_size(),bytes(pixels.to_bytearray()[0]))
                        if first:
                            player.set_pause(True); player.set_mute(muted)
                            first=False; paused=True
                        if token==self.generation:
                            self.publish((token,'state',(image,pts,duration,paused)))
                    delay=.03 if isinstance(wait,str) else max(.005,min(.05,float(wait or .005)))
                    self.stop.wait(delay)
                except Exception as exc:
                    self.publish((token,'error',str(exc)))
                    player.close_player(); player=None
        finally:
            if player: player.close_player()
