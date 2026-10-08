"""VaultVision 0.1: explicit session arming, OBS screenshots and replay saves."""
import base64,io,queue,threading,time,tkinter as tk
from tkinter import ttk
from PIL import Image
from detector import Detector,crop,ocr,FEED,NAME
from obs_client import OBS
from local_settings import load_password,save_password,password_path
import os

class App:
    def __init__(self,root):
        self.root=root; root.title('VaultVision 0.1 — prototype'); self.stop=threading.Event(); self.manual=threading.Event(); self.messages=queue.Queue(); self.worker=None
        self.source=tk.StringVar(value='Dark and Darker'); self.password=tk.StringVar(); self.name=tk.StringVar(); self.after=tk.StringVar(value='0'); self.tesseract=tk.StringVar(value=r'C:\Program Files\Tesseract-OCR\tesseract.exe')
        try: self.password.set(load_password())
        except (OSError,UnicodeError): self.messages.put('Could not load the local password file; enter the password manually.')
        from ui_theme import build_ui
        build_ui(self)
        root.protocol('WM_DELETE_WINDOW',self.close); root.after(100,self.poll)
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
        while not self.messages.empty():
            self.log.configure(state='normal'); text=self.messages.get()
            tag='error' if 'Stopped:' in text or 'Could not' in text else 'kill' if 'KILL:' in text or 'DEATH:' in text else ''
            self.log.insert('end',text+'\n',tag)
            if 'Active character: ' in text: self.character_label.configure(text='Character: '+text.split('Active character: ',1)[1])
            self.log.configure(state='normal'); self.log.see('end'); self.log.configure(state='disabled')
        running=bool(self.worker and self.worker.is_alive())
        self.start_button.configure(state='disabled' if running else 'normal')
        self.status_label.configure(text='●  MONITORING' if running else '●  DISARMED',fg='#c7a96b' if running else '#aca79b')
        for entry in self.entries: entry.configure(state='disabled' if running else 'normal')
        self.root.after(100,self.poll)
    def start(self):
        if self.worker and self.worker.is_alive(): return
        try:
            delay=float(self.after.get())
            if not 0<=delay<=30: raise ValueError()
        except ValueError: self.say('After-event delay must be 0–30 seconds.'); return
        args=(self.source.get(),self.password.get(),self.name.get(),delay,self.tesseract.get())
        self.stop.clear(); self.manual.clear(); self.worker=threading.Thread(target=self.run,args=args,daemon=True); self.worker.start()
    def run(self,source,password,name,delay,executable):
        obs=None; due=None; detector=Detector(name); last_name=''; scans=0
        try:
            obs=OBS(password)
            if not obs.request('GetReplayBufferStatus')['outputActive']: raise RuntimeError('Start the OBS Replay Buffer before arming.')
            obs.request('GetSourceScreenshot',sourceName=source,imageFormat='png',imageWidth=1920,imageHeight=1080)
            self.say(f'Armed. Replay save delay: {delay:.1f}s. Capture must show the complete HUD.')
            while not self.stop.is_set():
                now=time.monotonic(); scan_started=now
                if self.manual.is_set():
                    self.manual.clear(); obs.request('SaveReplayBuffer'); self.say('Manual replay save requested.')
                if due is not None and now>=due:
                    obs.request('SaveReplayBuffer'); self.say('Event replay save requested; check the OBS output folder.'); due=None
                data=obs.request('GetSourceScreenshot',sourceName=source,imageFormat='png',imageWidth=1920,imageHeight=1080)['imageData']
                capture_done=time.monotonic()
                image=Image.open(io.BytesIO(base64.b64decode(data.split(',',1)[1])))
                if not name and (not detector.name or scans%10==0): detector.update_name(ocr(crop(image,NAME),executable,7))
                if detector.name!=last_name: last_name=detector.name; self.say('Active character: '+last_name)
                feed_started=time.monotonic()
                feed_text=ocr(crop(image,FEED),executable)
                feed_done=time.monotonic()
                events=detector.process(feed_text,feed_done)
                for event in events:
                    self.say(f"{event['kind'].upper()}: {event['killer']} → {event['victim']} ({event['weapon']})")
                    # Keep the first save deadline so rapid kills cannot evict its pre-roll.
                    if delay==0:
                        obs.request('SaveReplayBuffer'); self.say('Immediate event replay save requested.')
                    elif due is None: due=time.monotonic()+delay
                scans+=1
                elapsed=time.monotonic()-scan_started
                if scans==1 or scans%20==0 or events:
                    self.say(f'Scan: {elapsed:.2f}s; capture: {capture_done-scan_started:.2f}s; feed OCR: {feed_done-feed_started:.2f}s; feed lines: {len(feed_text.splitlines())}.')
                if elapsed>3 and scans%20==0: self.say('Slow scanning: recognition can lag. Send this timing log with the clip.')
                if detector.dead:
                    self.say('Death detected: identity frozen. Disarm before spectating; re-arm for next match.')
                    if due is not None:
                        if not self.stop.wait(max(0,due-time.monotonic())): obs.request('SaveReplayBuffer'); self.say('Death replay save requested.')
                    break
                self.stop.wait(max(0,.5-(time.monotonic()-scan_started)))
        except Exception as e: self.say('Stopped: '+str(e))
        finally:
            if obs: obs.close()
            self.say('Disarmed. OBS replay buffer remains under your control.')
    def close(self): self.stop.set(); self.root.destroy()
if __name__=='__main__':
    root=tk.Tk(); App(root); root.mainloop()
