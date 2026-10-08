"""VaultVision 0.1: explicit session arming, OBS screenshots and replay saves."""
import base64,io,queue,threading,time,tkinter as tk
from tkinter import ttk
from PIL import Image
from detector import Detector,crop,ocr,FEED,NAME
from obs_client import OBS

class App:
    def __init__(self,root):
        self.root=root; root.title('VaultVision 0.1 — prototype'); self.stop=threading.Event(); self.manual=threading.Event(); self.messages=queue.Queue(); self.worker=None
        self.source=tk.StringVar(value='Dark and Darker'); self.password=tk.StringVar(); self.name=tk.StringVar(); self.after=tk.StringVar(value='10'); self.tesseract=tk.StringVar(value=r'C:\Program Files\Tesseract-OCR\tesseract.exe')
        frame=ttk.Frame(root,padding=18); frame.pack(fill='both',expand=True)
        for row,(label,var) in enumerate([('OBS source name',self.source),('OBS WebSocket password',self.password),('Character name (blank = automatic)',self.name),('Seconds after event',self.after),('Tesseract executable',self.tesseract)]):
            ttk.Label(frame,text=label).grid(row=row,column=0,sticky='w',pady=5)
            ttk.Entry(frame,textvariable=var,width=48,show='*' if var is self.password else '').grid(row=row,column=1)
        buttons=ttk.Frame(frame); buttons.grid(row=5,columnspan=2,pady=12)
        self.start_button=ttk.Button(buttons,text='Arm session',command=self.start); self.start_button.pack(side='left')
        ttk.Button(buttons,text='Disarm',command=self.stop.set).pack(side='left',padx=8)
        ttk.Button(buttons,text='Save replay now',command=self.manual.set).pack(side='left')
        ttk.Label(frame,text='Arm for your match. Disarm before spectating or switching characters.\nOBS replay length controls clip length; use 60 seconds initially.').grid(row=6,columnspan=2)
        self.log=tk.Text(frame,width=85,height=14,state='disabled'); self.log.grid(row=7,columnspan=2,pady=12)
        root.protocol('WM_DELETE_WINDOW',self.close); root.after(100,self.poll)
    def say(self,text): self.messages.put(text)
    def poll(self):
        while not self.messages.empty():
            self.log.configure(state='normal'); self.log.insert('end',self.messages.get()+'\n'); self.log.see('end'); self.log.configure(state='disabled')
        self.start_button.configure(state='disabled' if self.worker and self.worker.is_alive() else 'normal')
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
            self.say('Armed. Capture must show your gameplay, with the complete HUD.')
            while not self.stop.is_set():
                now=time.monotonic()
                if self.manual.is_set():
                    self.manual.clear(); obs.request('SaveReplayBuffer'); self.say('Manual replay save requested.')
                if due is not None and now>=due:
                    obs.request('SaveReplayBuffer'); self.say('Event replay save requested; check the OBS output folder.'); due=None
                data=obs.request('GetSourceScreenshot',sourceName=source,imageFormat='png',imageWidth=1920,imageHeight=1080)['imageData']
                image=Image.open(io.BytesIO(base64.b64decode(data.split(',',1)[1])))
                if not name and scans%2==0: detector.update_name(ocr(crop(image,NAME),executable,7))
                if detector.name!=last_name: last_name=detector.name; self.say('Active character: '+last_name)
                for event in detector.process(ocr(crop(image,FEED),executable),time.monotonic()):
                    self.say(f"{event['kind'].upper()}: {event['killer']} → {event['victim']} ({event['weapon']})")
                    # Keep the first save deadline so rapid kills cannot evict its pre-roll.
                    if due is None: due=time.monotonic()+delay
                scans+=1
                if detector.dead:
                    self.say('Death detected: identity frozen. Disarm before spectating; re-arm for next match.')
                    if due is not None:
                        if not self.stop.wait(max(0,due-time.monotonic())): obs.request('SaveReplayBuffer'); self.say('Death replay save requested.')
                    break
                self.stop.wait(.5)
        except Exception as e: self.say('Stopped: '+str(e))
        finally:
            if obs: obs.close()
            self.say('Disarmed. OBS replay buffer remains under your control.')
    def close(self): self.stop.set(); self.root.destroy()
if __name__=='__main__':
    root=tk.Tk(); App(root); root.mainloop()
