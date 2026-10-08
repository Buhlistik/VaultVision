"""Persistent clip index and embedded FFmpeg video/audio preview."""
import json,os
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog
from PIL import Image,ImageTk
from local_settings import password_path

class ClipGallery:
    def __init__(self,parent,say):
        self.say=say; self.player=None; self.job=None; self.photo=None; self.path=None; self.first_frame=False; self.eof=False
        self.index=password_path().parent/'clips.json'
        try:
            records=json.loads(self.index.read_text(encoding='utf-8'))
            self.records=[r for r in records if isinstance(r,dict) and isinstance(r.get('path'),str) and Path(r['path']).is_file()] if isinstance(records,list) else []
        except (OSError,ValueError): self.records=[]
        outer=tk.Frame(parent,bg='#171a1f',padx=18,pady=16); outer.pack(fill='both',expand=True)
        top=tk.Frame(outer,bg='#171a1f'); top.pack(fill='x')
        tk.Label(top,text='SAVED CLIPS',bg='#171a1f',fg='#c7a96b',font=('Segoe UI',11,'bold')).pack(side='left')
        ttk.Button(top,text='Import clips',command=self.import_clips).pack(side='right')
        self.list=tk.Listbox(outer,height=5,bg='#101216',fg='#e7dfcd',selectbackground='#4c4030',
                             relief='flat',font=('Segoe UI',10),exportselection=False)
        self.list.pack(fill='x',pady=12); self.list.bind('<<ListboxSelect>>',self.select)
        self.screen=tk.Label(outer,text='Select a saved clip to preview',bg='#08090b',fg='#aca79b',height=14)
        self.screen.pack(fill='both',expand=True)
        buttons=tk.Frame(outer,bg='#171a1f'); buttons.pack(fill='x',pady=(12,0))
        self.play=ttk.Button(buttons,text='Play / Pause',command=self.toggle); self.play.pack(side='left')
        ttk.Button(buttons,text='Restart',command=self.restart).pack(side='left',padx=8)
        ttk.Button(buttons,text='Open folder',command=self.open_folder).pack(side='right')
        self.time=tk.Label(buttons,text='0:00',bg='#171a1f',fg='#aca79b'); self.time.pack(side='right',padx=12)
        self.refresh()
    def refresh(self):
        selected=self.list.curselection()
        previous=self.list.get(selected[0]) if selected else None
        self.list.delete(0,'end')
        for record in self.records:
            self.list.insert('end',record.get('label','Replay')+'  •  '+Path(record['path']).name)
        if previous:
            for i in range(self.list.size()):
                if self.list.get(i)==previous: self.list.selection_set(i); break
    def add(self,path,label='Replay'):
        path=str(Path(path))
        if not Path(path).is_file() or any(r['path']==path for r in self.records): return
        self.records.insert(0,{'path':path,'label':label})
        self.refresh()
        try:
            self.index.parent.mkdir(parents=True,exist_ok=True)
            temporary=self.index.with_suffix('.tmp'); temporary.write_text(json.dumps(self.records,indent=2),encoding='utf-8'); temporary.replace(self.index)
        except OSError: self.say('Could not persist clip history.')
        self.say('Saved clip: '+Path(path).name)
        # Do not interrupt playback or automatically play audio during a match.
    def import_clips(self):
        for path in filedialog.askopenfilenames(filetypes=[('Video files','*.mp4 *.mkv *.mov *.flv *.ts'),('All files','*.*')]): self.add(path,'Imported')
    def select(self,event=None):
        choice=self.list.curselection()
        if not choice: return
        self.close_player()
        self.path=self.records[choice[0]]['path']
        try:
            from ffpyplayer.player import MediaPlayer
            self.player=MediaPlayer(self.path,ff_opts={'out_fmt':'rgb24','volume':0.7})
            self.player.set_size(640,-1); self.player.set_mute(True)
            self.first_frame=True; self.eof=False
            self.screen.configure(text='',height=0)
            self.tick()
        except Exception as exc:
            self.close_player(); self.screen.configure(text='Preview could not open',image='')
            self.say('Preview error: '+str(exc))
    def tick(self):
        self.job=None
        if not self.player: return
        try:
            frame,delay=self.player.get_frame()
            if delay=='eof':
                self.eof=True; return
            if frame:
                pixels,pts=frame
                image=Image.frombytes('RGB',pixels.get_size(),bytes(pixels.to_bytearray()[0]))
                image.thumbnail((max(320,self.screen.winfo_width()),max(180,self.screen.winfo_height())))
                self.photo=ImageTk.PhotoImage(image); self.screen.configure(image=self.photo,text='')
                self.time.configure(text=f'{int(pts)//60}:{int(pts)%60:02d}')
                if self.first_frame:
                    self.player.set_pause(True); self.player.set_mute(False); self.first_frame=False
            wait=100 if delay=='paused' else max(10,min(100,int(float(delay or .02)*1000)))
            self.job=self.screen.after(wait,self.tick)
        except Exception as exc:
            self.say('Preview error: '+str(exc)); self.close_player()
    def toggle(self):
        if not self.player: return
        if self.eof: self.restart(); return
        self.player.set_pause(not self.player.get_pause())
    def restart(self):
        if not self.path: return
        # Reopen to reset EOF decoder state reliably.
        self.select()
        if self.player:
            self.first_frame=False; self.player.set_mute(False); self.player.set_pause(False)
    def open_folder(self):
        if self.path:
            try: os.startfile(str(Path(self.path).parent))
            except OSError: self.say('Could not open clip folder.')
    def close_player(self):
        if self.job: self.screen.after_cancel(self.job); self.job=None
        if self.player: self.player.close_player(); self.player=None
    def close(self): self.close_player()
