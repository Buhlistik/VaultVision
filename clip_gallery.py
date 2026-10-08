"""Modern clip browser; decoder lifecycle never runs on the Tk thread."""
import json,os,queue
from collections import OrderedDict
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog
from PIL import ImageTk
from local_settings import password_path
from preview_engine import PreviewEngine

BG='#171a1f'; INK='#e7dfcd'; MUTED='#92979f'; GOLD='#c7a96b'
def clock(seconds):
    value=max(0,int(seconds or 0)); return f'{value//60}:{value%60:02d}'

class ClipGallery:
    def __init__(self,parent,say):
        self.say=say; self.path=None; self.photo=None; self.image=None
        self.duration=0; self.position=0; self.paused=True; self.muted=False
        self.token=0; self.cache=OrderedDict(); self.closing=False
        self.engine=PreviewEngine()
        self.index=password_path().parent/'clips.json'
        try:
            records=json.loads(self.index.read_text(encoding='utf-8'))
            self.records=[r for r in records if isinstance(r,dict) and isinstance(r.get('path'),str) and Path(r['path']).is_file()] if isinstance(records,list) else []
        except (OSError,ValueError): self.records=[]
        outer=tk.Frame(parent,bg=BG,padx=18,pady=18); outer.pack(fill='both',expand=True)
        header=tk.Frame(outer,bg=BG); header.pack(fill='x')
        tk.Label(header,text='CLIP VAULT',bg=BG,fg=INK,font=('Segoe UI',14,'bold')).pack(side='left')
        self.count=tk.Label(header,bg=BG,fg=MUTED,font=('Segoe UI',10)); self.count.pack(side='right')
        self.title=tk.Label(outer,text='Your combat highlights',bg=BG,fg=MUTED,font=('Segoe UI',10),anchor='w')
        self.title.pack(fill='x',pady=(5,16))
        self.viewport=tk.Frame(outer,bg='#080a0d',height=300); self.viewport.pack(fill='both',expand=True)
        self.viewport.pack_propagate(False)
        self.screen=tk.Label(self.viewport,text='Select a clip below',bg='#080a0d',fg=MUTED,font=('Segoe UI',12))
        self.screen.pack(fill='both',expand=True); self.screen.bind('<Configure>',self.resize)
        self.screen.bind('<Button-1>',lambda e:self.toggle())
        self.timeline=tk.Canvas(outer,height=20,bg=BG,highlightthickness=0,cursor='hand2')
        self.timeline.pack(fill='x',pady=(8,0)); self.timeline.bind('<Configure>',lambda e:self.draw_progress())
        self.timeline.bind('<Button-1>',self.seek_at); self.timeline.bind('<ButtonRelease-1>',self.seek_at)
        bar=tk.Frame(outer,bg=BG); bar.pack(fill='x',pady=(0,14))
        def button(text,command):
            b=tk.Button(bar,text=text,command=command,bg='#252931',fg=INK,
                        activebackground='#373b44',activeforeground=INK,relief='flat',
                        bd=0,padx=12,pady=7,cursor='hand2',font=('Segoe UI',10))
            b.pack(side='left',padx=(0,6)); return b
        self.play=button('▶  Play',self.toggle)
        button('↺',self.restart); self.mute_button=button('Mute',self.mute)
        self.time=tk.Label(bar,text='0:00 / 0:00',bg=BG,fg=MUTED,font=('Segoe UI',10)); self.time.pack(side='right')
        tools=tk.Frame(outer,bg=BG); tools.pack(fill='x',pady=(6,8))
        tk.Label(tools,text='RECENT CLIPS',bg=BG,fg=GOLD,font=('Segoe UI',9,'bold')).pack(side='left')
        tk.Button(tools,text='+ Import',command=self.import_clips,bg=BG,fg=INK,
                  activebackground=BG,activeforeground=GOLD,bd=0,cursor='hand2').pack(side='right')
        tk.Button(tools,text='Open folder',command=self.open_folder,bg=BG,fg=MUTED,
                  activebackground=BG,activeforeground=GOLD,bd=0,cursor='hand2').pack(side='right',padx=10)
        style=ttk.Style(parent)
        style.configure('Clips.Treeview',background='#13161b',fieldbackground='#13161b',foreground=INK,
                        rowheight=38,borderwidth=0,font=('Segoe UI',10))
        style.map('Clips.Treeview',background=[('selected','#34312b')],foreground=[('selected','#f2e3c5')])
        listing=tk.Frame(outer,bg=BG); listing.pack(fill='x')
        self.list=ttk.Treeview(listing,show='tree',height=5,selectmode='browse',style='Clips.Treeview')
        self.list.column('#0',width=300,stretch=True)
        scroll=ttk.Scrollbar(listing,command=self.list.yview); self.list.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y'); self.list.pack(side='left',fill='x',expand=True)
        self.list.bind('<<TreeviewSelect>>',self.select); self.refresh()
        self.job=self.screen.after(30,self.poll)
    def refresh(self):
        self.list.delete(*self.list.get_children())
        for i,record in enumerate(self.records):
            label=record.get('label','Replay')
            self.list.insert('', 'end',iid=str(i),text='  '+label+'  ·  '+Path(record['path']).stem)
            if record['path']==self.path: self.list.selection_set(str(i))
        self.count.configure(text=f'{len(self.records)} clips')
    def add(self,path,label='Replay'):
        path=str(Path(path))
        if not Path(path).is_file() or any(r['path']==path for r in self.records): return
        self.records.insert(0,{'path':path,'label':label}); self.refresh()
        try:
            self.index.parent.mkdir(parents=True,exist_ok=True)
            temporary=self.index.with_suffix('.tmp'); temporary.write_text(json.dumps(self.records,indent=2),encoding='utf-8'); temporary.replace(self.index)
        except OSError: self.say('Could not persist clip history.')
        self.say('Saved clip: '+Path(path).name)
    def import_clips(self):
        for path in filedialog.askopenfilenames(filetypes=[('Video files','*.mp4 *.mkv *.mov *.flv *.ts'),('All files','*.*')]): self.add(path,'Imported')
    def select(self,event=None):
        choice=self.list.selection()
        if not choice: return
        record=self.records[int(choice[0])]
        if record['path']==self.path: return
        self.path=record['path']; self.title.configure(text=Path(self.path).name)
        self.duration=0; self.position=0; self.paused=True
        self.play.configure(text='▶  Play'); self.time.configure(text='Loading…')
        self.image=self.cache.get(self.path)
        if self.image: self.render()
        else: self.photo=None; self.screen.configure(image='',text='Loading preview…')
        self.token=self.engine.open(self.path); self.draw_progress()
    def poll(self):
        if self.closing: return
        try:
            while True:
                token,kind,data=self.engine.frames.get_nowait()
                if token!=self.token: continue
                if kind=='error':
                    self.screen.configure(image='',text='Unable to preview this clip')
                    self.say('Preview error: '+data); continue
                image,self.position,self.duration,self.paused=data
                if image:
                    self.image=image
                    if self.path not in self.cache:
                        self.cache[self.path]=image.copy()
                        while len(self.cache)>6: self.cache.popitem(last=False)
                    self.render()
                self.play.configure(text='▶  Play' if self.paused else 'Ⅱ  Pause')
                self.time.configure(text=clock(self.position)+' / '+clock(self.duration))
                self.draw_progress()
        except queue.Empty: pass
        self.job=self.screen.after(30,self.poll)
    def render(self):
        if self.image is None: return
        image=self.image.copy()
        image.thumbnail((max(1,self.screen.winfo_width()),max(1,self.screen.winfo_height())))
        self.photo=ImageTk.PhotoImage(image); self.screen.configure(image=self.photo,text='')
    def resize(self,event=None):
        if self.image is not None: self.render()
    def draw_progress(self):
        canvas=self.timeline; canvas.delete('all'); width=max(1,canvas.winfo_width())
        canvas.create_line(0,10,width,10,fill='#34383f',width=3)
        x=width*min(1,self.position/self.duration) if self.duration else 0
        canvas.create_line(0,10,x,10,fill=GOLD,width=3)
        canvas.create_oval(x-4,6,x+4,14,fill=GOLD,outline='')
    def seek_at(self,event):
        if self.duration:
            self.engine.command('seek',max(0,min(1,event.x/max(1,self.timeline.winfo_width())))*self.duration)
    def toggle(self):
        if self.path: self.engine.command('toggle')
    def restart(self):
        if self.path: self.engine.command('restart')
    def mute(self):
        self.muted=not self.muted; self.mute_button.configure(text='Unmute' if self.muted else 'Mute')
        self.engine.command('mute',self.muted)
    def open_folder(self):
        if self.path:
            try: os.startfile(str(Path(self.path).parent))
            except OSError: self.say('Could not open clip folder.')
    def close(self):
        self.closing=True
        if self.job: self.screen.after_cancel(self.job)
        self.engine.close()
