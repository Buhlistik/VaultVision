"""Modern clip browser; decoder lifecycle never runs on the Tk thread."""
import json,os,queue,math
from collections import OrderedDict
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,simpledialog,messagebox
from PIL import ImageTk,ImageOps
from local_settings import password_path
from preview_engine import PreviewEngine

BG='#171a1f'; INK='#e7dfcd'; MUTED='#92979f'; GOLD='#c7a96b'
def clock(seconds):
    value=max(0,int(seconds or 0)) if math.isfinite(float(seconds or 0)) else 0; return f'{value//60}:{value%60:02d}'

class ClipGallery:
    def __init__(self,parent,say):
        self.say=say; self.path=None; self.photo=None; self.image=None
        self.decoder_width=640; self.resize_job=None
        self.fullscreen_window=None; self.full_screen=None; self.full_timeline=None; self.full_photo=None
        self.duration=0; self.position=0; self.paused=True; self.muted=False; self.volume=tk.DoubleVar(value=.7)
        self.scrubbing=False; self.scrub_position=0.; self.token=0; self.cache=OrderedDict(); self.closing=False
        self.engine=PreviewEngine()
        self.index=password_path().parent/'clips.json'
        try:
            records=json.loads(self.index.read_text(encoding='utf-8'))
            self.records=[r for r in records if isinstance(r,dict) and isinstance(r.get('path'),str) and Path(r['path']).is_file()] if isinstance(records,list) else []
        except (OSError,ValueError): self.records=[]
        outer=tk.Frame(parent,bg=BG,padx=18,pady=18); outer.pack(fill='both',expand=True)
        header=tk.Frame(outer,bg=BG); header.pack(fill='x')
        tk.Label(header,text='Clip vault',bg=BG,fg=INK,font=('Segoe UI',16,'bold')).pack(side='left')
        self.count=tk.Label(header,bg=BG,fg=MUTED,font=('Segoe UI',10)); self.count.pack(side='right')
        self.title=tk.Label(outer,text='Select a replay to preview',bg=BG,fg=MUTED,font=('Segoe UI',10),anchor='w',width=1)
        self.title.pack(fill='x',pady=(5,16))
        workspace=tk.Frame(outer,bg=BG); workspace.pack(fill='both',expand=True)
        library=tk.Frame(workspace,bg='#13161b',width=250,padx=12,pady=12)
        library.pack(side='right',fill='y',padx=(14,0)); library.pack_propagate(False)
        player_area=tk.Frame(workspace,bg=BG); player_area.pack(side='left',fill='both',expand=True)
        self.viewport=tk.Frame(player_area,bg='#080a0d',height=240,highlightbackground='#30343b',highlightthickness=1); self.viewport.pack(fill='both',expand=True)
        self.viewport.pack_propagate(False)
        self.screen=tk.Label(self.viewport,bd=0,padx=0,pady=0,text='Your next highlight belongs here\n\nSaved replays appear below. You can also import a video.',bg='#080a0d',fg=MUTED,font=('Segoe UI',12))
        self.screen.pack(fill='both',expand=True); self.screen.bind('<Configure>',self.resize)
        self.screen.bind('<Button-1>',lambda e:self.toggle())
        self.screen.bind('<Double-Button-1>',lambda e:self.toggle_fullscreen())
        self.timeline=tk.Canvas(player_area,height=20,bg=BG,highlightthickness=0,cursor='hand2')
        self.timeline.pack(fill='x',pady=(8,0)); self.timeline.bind('<Configure>',lambda e:self.draw_progress())
        self.timeline.bind('<Button-1>',self.scrub_at)
        self.timeline.bind('<B1-Motion>',self.scrub_at)
        self.timeline.bind('<ButtonRelease-1>',self.seek_at)
        bar=tk.Frame(player_area,bg=BG); bar.pack(fill='x',pady=(0,14))
        def button(text,command):
            b=tk.Button(bar,text=text,command=command,bg='#252931',fg=INK,
                        activebackground='#373b44',activeforeground=INK,relief='flat',
                        bd=0,padx=12,pady=7,cursor='hand2',font=('Segoe UI',10))
            b.pack(side='left',padx=(0,6)); return b
        self.play=button('▶  Play',self.toggle); self.play.configure(state='disabled')
        button('↺',self.restart); self.mute_button=button('Mute',self.mute)
        self.fullscreen_button=button('Fullscreen',self.toggle_fullscreen); self.fullscreen_button.configure(state='disabled')
        self.volume_slider=tk.Scale(bar,from_=0,to=1,resolution=.05,orient='horizontal',
                    variable=self.volume,command=self.change_volume,length=70,
                    showvalue=False,bg=BG,troughcolor='#34383f',highlightthickness=0,
                    activebackground=GOLD,bd=0,sliderlength=10)
        self.volume_slider.pack(side='left',padx=5)
        self.time=tk.Label(bar,text='0:00 / 0:00',bg=BG,fg=MUTED,font=('Segoe UI',10)); self.time.pack(side='right')
        tools=tk.Frame(library,bg='#13161b'); tools.pack(fill='x',pady=(0,10))
        tk.Label(tools,text='SAVED CLIPS',bg='#13161b',fg=GOLD,font=('Segoe UI',9,'bold')).pack(anchor='w',pady=(0,10))
        tool_actions=tk.Frame(tools,bg='#13161b'); tool_actions.pack(fill='x')
        tk.Button(tool_actions,text='Import',command=self.import_clips,bg=BG,fg=INK,
                  activebackground=BG,activeforeground=GOLD,bd=0,cursor='hand2').pack(side='right')
        tk.Button(tool_actions,text='Folder',command=self.open_folder,bg=BG,fg=MUTED,
                  activebackground=BG,activeforeground=GOLD,bd=0,cursor='hand2').pack(side='right',padx=10)
        self.rename_button=tk.Button(tool_actions,text='Rename',command=self.rename_clip,bg=BG,fg=INK,
                  activebackground=BG,activeforeground=GOLD,bd=0,cursor='hand2',state='disabled')
        self.rename_button.pack(side='right',padx=8)
        style=ttk.Style(parent)
        style.configure('Clips.Treeview',background='#13161b',fieldbackground='#13161b',foreground=INK,
                        rowheight=38,borderwidth=0,font=('Segoe UI',10))
        style.map('Clips.Treeview',background=[('selected','#34312b')],foreground=[('selected','#f2e3c5')])
        listing=tk.Frame(library,bg='#13161b'); listing.pack(fill='both',expand=True)
        self.list=ttk.Treeview(listing,show='tree',height=4,selectmode='browse',style='Clips.Treeview')
        self.list.column('#0',width=200,stretch=True)
        self.list.tag_configure('even',background='#13161b')
        self.list.tag_configure('odd',background='#191d23')
        scroll=ttk.Scrollbar(listing,command=self.list.yview); self.list.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y'); self.list.pack(side='left',fill='both',expand=True)
        self.list.bind('<<TreeviewSelect>>',self.select); self.refresh()
        self.job=self.screen.after(30,self.poll)
    def restore_preferences(self,settings):
        value=settings.get('volume',.7)
        if isinstance(value,(int,float)) and math.isfinite(value): self.volume.set(max(0,min(1,value)))
        self.muted=bool(settings.get('muted',False))
        self.mute_button.configure(text='Unmute' if self.muted else 'Mute')
        self.engine.command('volume',self.volume.get()); self.engine.command('mute',self.muted)
    def change_volume(self,value):
        self.engine.command('volume',float(value))
    def refresh(self):
        self.list.delete(*self.list.get_children())
        for i,record in enumerate(self.records):
            label=record.get('label','Replay')
            self.list.insert('', 'end',iid=str(i),text='  '+label+'  ·  '+(record.get('title') or Path(record['path']).stem),tags=('even' if i%2==0 else 'odd',))
            if record['path']==self.path: self.list.selection_set(str(i))
        self.count.configure(text=f'{len(self.records)} clips')
    def add(self,path,label='Replay'):
        path=str(Path(path))
        if not Path(path).is_file() or any(r['path']==path for r in self.records): return
        self.records.insert(0,{'path':path,'label':label}); self.refresh()
        self.persist_records()
        self.say('Saved clip: '+Path(path).name)
    def persist_records(self):
        try:
            self.index.parent.mkdir(parents=True,exist_ok=True)
            temporary=self.index.with_suffix('.tmp')
            temporary.write_text(json.dumps(self.records,indent=2),encoding='utf-8')
            temporary.replace(self.index)
            return True
        except OSError:
            self.say('Could not persist clip history.'); return False
    def set_clip_title(self,index,title):
        title=title.strip()
        if not title or len(title)>120 or any(ord(ch)<32 for ch in title):
            raise ValueError('Use a name from 1 to 120 characters without line breaks.')
        record=self.records[index]; previous=record.get('title')
        record['title']=title
        if not self.persist_records():
            if previous is None: record.pop('title',None)
            else: record['title']=previous
            return False
        self.refresh()
        if record['path']==getattr(self,'path',None): self.title.configure(text=title)
        return True
    def rename_clip(self):
        selected=self.list.selection()
        if not selected: return
        index=int(selected[0]); record=self.records[index]
        title=simpledialog.askstring('Rename clip','Display name:',initialvalue=record.get('title') or Path(record['path']).stem,
                                     parent=self.screen.winfo_toplevel())
        if title is None: return
        try:
            if not self.set_clip_title(index,title):
                messagebox.showerror('Rename clip','Could not save the new name.',parent=self.screen.winfo_toplevel())
        except ValueError as exc:
            messagebox.showerror('Rename clip',str(exc),parent=self.screen.winfo_toplevel())
    def toggle_fullscreen(self):
        if self.fullscreen_window is not None:
            self.exit_fullscreen(); return
        if not self.path: return
        window=tk.Toplevel(self.screen); self.fullscreen_window=window
        window.configure(bg='#080a0d'); window.attributes('-fullscreen',True)
        window.protocol('WM_DELETE_WINDOW',self.exit_fullscreen)
        window.bind('<Escape>',lambda event:self.exit_fullscreen())
        window.bind('<space>',lambda event:self.toggle())
        window.bind('<Left>',lambda event:self.skip(-5))
        window.bind('<Right>',lambda event:self.skip(5))
        controls=tk.Frame(window,bg=BG,padx=18,pady=10); controls.place(relx=0,rely=1,anchor='sw',relwidth=1,height=50)
        self.full_play=tk.Button(controls,text='Play',command=self.toggle,bg='#252931',fg=INK,bd=0,padx=18,pady=8)
        self.full_play.pack(side='left')
        tk.Button(controls,text='Exit fullscreen · Esc',command=self.exit_fullscreen,bg=BG,fg=INK,bd=0,padx=18,pady=8).pack(side='right')
        self.full_time=tk.Label(controls,text=clock(self.position)+' / '+clock(self.duration),bg=BG,fg=MUTED)
        self.full_time.pack(side='right',padx=16)
        self.full_timeline=tk.Canvas(window,height=24,bg=BG,highlightthickness=0,cursor='hand2')
        self.full_timeline.place(relx=0,rely=1,anchor='sw',relwidth=1,y=-50,height=24)
        self.full_timeline.bind('<Configure>',lambda event:self.draw_progress())
        self.full_timeline.bind('<Button-1>',self.scrub_at)
        self.full_timeline.bind('<B1-Motion>',self.scrub_at)
        self.full_timeline.bind('<ButtonRelease-1>',self.seek_at)
        self.full_screen=tk.Label(window,bd=0,padx=0,pady=0,bg='#080a0d',fg=MUTED,text='Loading preview…')
        self.full_screen.pack(fill='both',expand=True)
        self.full_screen.bind('<Configure>',self.resize)
        self.full_screen.bind('<Button-1>',lambda event:self.toggle())
        self.full_screen.bind('<Double-Button-1>',lambda event:self.exit_fullscreen())
        controls.lift(); self.full_timeline.lift()
        window.focus_set(); self.resize(); self.draw_progress()
    def exit_fullscreen(self):
        window=self.fullscreen_window
        self.fullscreen_window=None; self.full_screen=None; self.full_timeline=None; self.full_photo=None
        if window is not None: window.destroy()
        if not self.closing: self.resize()
    def skip(self,seconds):
        if self.path and self.duration:
            self.position=max(0,min(self.duration,self.position+seconds))
            self.engine.command('seek',self.position); self.draw_progress()
    def import_clips(self):
        for path in filedialog.askopenfilenames(filetypes=[('Video files','*.mp4 *.mkv *.mov *.flv *.ts'),('All files','*.*')]): self.add(path,'Imported')
    def select(self,event=None):
        choice=self.list.selection()
        if not choice: return
        record=self.records[int(choice[0])]
        if record['path']==self.path: return
        self.path=record['path']; self.title.configure(text=record.get('title') or Path(self.path).name)
        self.rename_button.configure(state='normal'); self.fullscreen_button.configure(state='normal')
        self.duration=0; self.position=0; self.paused=True
        self.play.configure(text='▶  Play',state='disabled'); self.time.configure(text='Loading…')
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
                    if self.full_screen is not None: self.full_screen.configure(image='',text='Unable to preview this clip')
                    self.play.configure(state='disabled')
                    self.say('Preview error: '+data); continue
                image,self.position,self.duration,self.paused=data
                if image:
                    self.image=image
                    if self.path not in self.cache:
                        self.cache[self.path]=image.copy()
                        while len(self.cache)>6: self.cache.popitem(last=False)
                    self.render()
                self.play.configure(text='▶  Play' if self.paused else 'Ⅱ  Pause',state='normal')
                if not self.scrubbing: self.time.configure(text=clock(self.position)+' / '+clock(self.duration))
                if self.fullscreen_window is not None:
                    self.full_play.configure(text='Play' if self.paused else 'Pause')
                    if not self.scrubbing: self.full_time.configure(text=clock(self.position)+' / '+clock(self.duration))
                self.draw_progress()
        except queue.Empty: pass
        except Exception as exc:
            self.say('Preview display error: '+str(exc))
        self.job=self.screen.after(30,self.poll)
    def render(self):
        if self.image is None: return
        # One image conversion per frame: fullscreen shares the existing decoder.
        target=self.full_screen if self.full_screen is not None else self.screen
        image=ImageOps.contain(self.image,(max(1,target.winfo_width()),max(1,target.winfo_height())))
        photo=ImageTk.PhotoImage(image)
        if self.full_screen is not None: self.full_photo=photo
        else: self.photo=photo
        target.configure(image=photo,text='')
    def resize(self,event=None):
        if self.image is not None: self.render()
        if self.resize_job is not None: self.screen.after_cancel(self.resize_job)
        self.resize_job=self.screen.after(150,self.update_decoder_size)
    def update_decoder_size(self):
        self.resize_job=None
        if self.closing: return
        target=self.full_screen if self.full_screen is not None else self.screen
        width=max(320,min(3840,target.winfo_width()))
        if abs(width-self.decoder_width)>=32:
            self.decoder_width=width; self.engine.command('size',width)
    def draw_progress(self):
        for canvas in (self.timeline,getattr(self,'full_timeline',None)):
            if canvas is None: continue
            canvas.delete('all'); width=max(1,canvas.winfo_width())
            canvas.create_line(0,10,width,10,fill='#34383f',width=3)
            x=width*min(1,(self.scrub_position if self.scrubbing else self.position)/self.duration) if self.duration else 0
            canvas.create_line(0,10,x,10,fill=GOLD,width=3)
            canvas.create_oval(x-4,6,x+4,14,fill=GOLD,outline='')
    def scrub_at(self,event):
        if not self.duration: return
        self.scrubbing=True
        self.scrub_position=max(0,min(1,event.x/max(1,getattr(event,'widget',self.timeline).winfo_width())))*self.duration
        self.time.configure(text=clock(self.scrub_position)+' / '+clock(self.duration))
        self.draw_progress()
    def seek_at(self,event):
        self.scrubbing=False
        if self.duration:
            self.position=max(0,min(1,event.x/max(1,getattr(event,'widget',self.timeline).winfo_width())))*self.duration
            self.draw_progress()
            self.engine.command('seek',self.position)
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
        if self.fullscreen_window is not None: self.exit_fullscreen()
        if self.resize_job is not None: self.screen.after_cancel(self.resize_job)
        if self.job: self.screen.after_cancel(self.job)
        self.engine.close()
