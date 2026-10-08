"""Stone, tarnished silver and gold styling inspired by the game lobby."""
import tkinter as tk
from tkinter import ttk
from PIL import Image,ImageOps,ImageTk

BG='#0b0b0a'
PANEL='#484138'
EDGE='#8b8275'
TEXT='#e1dacb'
MUTED='#c0b8aa'
GOLD='#e6d58a'

class StoneFrame(tk.Frame):
    """Static decorative border; redraw only when the panel changes size."""
    def __init__(self,parent,**kwargs):
        kwargs.pop('highlightbackground',None); kwargs.pop('highlightthickness',None)
        super().__init__(parent,**kwargs)
        self.stone=ImageOps.colorize(Image.effect_noise((420,420),18),black='#302b24',white='#665c4e')
        self.photo=None
        self.trim=tk.Canvas(self,bg=self.cget('bg'),highlightthickness=0,bd=0)
        self.trim.place(x=0,y=0,relwidth=1,relheight=1)
        self.tk.call('lower',self.trim._w)
        self.bind('<Configure>',self.draw_trim,add='+')
    def draw_trim(self,event):
        if event.widget is not self: return
        c=self.trim; c.delete('all'); w=event.width; h=event.height
        if self.cget('bg')==PANEL:
            self.photo=ImageTk.PhotoImage(self.stone.resize((max(1,w),max(1,h))))
            c.create_image(0,0,image=self.photo,anchor='nw')
        # Irregular, double-beveled silver frame with clipped corners.
        for inset,color,width in ((2,'#201e1a',5),(4,'#978e7f',2),(7,'#292723',2),(9,'#72695d',1)):
            d=10; i=inset
            points=(i+d,i,w-i-d,i,w-i,i+d,w-i,h-i-d,w-i-d,h-i,
                    i+d,h-i,i,h-i-d,i,i+d)
            c.create_polygon(*points,fill='',outline=color,width=width)
        for x,y in ((15,15),(w-15,15),(15,h-15),(w-15,h-15)):
            c.create_polygon(x,y-5,x+5,y,x,y+5,x-5,y,fill='#514b41',outline='#aca291')
        # Worn cuts in the exposed frame, fixed rather than animated.
        for x in range(35,max(35,w-25),67):
            c.create_line(x,7,x+6,9,fill='#151411')

def ornament(parent):
    c=tk.Canvas(parent,bg=parent.cget('bg'),height=20,highlightthickness=0)
    def draw(event):
        c.delete('all'); w=event.width; y=10
        c.create_line(10,y,w-10,y,fill=EDGE)
        for x in (20,w/2,w-20):
            c.create_polygon(x,y-4,x+4,y,x,y+4,x-4,y,fill=GOLD if x==w/2 else EDGE,outline='#302c25')
        c.create_arc(w/2-15,3,w/2+15,17,start=180,extent=180,outline=EDGE,style='arc')
    c.bind('<Configure>',draw)
    return c

def build_ui(app):
    root=app.root
    root.title('VaultVision • Dark and Darker')
    root.geometry('1480x850'); root.minsize(1240,760)
    root.configure(bg=BG)
    style=ttk.Style(root); style.theme_use('clam')
    style.configure('.',font=('Georgia',10),background=PANEL,foreground=TEXT)
    style.configure('TFrame',background=BG)
    style.configure('TCheckbutton',background=PANEL,foreground=TEXT,font=('Georgia',10))
    style.map('TCheckbutton',background=[('active',PANEL)],foreground=[('active',GOLD)])
    style.configure('Vertical.TScrollbar',background='#655c4e',troughcolor='#211f1b',bordercolor=EDGE,arrowcolor=TEXT)
    style.configure('TEntry',fieldbackground='#171613',foreground=TEXT,
                    bordercolor=EDGE,lightcolor=EDGE,darkcolor=EDGE,padding=9,
                    insertcolor=TEXT)
    style.map('TEntry',bordercolor=[('focus',GOLD)])
    style.configure('TButton',background='#302d28',foreground=TEXT,
                    bordercolor=EDGE,lightcolor=EDGE,darkcolor=EDGE,padding=(14,10))
    style.map('TButton',background=[('active','#51493c'),('disabled','#24221e')],
              foreground=[('disabled','#6e7074')])
    style.configure('Primary.TButton',background='#51452a',foreground='#fff0dd',
                    bordercolor=GOLD,padding=(20,12),font=('Segoe UI',11,'bold'))
    style.map('Primary.TButton',background=[('active','#6b5b35'),('disabled','#302b21')],
              foreground=[('disabled','#8e7d79')])
    def label(parent,text,color=TEXT,font=('Segoe UI',10),**kw):
        return tk.Label(parent,text=text,bg=parent.cget('bg'),fg=color,font=font,**kw)
    header=tk.Frame(root,bg=BG,padx=28,pady=18); header.pack(fill='x')
    brand=tk.Frame(header,bg=BG); brand.pack(side='left')
    label(brand,'◈  VaultVision  ◈',GOLD,('Georgia',25,'bold')).pack(anchor='w')
    label(brand,'Combat Archives  •  Dark and Darker',MUTED,('Segoe UI',9)).pack(anchor='w',pady=(6,0))
    app.status_label=label(header,'●  DISARMED',MUTED,('Segoe UI',10,'bold'))
    app.status_label.pack(side='right')
    ornament(root).pack(fill='x',padx=20)
    body=tk.Frame(root,bg=BG,padx=28,pady=22); body.pack(fill='both',expand=True)
    body.columnconfigure(0,weight=0); body.columnconfigure(1,weight=1); body.columnconfigure(2,weight=3, minsize=470)
    body.rowconfigure(0,weight=1)
    left=StoneFrame(body,bg=PANEL,highlightbackground=EDGE,highlightthickness=1,padx=22,pady=22)
    left.grid(row=0,column=0,sticky='ns',padx=(0,18))
    label(left,'◆  Expedition  ◆',GOLD,('Segoe UI',10,'bold')).pack(anchor='w')
    label(left,'Ready for the dungeon',TEXT,('Georgia',17)).pack(anchor='w',pady=(10,8))
    label(left,'Arms when your gameplay HUD\nis confirmed. Pauses while\nspectating or outside a match.',MUTED,justify='left').pack(anchor='w',pady=(0,20))
    app.character_label=label(left,'Character: automatic',TEXT,wraplength=240,justify='left')
    app.character_label.pack(anchor='w',pady=(0,20))
    app.start_button=ttk.Button(left,text='Start auto detection',style='Primary.TButton',command=app.start)
    app.start_button.pack(fill='x')
    ttk.Button(left,text='Pause auto detection',command=app.stop.set).pack(fill='x',pady=8)
    ttk.Button(left,text='Save replay now',command=app.manual.set).pack(fill='x')
    tk.Frame(left,bg=EDGE,height=1).pack(fill='x',pady=24)
    label(left,'Replay Buffer',GOLD,('Segoe UI',9,'bold')).pack(anchor='w')
    app.replay_label=label(left,'Checking OBS duration…',TEXT,('Segoe UI',12))
    app.replay_label.pack(anchor='w',pady=(7,6))
    label(left,'OBS controls clip duration\nand the output folder.',MUTED,justify='left').pack(anchor='w')
    label(left,'Screen recognition • Local OCR',MUTED,('Segoe UI',9)).pack(side='bottom',anchor='w',pady=(24,0))
    right=tk.Frame(body,bg=BG); right.grid(row=0,column=1,sticky='nsew')
    settings=StoneFrame(right,bg=PANEL,highlightbackground=EDGE,highlightthickness=1,padx=20,pady=18)
    settings.pack(fill='x')
    label(settings,'◆  Capture Settings  ◆',GOLD,('Segoe UI',10,'bold')).grid(row=0,columnspan=2,sticky='w',pady=(0,12))
    settings.columnconfigure(1,weight=1)
    app.entries=[]
    fields=[('Capture method (screen / obs)',app.capture_method),('Screen monitor',app.monitor),('OBS source',app.source),('WebSocket password',app.password),
            ('Character override',app.name),('Save delay (seconds)',app.after),('HUD absence timeout (seconds)',app.hud_timeout),
            ('Tesseract executable',app.tesseract)]
    for row,(title,var) in enumerate(fields,1):
        label(settings,title,MUTED).grid(row=row,column=0,sticky='w',padx=(0,16),pady=6)
        entry=ttk.Entry(settings,textvariable=var,show='●' if var is app.password else '')
        entry.grid(row=row,column=1,sticky='ew',pady=6)
        app.entries.append(entry)
    ttk.Checkbutton(settings,text='Capture deaths',variable=app.capture_deaths).grid(
        row=len(fields)+1,columnspan=2,sticky='w',pady=(8,0))
    actions=tk.Frame(settings,bg=PANEL); actions.grid(row=len(fields)+2,columnspan=2,sticky='e',pady=(10,0))
    ttk.Button(actions,text='Save password',command=app.store_password).pack(side='left',padx=(0,8))
    ttk.Button(actions,text='Open password file',command=app.open_password_file).pack(side='left')
    activity=StoneFrame(right,bg=BG,highlightbackground=EDGE,highlightthickness=1,padx=20,pady=16)
    activity.pack(fill='both',expand=True,pady=(16,0))
    label(activity,'◆  Chronicle  ◆',GOLD,('Segoe UI',10,'bold')).pack(anchor='w',pady=(0,12))
    logs=tk.Frame(activity,bg=BG); logs.pack(fill='both',expand=True)
    app.log=tk.Text(logs,height=8,width=48,state='disabled',bg='#101216',fg=TEXT,
                    font=('Consolas',10),relief='flat',borderwidth=0,padx=12,pady=12,
                    selectbackground='#4c4030',wrap='word')
    scroll=ttk.Scrollbar(logs,command=app.log.yview)
    app.log.configure(yscrollcommand=scroll.set)
    scroll.pack(side='right',fill='y'); app.log.pack(side='left',fill='both',expand=True)
    app.log.tag_configure('kill',foreground='#d7be7d')
    app.log.tag_configure('error',foreground='#ed9382')
    from clip_gallery import ClipGallery
    clips=StoneFrame(body,bg=PANEL,highlightbackground=EDGE,highlightthickness=1,padx=10,pady=10)
    clips.grid(row=0,column=2,sticky='nsew',padx=(18,0))
    app.gallery=ClipGallery(clips,app.say)
    footer=tk.Frame(root,bg=BG,padx=28,pady=12); footer.pack(fill='x')
    label(footer,'VaultVision  •  Combat Archives',MUTED,('Segoe UI',9)).pack(side='left')
    label(footer,'1080p • OBS replay capture',MUTED,('Segoe UI',9)).pack(side='right')
