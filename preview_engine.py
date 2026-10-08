"""One worker owns the decoder; Tk only receives the latest display frame."""
import queue
import threading
import time
from PIL import Image

class PreviewEngine:
    def __init__(self,factory=None):
        self.commands=queue.Queue(); self.frames=queue.Queue(maxsize=1)
        self.wake=threading.Event(); self.stop=threading.Event(); self.generation=0; self.factory=factory
        self.thread=threading.Thread(target=self._run,daemon=True); self.thread.start()
    def open(self,path):
        self.generation+=1
        self.commands.put(('open',self.generation,path))
        self.wake.set()
        return self.generation
    def command(self,kind,value=None):
        self.commands.put((kind,self.generation,value)); self.wake.set()
    def close(self): self.stop.set(); self.wake.set()
    def wait(self,delay):
        self.wake.wait(delay); self.wake.clear()
    def publish(self,value):
        try: self.frames.get_nowait()
        except queue.Empty: pass
        try: self.frames.put_nowait(value)
        except queue.Full: pass
    def _run(self):
        player=None; token=0; first=False; paused=True; duration=0.; eof=False; muted=False; ready=False; position=0.; volume=.7; last_display=0.; seek_target=None; display_width=640; resize_target=None
        try:
            while not self.stop.is_set():
                commands=[]
                while True:
                    try: commands.append(self.commands.get_nowait())
                    except queue.Empty: break
                # Only the newest selection is worth opening.
                opens=[i for i,c in enumerate(commands) if c[0]=='open']
                if opens:
                    settings=[command for command in commands[:opens[-1]] if command[0] in ('size','volume','mute')]
                    commands=settings+commands[opens[-1]:]
                # Drop superseded seeks/settings before touching the decoder.
                latest={}
                for index,command in enumerate(commands):
                    kind=command[0]
                    if kind in ('seek','restart','mute','volume','size'):
                        latest['position' if kind in ('seek','restart') else kind]=index
                commands=[command for index,command in enumerate(commands)
                          if command[0] not in ('seek','restart','mute','volume','size') or
                          latest['position' if command[0] in ('seek','restart') else command[0]]==index]
                for kind,generation,value in commands:
                    try:
                        if kind=='size':
                            display_width=max(320,min(3840,int(value)))
                            if player:
                                player.set_size(display_width,-1)
                                if ready:
                                    resize_target=display_width
                                    player.set_mute(True); player.set_pause(False)
                                    if paused:
                                        player.seek(max(0,min(position,max(0,duration-.05))),relative=False,accurate=True)
                                        seek_target=max(0,min(position,max(0,duration-.05)))
                                    first=True; eof=False
                            continue
                        if kind=='volume':
                            volume=max(0,min(1,float(value)))
                            if player and ready: player.set_volume(volume)
                            continue
                        if kind=='mute':
                            muted=bool(value)
                            if player and ready: player.set_mute(muted)
                            continue
                        if kind=='open':
                            if generation!=self.generation: continue
                            if player: player.close_player(); player=None
                            token=generation
                            if self.factory: factory=self.factory
                            else:
                                from ffpyplayer.player import MediaPlayer
                                factory=MediaPlayer
                            player=factory(value,ff_opts={'out_fmt':'rgb24','volume':volume})
                            player.set_size(display_width,-1); player.set_mute(True)
                            first=True; paused=True; duration=0.; eof=False; ready=False; position=0.; seek_target=None; resize_target=None
                        elif player and generation==token and ready:
                            if kind=='toggle':
                                if eof:
                                    player.set_pause(False); player.set_mute(True)
                                    player.seek(0,relative=False); eof=False; first=True; seek_target=0.
                                paused=not paused
                                if not first: player.set_pause(paused)
                                self.publish((token,'state',(None,position,duration,paused)))
                            elif kind=='seek':
                                player.set_mute(True); player.set_pause(False)
                                player.seek(float(value),relative=False,accurate=True); eof=False
                                first=True; seek_target=float(value)
                            elif kind=='restart':
                                player.set_mute(True); player.set_pause(False)
                                player.seek(0,relative=False)
                                paused=False; first=True; eof=False; seek_target=0.
                            elif kind=='mute':
                                muted=bool(value); player.set_mute(muted)
                    except Exception as exc:
                        self.publish((generation,'error',str(exc)))
                        if player: player.close_player(); player=None
                if not player or (paused and not first):
                    self.wait(.04); continue
                try:
                    frame,wait=player.get_frame()
                    duration=float(player.get_metadata().get('duration',0) or 0)
                    if wait=='eof':
                        eof=True; paused=True
                        self.publish((token,'state',(None,duration,duration,True))); continue
                    if frame:
                        pixels,pts=frame
                        if resize_target is not None and pixels.get_size()[0]!=resize_target:
                            self.wait(.005); continue
                        resize_target=None
                        # A seek may leave old frames queued. Do not pause on
                        # those frames before the requested position arrives.
                        if seek_target is not None and abs(pts-seek_target)>.25:
                            self.wait(.005); continue
                        seek_target=None
                        position=pts
                        if not ready: player.set_volume(volume)
                        ready=True
                        now=time.monotonic()
                        display=first or now-last_display>=1/30
                        if first:
                            player.set_pause(paused); player.set_mute(muted)
                            first=False
                        if display and token==self.generation:
                            image=Image.frombytes('RGB',pixels.get_size(),bytes(pixels.to_bytearray()[0]))
                            last_display=now
                            self.publish((token,'state',(image,pts,duration,paused)))
                    delay=.03 if isinstance(wait,str) else max(.005,min(.05,float(wait or .005)))
                    self.stop.wait(delay)
                except Exception as exc:
                    self.publish((token,'error',str(exc)))
                    player.close_player(); player=None
        finally:
            if player: player.close_player()
