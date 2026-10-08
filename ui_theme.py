"""Dark fantasy desktop styling, with no image assets or animation overhead."""
import tkinter as tk
from tkinter import ttk

BG='#0d0f12'
PANEL='#171a1f'
EDGE='#35312a'
TEXT='#e7dfcd'
MUTED='#aca79b'
GOLD='#c7a96b'

def build_ui(app):
    root=app.root
    root.title('VaultVision • Dark and Darker')
    root.geometry('1480x850'); root.minsize(1240,760)
    root.configure(bg=BG)
    style=ttk.Style(root); style.theme_use('clam')
    style.configure('.',font=('Segoe UI',10),background=PANEL,foreground=TEXT)
    style.configure('TFrame',background=BG)
    style.configure('TEntry',fieldbackground='#101216',foreground=TEXT,
                    bordercolor=EDGE,lightcolor=EDGE,darkcolor=EDGE,padding=9,
                    insertcolor=TEXT)
    style.map('TEntry',bordercolor=[('focus',GOLD)])
    style.configure('TButton',background='#282b30',foreground=TEXT,
                    bordercolor=EDGE,lightcolor=EDGE,darkcolor=EDGE,padding=(14,10))
    style.map('TButton',background=[('active','#3a3b3d'),('disabled','#191b20')],
              foreground=[('disabled','#6e7074')])
    style.configure('Primary.TButton',background='#783c37',foreground='#fff0dd',
                    bordercolor='#a15b4e',padding=(20,12),font=('Segoe UI',11,'bold'))
    style.map('Primary.TButton',background=[('active','#984e44'),('disabled','#392b2c')],
              foreground=[('disabled','#8e7d79')])
    def label(parent,text,color=TEXT,font=('Segoe UI',10),**kw):
        return tk.Label(parent,text=text,bg=parent.cget('bg'),fg=color,font=font,**kw)
    header=tk.Frame(root,bg=BG,padx=28,pady=24); header.pack(fill='x')
    brand=tk.Frame(header,bg=BG); brand.pack(side='left')
    label(brand,'V A U L T V I S I O N',GOLD,('Georgia',25,'bold')).pack(anchor='w')
    label(brand,'DARK AND DARKER  /  AUTOMATIC COMBAT CLIPS',MUTED,('Segoe UI',9)).pack(anchor='w',pady=(6,0))
    app.status_label=label(header,'●  DISARMED',MUTED,('Segoe UI',10,'bold'))
    app.status_label.pack(side='right')
    tk.Frame(root,bg=EDGE,height=1).pack(fill='x',padx=28)
    body=tk.Frame(root,bg=BG,padx=28,pady=22); body.pack(fill='both',expand=True)
    body.columnconfigure(0,weight=0); body.columnconfigure(1,weight=1); body.columnconfigure(2,weight=3, minsize=470)
    body.rowconfigure(0,weight=1)
    left=tk.Frame(body,bg=PANEL,highlightbackground=EDGE,highlightthickness=1,padx=22,pady=22)
    left.grid(row=0,column=0,sticky='ns',padx=(0,18))
    label(left,'SESSION',GOLD,('Segoe UI',10,'bold')).pack(anchor='w')
    label(left,'Ready for the dungeon',TEXT,('Georgia',17)).pack(anchor='w',pady=(10,8))
    label(left,'Arms when your gameplay HUD\nis confirmed. Pauses while\nspectating or outside a match.',MUTED,justify='left').pack(anchor='w',pady=(0,20))
    app.character_label=label(left,'Character: automatic',TEXT,wraplength=240,justify='left')
    app.character_label.pack(anchor='w',pady=(0,20))
    app.start_button=ttk.Button(left,text='Start auto detection',style='Primary.TButton',command=app.start)
    app.start_button.pack(fill='x')
    ttk.Button(left,text='Pause auto detection',command=app.stop.set).pack(fill='x',pady=8)
    ttk.Button(left,text='Save replay now',command=app.manual.set).pack(fill='x')
    tk.Frame(left,bg=EDGE,height=1).pack(fill='x',pady=24)
    label(left,'REPLAY BUFFER',GOLD,('Segoe UI',9,'bold')).pack(anchor='w')
    app.replay_label=label(left,'Checking OBS duration…',TEXT,('Segoe UI',12))
    app.replay_label.pack(anchor='w',pady=(7,6))
    label(left,'OBS controls clip duration\nand the output folder.',MUTED,justify='left').pack(anchor='w')
    label(left,'Screen recognition • Local OCR',MUTED,('Segoe UI',9)).pack(side='bottom',anchor='w',pady=(24,0))
    right=tk.Frame(body,bg=BG); right.grid(row=0,column=1,sticky='nsew')
    settings=tk.Frame(right,bg=PANEL,highlightbackground=EDGE,highlightthickness=1,padx=20,pady=18)
    settings.pack(fill='x')
    label(settings,'CAPTURE SETTINGS',GOLD,('Segoe UI',10,'bold')).grid(row=0,columnspan=2,sticky='w',pady=(0,12))
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
    actions=tk.Frame(settings,bg=PANEL); actions.grid(row=len(fields)+1,columnspan=2,sticky='e',pady=(10,0))
    ttk.Button(actions,text='Save password',command=app.store_password).pack(side='left',padx=(0,8))
    ttk.Button(actions,text='Open password file',command=app.open_password_file).pack(side='left')
    activity=tk.Frame(right,bg=PANEL,highlightbackground=EDGE,highlightthickness=1,padx=20,pady=16)
    activity.pack(fill='both',expand=True,pady=(16,0))
    label(activity,'ACTIVITY',GOLD,('Segoe UI',10,'bold')).pack(anchor='w',pady=(0,12))
    logs=tk.Frame(activity,bg=PANEL); logs.pack(fill='both',expand=True)
    app.log=tk.Text(logs,height=8,width=48,state='disabled',bg='#101216',fg=TEXT,
                    font=('Consolas',10),relief='flat',borderwidth=0,padx=12,pady=12,
                    selectbackground='#4c4030',wrap='word')
    scroll=ttk.Scrollbar(logs,command=app.log.yview)
    app.log.configure(yscrollcommand=scroll.set)
    scroll.pack(side='right',fill='y'); app.log.pack(side='left',fill='both',expand=True)
    app.log.tag_configure('kill',foreground='#d7be7d')
    app.log.tag_configure('error',foreground='#ed9382')
    from clip_gallery import ClipGallery
    clips=tk.Frame(body,bg=PANEL,highlightbackground=EDGE,highlightthickness=1)
    clips.grid(row=0,column=2,sticky='nsew',padx=(18,0))
    app.gallery=ClipGallery(clips,app.say)
    footer=tk.Frame(root,bg=BG,padx=28,pady=12); footer.pack(fill='x')
    label(footer,'VAULTVISION  /  PROTOTYPE',MUTED,('Segoe UI',9)).pack(side='left')
    label(footer,'1080p • OBS replay capture',MUTED,('Segoe UI',9)).pack(side='right')
