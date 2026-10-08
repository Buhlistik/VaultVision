"""VaultVision 0.1: explicit session arming, OBS screenshots and replay saves."""
import base64,io,queue,threading,time,tkinter as tk
from tkinter import ttk
from PIL import Image
from pathlib import Path
import shutil
from activity_log import create_activity_logger,activity_log_path
from detector import Detector,crop,ocr,FEED,NAME
from obs_client import OBS
from capture import Capture
from obs_startup import wait_for_replay
from screen_reader import ScreenReader,replay_description
from game_state import GameGate,read_name,spectator_present,health_present,SPECTATOR,recover_death
from local_settings import load_password,save_password,password_path,load_settings,save_settings
import os,math,re

class App:
    def __init__(self,root):
        self.root=root; root.title('VaultVision 0.1 — prototype'); self.stop=threading.Event(); self.manual=threading.Event(); self.messages=queue.Queue(); self.worker=None; self.shutdown=threading.Event(); self.saved_clips=queue.Queue(); self.clip_labels=queue.Queue(); self.obs_password=''; self.obs_ready=False; self.auto_started=False; self.game_armed=False
        self.user_paused=False; self.phase='Waiting for gameplay'; self.phase_detail=''; self.obs_stage='Starting OBS'
        self.last_scan=0.; self.scan_count=0; self.pending_save_at=None; self.last_saved='No clips saved this session'; self.notice=''; self.notice_until=0.
        self.activity_logger=create_activity_logger()
        self.paused_seen={}; self.manual_busy=threading.Event()
        self.source=tk.StringVar(value='Dark and Darker'); self.password=tk.StringVar(); self.after=tk.StringVar(value='0'); self.tesseract=tk.StringVar(value=r'C:\Program Files\Tesseract-OCR\tesseract.exe')
        self.capture_method=tk.StringVar(value='obs'); self.monitor=tk.StringVar(value='1')
        self.settings=load_settings()
        self.capture_deaths=tk.BooleanVar(value=self.settings.get('capture_deaths',False) is True)
        self.deaths_enabled=threading.Event()
        self.capture_deaths.trace_add('write',self.update_death_capture)
        self.update_death_capture()
        for key,var in [('source',self.source),('save_delay',self.after),('tesseract',self.tesseract),('capture_method',self.capture_method),('monitor',self.monitor)]:
            value=self.settings.get(key)
            if isinstance(value,(str,int,float)): var.set(str(value))
        if not Path(self.tesseract.get()).is_file():
            discovered=shutil.which('tesseract')
            if discovered: self.tesseract.set(discovered)
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
    def update_death_capture(self,*args):
        if self.capture_deaths.get(): self.deaths_enabled.set()
        else: self.deaths_enabled.clear()

    def watch_obs(self):
        from obs_launcher import launch_obs
        from pathlib import Path
        try:
            launched=launch_obs()
            self.say('Starting OBS with replay buffer, minimized to tray. Waiting 8 seconds for startup…' if launched else 'OBS is already running; checking replay buffer readiness.')
            if launched and self.shutdown.wait(8): return
        except Exception as exc:
            self.say('Could not launch OBS: '+str(exc))
        last_path=''; last_error=''; connection=None
        while not self.shutdown.is_set():
            try:
                if connection is None:
                    connection=OBS(self.obs_password)
                    self.obs_stage='Waiting for OBS replay buffer'; self.say('Waiting for OBS replay buffer to become active…')
                    if not wait_for_replay(connection,self.shutdown):
                        connection.close(); connection=None; break
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
                    if (not last_path and str(exc)=='GetLastReplayBufferReplay failed') or 'No replay' in str(exc) or 'not saved' in str(exc).lower() or 'no saved' in str(exc).lower():
                        path=''
                    else: raise
                if path and path!=last_path and Path(path).is_file():
                    label='Replay'
                    if not self.clip_labels.empty(): label=self.clip_labels.get()
                    self.saved_clips.put((path,label)); last_path=path
            except Exception as exc:
                self.obs_ready=False; self.obs_stage='Connecting to OBS'
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
    def say(self,text):
        self.activity_logger.info(text)
        self.messages.put(time.strftime('%H:%M:%S')+' '+text)
    def choose_ocr(self):
        from tkinter import filedialog,messagebox
        path=filedialog.askopenfilename(parent=self.root,title='Choose Tesseract OCR once',
                                       filetypes=[('Tesseract executable','*.exe'),('All files','*')])
        if not path: return
        if not Path(path).is_file() or 'tesseract' not in Path(path).name.lower():
            messagebox.showerror('OCR setup','Choose the installed tesseract.exe.',parent=self.root); return
        self.tesseract.set(path)
        settings=load_settings(); settings['tesseract']=path
        try: save_settings(settings)
        except OSError:
            messagebox.showerror('OCR setup','Could not remember the executable location.',parent=self.root); return
        self.say('OCR setup saved. Future launches will use this executable.')
        self.ocr_label.configure(text='OCR: ready')
        if self.obs_ready and not self.user_paused: self.start()
    def open_activity_log(self):
        try: os.startfile(str(activity_log_path()))
        except OSError: self.say('Could not open activity log.')
    def toggle_monitoring(self):
        if self.worker and self.worker.is_alive():
            if not self.stop.is_set():
                self.user_paused=True; self.stop.set()
                self.say('Automatic clips paused by you. Use Resume automatic clips to continue.')
        else:
            self.user_paused=False; self.start()
    def manual_save(self):
        if not self.obs_ready: return
        if self.worker and self.worker.is_alive() and not self.stop.is_set():
            self.manual.set(); return
        if self.manual_busy.is_set(): return
        self.manual_busy.set()
        password=self.password.get()
        def save():
            connection=None
            try:
                connection=OBS(password); self.request_save(connection,'Manual')
                self.say('Manual replay save requested.')
            except Exception as exc: self.say('Could not save replay: '+str(exc))
            finally:
                if connection: connection.close()
                self.manual_busy.clear()
        threading.Thread(target=save,daemon=True).start()

    def poll(self):
        self.obs_password=self.password.get()
        while not self.saved_clips.empty():
            path,label=self.saved_clips.get(); self.gallery.add(path,label)
            self.last_saved='Last saved: '+Path(path).name
        while not self.messages.empty():
            text=self.messages.get()
            if 'OBS replay duration: ' in text:
                self.replay_label.configure(text=text.split('OBS replay duration: ',1)[1])
            if 'Active character: ' in text:
                self.character_label.configure(text='Character: '+text.split('Active character: ',1)[1])
            if 'Lobby confirmed:' in text:
                self.character_label.configure(text='Character: waiting for next match')
            if any(message in text for message in ('After-event delay must','Capture method must','Monitor must','Choose your installed Tesseract')):
                self.phase='Monitoring needs attention'; self.phase_detail=text[9:]
            if 'Could not' in text:
                self.notice=text[9:]; self.notice_until=time.monotonic()+10
            if 'Stopped:' in text:
                self.phase='Monitoring needs attention'; self.phase_detail=text.split('Stopped:',1)[1].strip()
        ocr_ready=Path(self.tesseract.get()).is_file()
        if self.obs_ready and ocr_ready and not self.user_paused and not self.auto_started and not getattr(self,'closing',False):
            self.auto_started=True; self.start()
        running=bool(self.worker and self.worker.is_alive())
        stopping=running and self.stop.is_set()
        self.start_button.configure(text='Pausing…' if stopping else 'Pause automatic clips' if running else 'Resume automatic clips' if self.user_paused else 'Enable automatic clips',
                                    state='disabled' if stopping or not self.obs_ready or not ocr_ready else 'normal')
        self.save_button.configure(state='normal' if self.obs_ready and not self.manual_busy.is_set() else 'disabled')
        if self.user_paused:
            heading='Automatic clips paused'; detail='Resume when you want automatic highlights. You can still save a clip manually.'
        elif not ocr_ready:
            heading='OCR setup needed'; detail='Open Settings and choose your installed Tesseract executable once.'
        elif not self.obs_ready:
            heading=self.obs_stage; detail='Preparing your replay buffer. Monitoring begins automatically when OBS is ready.'
        elif not running:
            heading=self.phase if self.phase=='Monitoring needs attention' else 'Automatic clips stopped'
            detail=self.phase_detail or 'Use Enable automatic clips to continue.'
        elif self.pending_save_at is not None:
            heading='Highlight detected'; detail=f'Saving your clip in {max(0,math.ceil(self.pending_save_at-time.monotonic()))} seconds…'
        else:
            heading=self.phase; detail=self.phase_detail
        self.status_label.configure(text='●  PAUSED' if self.user_paused else '●  WATCHING' if self.game_armed and running else '●  PREPARING' if not self.obs_ready else '●  WAITING',
                                    fg='#c7a96b' if running and not self.user_paused else '#aca79b')
        self.phase_label.configure(text=heading)
        self.detail_label.configure(text=detail)
        age=time.monotonic()-self.last_scan if self.last_scan else 0
        heartbeat=f'Last screen check {int(age)}s ago · {self.scan_count} checks' if running and self.last_scan else 'Monitoring resumes only when you choose Resume.' if self.user_paused else ''
        if running and self.last_scan and age>8: heartbeat='Screen recognition in progress… '+heartbeat
        self.heartbeat_label.configure(text=heartbeat)
        self.saved_label.configure(text=self.notice if time.monotonic()<self.notice_until else self.last_saved)
        for entry in self.entries: entry.configure(state='disabled' if running else 'normal')
        self.ocr_button.configure(state='disabled' if running else 'normal')
        self.root.after(100,self.poll)
    def start(self):
        if not self.obs_ready:
            self.say('Waiting for OBS startup and replay buffer readiness.'); return
        if self.worker and self.worker.is_alive(): return
        try:
            delay=float(self.after.get())
            if not math.isfinite(delay) or not 0<=delay<=30: raise ValueError()
        except ValueError: self.say('After-event delay must be 0–30 seconds.'); return
        method=self.capture_method.get().strip().lower()
        if method not in ('screen','obs'):
            self.say('Capture method must be screen or obs.'); return
        try:
            monitor=int(self.monitor.get())
            if monitor<1: raise ValueError()
        except ValueError:
            self.say('Monitor must be a positive whole number.'); return
        if not Path(self.tesseract.get()).is_file():
            self.say('Choose your installed Tesseract executable in Settings.'); return
        args=(self.source.get(),self.password.get(),'',delay,self.tesseract.get(),None,method,monitor)
        self.user_paused=False; self.phase='Checking gameplay'; self.phase_detail='Looking for your health bar; spectator controls must be absent.'
        self.auto_started=True; self.last_scan=0.; self.scan_count=0; self.stop.clear(); self.manual.clear(); self.worker=threading.Thread(target=self.run,args=args,daemon=True); self.worker.start()
    def run(self,source,password,name,delay,executable,timeout,method='obs',monitor=1):
        obs=None; capture=None; due=None; due_label='Replay'; detector=Detector(name); last_name=''; scans=0; was_lobby=False; gate=GameGate(missing_seconds=timeout); reader=ScreenReader()
        try:
            obs=OBS(password)
            if not obs.request('GetReplayBufferStatus')['outputActive']:
                raise RuntimeError('OBS replay buffer is not active yet. Wait for OBS readiness before starting detection.')
            capture=Capture(obs,source,method,monitor,self.say)
            capture.grab()
            self.say(f'Automatic monitoring started. Save delay: {delay:.1f}s. Waiting for your gameplay HUD.')
            while not self.stop.is_set():
                now=time.monotonic(); scan_started=now
                if self.manual.is_set():
                    self.manual.clear(); self.request_save(obs,'Manual'); self.say('Manual replay save requested.')
                if due is not None and due_label.startswith('Death:') and not self.deaths_enabled.is_set():
                    due=None; self.pending_save_at=None
                if due is not None and now>=due:
                    self.request_save(obs,due_label); self.say('Event replay save requested; check the OBS output folder.'); due=None; self.pending_save_at=None
                image=capture.grab()
                capture_done=time.monotonic()
                feed_started=time.monotonic()
                # Run feed OCR alongside the HUD checks, then gate events.
                hud_name,health,spectator,feed_text=reader.read(image,executable,gate.armed,need_name=not bool(detector.name))
                was_armed=gate.armed
                armed,changed,reason=gate.update(hud_name,health,spectator,time.monotonic(),lobby=reader.lobby)
                if gate.in_lobby and not was_lobby:
                    detector=Detector(name); last_name=''; self.paused_seen={}
                    self.say('Lobby confirmed: spectator lock and character state reset. Waiting for your next match.')
                was_lobby=gate.in_lobby
                self.game_armed=armed
                if reader.lobby:
                    self.phase='In the lobby'; self.phase_detail='Ready for your next match. Automatic clips will activate in gameplay.'
                elif gate.spectating:
                    self.phase='Spectating'; self.phase_detail='Automatic clips are paused until you return to the lobby.'
                elif armed and not detector.name:
                    self.phase='Reading your character name'; self.phase_detail='Gameplay found. Identifying your character for killfeed matching.'
                elif armed and health:
                    self.phase='Watching the killfeed'; self.phase_detail='Automatic kill clips are active.'
                elif armed:
                    self.phase='Waiting for gameplay HUD'; self.phase_detail='Your match state is preserved through floor transitions.'
                else:
                    self.phase='Checking gameplay'; self.phase_detail='Looking for your health bar and checking for spectator controls.'
                if changed: self.say(('Automatically armed: ' if armed else 'Automatically disarmed: ')+reason)
                if armed and not was_armed:
                    detector=Detector(name); detector.seen=dict(self.paused_seen)
                    last_name=''
                    if not name: self.say('Gameplay confirmed. Reading your character name…')
                if armed and health and not spectator and not detector.name:
                    detector.update_name(hud_name)
                if armed and detector.name and detector.name!=last_name:
                    self.say('Active character: '+detector.name); last_name=detector.name
                events=[]
                if not reader.lobby and (armed or (was_armed and spectator)):
                    if not was_armed: feed_text=ocr(crop(image,FEED),executable)
                    events=detector.process(feed_text,time.monotonic())
                    if spectator:
                        events=[event for event in events if event['kind']=='death']
                        if self.deaths_enabled.is_set() and not events and not detector.dead and detector.name:
                            recovered=recover_death(image,executable,detector.name,time.monotonic())
                            detector.dead=True
                            events=[recovered or {'kind':'death','killer':'Unknown','victim':detector.name,'weapon':''}]
                    elif was_armed and detector.dead:
                        events=[event for event in events if event['kind']=='death']
                else: feed_text=''
                if not self.deaths_enabled.is_set():
                    events=[event for event in events if event['kind']=='kill']
                feed_done=time.monotonic(); self.last_scan=feed_done; self.scan_count+=1
                for event in events:
                    self.say(f"{event['kind'].upper()}: {event['killer']} → {event['victim']} ({event['weapon']})")
                    # Keep the first save deadline so rapid kills cannot evict its pre-roll.
                    if delay==0:
                        self.request_save(obs,event['kind'].title()+': '+event['killer']+' → '+event['victim']); self.say('Immediate event replay save requested.')
                    elif due is None:
                        due=time.monotonic()+delay; due_label=event['kind'].title()+': '+event['killer']+' → '+event['victim']; self.pending_save_at=due
                scans+=1
                elapsed=time.monotonic()-scan_started
                if scans==1 or scans%20==0 or events:
                    self.say(f'Scan: {elapsed:.2f}s; capture: {capture_done-scan_started:.2f}s; parallel OCR checks: {feed_done-feed_started:.2f}s; feed lines: {len(feed_text.splitlines())}.')
                if elapsed>3 and scans%20==0: self.say('Slow scanning: recognition can lag. Send this timing log with the clip.')
                self.stop.wait(max(0,.5-(time.monotonic()-scan_started)))
        except Exception as e: self.say('Stopped: '+str(e))
        finally:
            self.game_armed=False
            if self.user_paused: self.paused_seen=dict(detector.seen)
            if due is not None and obs and self.user_paused and (not due_label.startswith('Death:') or self.deaths_enabled.is_set()):
                try:
                    self.request_save(obs,due_label); self.say('Saved pending highlight before pausing.')
                except Exception as exc: self.say('Could not save pending highlight: '+str(exc))
            self.pending_save_at=None
            reader.close()
            if capture: capture.close()
            if obs: obs.close()
            self.say('Disarmed. OBS replay buffer remains under your control.')
    def close(self):
        if getattr(self,'closing',False): return
        try:
            save_settings({'source':self.source.get(),
                           'save_delay':self.after.get(),'tesseract':self.tesseract.get(),
                           'capture_method':self.capture_method.get(),
                           'monitor':self.monitor.get(),'capture_deaths':self.capture_deaths.get(),'window_geometry':self.root.geometry(),
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
