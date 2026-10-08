"""VaultVision 0.1: explicit session arming, OBS screenshots and replay saves."""
import base64,io,queue,threading,time,tkinter as tk
from tkinter import ttk
from PIL import Image
from detector import Detector,crop,ocr,FEED,NAME
from obs_client import OBS
from capture import Capture
from screen_reader import ScreenReader,replay_description
from game_state import GameGate,read_name,spectator_present,health_present,SPECTATOR,recover_death
from local_settings import load_password,save_password,password_path,load_settings,save_settings
import os,math,re

class App:
    def __init__(self,root):
        self.root=root; root.title('VaultVision 0.1 — prototype'); self.stop=threading.Event(); self.manual=threading.Event(); self.messages=queue.Queue(); self.worker=None; self.shutdown=threading.Event(); self.saved_clips=queue.Queue(); self.clip_labels=queue.Queue(); self.obs_password=''; self.obs_ready=False; self.auto_started=False; self.game_armed=False 
        self.source=tk.StringVar(value='Dark and Darker'); self.password=tk.StringVar(); self.name=tk.StringVar(); self.after=tk.StringVar(value='0'); self.tesseract=tk.StringVar(value=r'C:\Program Files\Tesseract-OCR\tesseract.exe')
        self.hud_timeout=tk.StringVar(value='30')
        self.capture_method=tk.StringVar(value='obs'); self.monitor=tk.StringVar(value='1')
        self.settings=load_settings()
        for key,var in [('source',self.source),('character_override',self.name),('save_delay',self.after),('tesseract',self.tesseract),('hud_timeout',self.hud_timeout),('capture_method',self.capture_method),('monitor',self.monitor)]:
            value=self.settings.get(key)
            if isinstance(value,(str,int,float)): var.set(str(value))
        try: self.password.set(load_password())
        except (OSError,UnicodeError): self.messages.put('Could not load the local password file; enter the password manually.')
        from ui_theme import build_ui
        build_ui(self)
        geometry=self.settings.get('window_geometry','')
        if isinstance(geometry,str) and re.fullmatch(r'\d{3,5}x\d{3,5}[+-]\d+[+-]\d+',geometry):
            root.geometry(geometry)
        self.gallery.restore_preferences(self.settings)
        root.protocol('WM_DELETE_WINDOW',self.close); root.after(100,self.poll)
        self.obs_password=self.password.get()
        threading.Thread(target=self.watch_obs,daemon=True).start()
    def watch_obs(self):
        from obs_launcher import launch_obs
        from pathlib import Path
        try:
            launched=launch_obs()
            self.say('Starting OBS with replay buffer, minimized to tray.' if launched else 'OBS is already running; reusing it.')
        except Exception as exc:
            self.say('Could not launch OBS: '+str(exc))
        last_path=''; last_error=''; connection=None
        while not self.shutdown.is_set():
            try:
                if connection is None:
                    connection=OBS(self.obs_password)
                    if not self.shutdown.is_set() and not connection.request('GetReplayBufferStatus')['outputActive']:
                        connection.request('StartReplayBuffer')
                    try:
                        seconds=replay_description(connection)
                        self.say(f'OBS replay duration: {seconds} seconds.')
                        if seconds<60:
                            self.say('Short replay buffer: set OBS Settings > Output > Replay Buffer > Maximum Replay Time to 60 seconds or more. A short buffer can lose the kill before recognition.')
                    except Exception as exc:
                        self.say('Could not check OBS replay duration: '+str(exc))
                    self.say('OBS replay buffer ready.'); self.obs_ready=True
                    last_error=''
                try:
                    path=connection.request('GetLastReplayBufferReplay').get('savedReplayPath','')
                except RuntimeError as exc:
                    # OBS has no last replay until the first completed save.
                    if 'No replay' in str(exc) or 'not saved' in str(exc).lower() or 'no saved' in str(exc).lower():
                        path=''
                    else: raise
                if path and path!=last_path and Path(path).is_file():
                    label='Replay'
                    if not self.clip_labels.empty(): label=self.clip_labels.get()
                    self.saved_clips.put((path,label)); last_path=path
            except Exception as exc:
                if connection:
                    connection.close(); connection=None
                text=str(exc)
                if text!=last_error: self.say('OBS setup: '+text); last_error=text
            self.shutdown.wait(2)
        if connection: connection.close()
    def request_save(self,obs,label):
        self.clip_labels.put(label)
        try: obs.request('SaveReplayBuffer')
        except Exception:
            # No completed file is expected for a rejected request.
            try: self.clip_labels.get_nowait()
            except queue.Empty: pass
            raise
    def store_password(self):
        try:
            save_password(self.password.get())
            self.say('Password saved locally; it will autofill on next launch.')
        except (OSError,ValueError): self.say('Could not save the password file.')
    def open_password_file(self):
        try:
            load_password()
            os.startfile(str(password_path()))
        except (OSError,AttributeError,UnicodeError): self.say('Could not open the password file: '+str(password_path()))
    def say(self,text): self.messages.put(time.strftime('%H:%M:%S')+' '+text)
    def poll(self):
        self.obs_password=self.password.get()
        while not self.saved_clips.empty():
            path,label=self.saved_clips.get(); self.gallery.add(path,label)
        while not self.messages.empty():
            self.log.configure(state='normal'); text=self.messages.get()
            tag='error' if 'Stopped:' in text or 'Could not' in text else 'kill' if 'KILL:' in text or 'DEATH:' in text else ''
            self.log.insert('end',text+'\n',tag)
            if 'OBS replay duration: ' in text:
                self.replay_label.configure(text=text.split('OBS replay duration: ',1)[1])
            if 'Active character: ' in text: self.character_label.configure(text='Character: '+text.split('Active character: ',1)[1])
            self.log.configure(state='normal'); self.log.see('end'); self.log.configure(state='disabled')
        if self.obs_ready and not self.auto_started and not getattr(self,'closing',False):
            self.auto_started=True; self.start()
        running=bool(self.worker and self.worker.is_alive())
        self.start_button.configure(state='disabled' if running else 'normal')
        self.status_label.configure(text='●  ARMED' if self.game_armed and running else '●  AUTO WATCH' if running else '●  DISARMED',fg='#c7a96b' if running else '#aca79b')
        for entry in self.entries: entry.configure(state='disabled' if running else 'normal')
        self.root.after(100,self.poll)
    def start(self):
        if self.worker and self.worker.is_alive(): return
        try:
            delay=float(self.after.get())
            if not math.isfinite(delay) or not 0<=delay<=30: raise ValueError()
            timeout=float(self.hud_timeout.get())
            if not math.isfinite(timeout) or not 1<=timeout<=600:
                self.say('HUD-absence timeout must be 1–600 seconds.'); return
        except ValueError: self.say('After-event delay must be 0–30 seconds.'); return
        method=self.capture_method.get().strip().lower()
        if method not in ('screen','obs'):
            self.say('Capture method must be screen or obs.'); return
        try:
            monitor=int(self.monitor.get())
            if monitor<1: raise ValueError()
        except ValueError:
            self.say('Monitor must be a positive whole number.'); return
        args=(self.source.get(),self.password.get(),self.name.get(),delay,self.tesseract.get(),timeout,method,monitor)
        self.auto_started=True; self.stop.clear(); self.manual.clear(); self.worker=threading.Thread(target=self.run,args=args,daemon=True); self.worker.start()
    def run(self,source,password,name,delay,executable,timeout,method='obs',monitor=1):
        obs=None; capture=None; due=None; due_label='Replay'; detector=Detector(name); last_name=''; scans=0; gate=GameGate(missing_seconds=timeout); reader=ScreenReader()
        try:
            obs=OBS(password)
            if not obs.request('GetReplayBufferStatus')['outputActive']: obs.request('StartReplayBuffer')
            capture=Capture(obs,source,method,monitor,self.say)
            capture.grab()
            self.say(f'Automatic monitoring started. Save delay: {delay:.1f}s. Waiting for your gameplay HUD.')
            while not self.stop.is_set():
                now=time.monotonic(); scan_started=now
                if self.manual.is_set():
                    self.manual.clear(); self.request_save(obs,'Manual'); self.say('Manual replay save requested.')
                if due is not None and now>=due:
                    self.request_save(obs,due_label); self.say('Event replay save requested; check the OBS output folder.'); due=None
                image=capture.grab()
                capture_done=time.monotonic()
                feed_started=time.monotonic()
                # Run feed OCR alongside the HUD checks, then gate events.
                hud_name,health,spectator,feed_text=reader.read(image,executable,gate.armed)
                was_armed=gate.armed
                armed,changed,reason=gate.update(hud_name,health,spectator,time.monotonic())
                self.game_armed=armed
                if changed: self.say(('Automatically armed: ' if armed else 'Automatically disarmed: ')+reason)
                if armed and not was_armed:
                    detector=Detector(name or hud_name)
                    self.say('Active character: '+detector.name); last_name=detector.name
                events=[]
                if armed or (was_armed and spectator):
                    if not was_armed: feed_text=ocr(crop(image,FEED),executable)
                    events=detector.process(feed_text,time.monotonic())
                    if spectator:
                        events=[event for event in events if event['kind']=='death']
                        if not events and not detector.dead and detector.name:
                            recovered=recover_death(image,executable,detector.name,time.monotonic())
                            detector.dead=True
                            events=[recovered or {'kind':'death','killer':'Unknown','victim':detector.name,'weapon':''}]
                    elif was_armed and detector.dead:
                        events=[event for event in events if event['kind']=='death']
                else: feed_text=''
                feed_done=time.monotonic()
                for event in events:
                    self.say(f"{event['kind'].upper()}: {event['killer']} → {event['victim']} ({event['weapon']})")
                    # Keep the first save deadline so rapid kills cannot evict its pre-roll.
                    if delay==0:
                        self.request_save(obs,event['kind'].title()+': '+event['killer']+' → '+event['victim']); self.say('Immediate event replay save requested.')
                    elif due is None:
                        due=time.monotonic()+delay; due_label=event['kind'].title()+': '+event['killer']+' → '+event['victim']
                scans+=1
                elapsed=time.monotonic()-scan_started
                if scans==1 or scans%20==0 or events:
                    self.say(f'Scan: {elapsed:.2f}s; capture: {capture_done-scan_started:.2f}s; parallel OCR checks: {feed_done-feed_started:.2f}s; feed lines: {len(feed_text.splitlines())}.')
                if elapsed>3 and scans%20==0: self.say('Slow scanning: recognition can lag. Send this timing log with the clip.')
                self.stop.wait(max(0,.5-(time.monotonic()-scan_started)))
        except Exception as e: self.say('Stopped: '+str(e))
        finally:
            self.game_armed=False
            reader.close()
            if capture: capture.close()
            if obs: obs.close()
            self.say('Disarmed. OBS replay buffer remains under your control.')
    def close(self):
        if getattr(self,'closing',False): return
        try:
            save_settings({'source':self.source.get(),'character_override':self.name.get(),
                           'save_delay':self.after.get(),'tesseract':self.tesseract.get(),
                           'hud_timeout':self.hud_timeout.get(),'capture_method':self.capture_method.get(),
                           'monitor':self.monitor.get(),'window_geometry':self.root.geometry(),
                           'muted':self.gallery.muted,'volume':self.gallery.volume.get()})
            save_password(self.password.get())
        except (OSError,ValueError):
            from tkinter import messagebox
            messagebox.showerror('Settings','Could not save settings locally.',parent=self.root)
        self.closing=True; self.stop.set(); self.shutdown.set(); self.gallery.close()
        self.close_done=threading.Event(); self.close_error=''
        self.status_label.configure(text='●  CLOSING OBS')
        password=self.password.get()
        def finish():
            connection=None
            try:
                # Let detection finish its in-flight request before stopping the buffer.
                if self.worker: self.worker.join(timeout=10)
                try:
                    connection=OBS(password)
                    from obs_shutdown import stop_replay_buffer
                    stop_replay_buffer(connection)
                except Exception:
                    pass  # Normal window-close still works without WebSocket access.
                finally:
                    if connection: connection.close()
                from obs_shutdown import close_obs_windows
                close_obs_windows()
            except Exception as exc: self.close_error=str(exc)
            finally: self.close_done.set()
        threading.Thread(target=finish,daemon=True).start()
        self.root.after(100,self.finish_close)
    def finish_close(self):
        if not self.close_done.is_set():
            self.root.after(100,self.finish_close); return
        if self.close_error:
            from tkinter import messagebox
            messagebox.showerror('OBS shutdown',self.close_error,parent=self.root)
        self.root.destroy()
if __name__=='__main__':
    import faulthandler,traceback
    diagnostic_path=password_path().parent/'crash.log'
    diagnostic_path.parent.mkdir(parents=True,exist_ok=True)
    diagnostic_file=diagnostic_path.open('a',encoding='utf-8',buffering=1)
    faulthandler.enable(file=diagnostic_file,all_threads=True)
    root=tk.Tk()
    def callback_error(kind,value,tb):
        traceback.print_exception(kind,value,tb,file=diagnostic_file)
    root.report_callback_exception=callback_error
    App(root); root.mainloop()
