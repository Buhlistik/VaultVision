"""Charcoal and gold interface with supplied game artwork."""
import tkinter as tk
from tkinter import ttk
from pathlib import Path
import sys
from PIL import Image,ImageTk

BG='#0d0f12'
PANEL='#171a1f'
EDGE='#35312a'
TEXT='#e7dfcd'
MUTED='#aca79b'
GOLD='#c7a96b'

def build_ui(app):
    root=app.root
    root.title('VaultVision • Dark and Darker')
    root.geometry('1480x850'); root.minsize(1120,760)
    root.configure(bg=BG)
    app.artwork={}
    asset_dir=Path(__file__).resolve().parent/'assets'
    def artwork(name,size):
        try:
            with Image.open(asset_dir/name) as source:
                image=source.convert('RGBA')
                image.thumbnail(size,Image.Resampling.LANCZOS)
            photo=ImageTk.PhotoImage(image,master=root)
            app.artwork[name]=photo
            return photo
        except (OSError,ValueError) as exc:
            app.say('Could not load interface artwork '+name+': '+str(exc))
            return None
    icon=artwork('jokester.png',(256,256))
    if icon is not None: root.iconphoto(True,icon)
    if sys.platform=='win32' and (asset_dir/'jokester.ico').is_file():
        try: root.iconbitmap(str(asset_dir/'jokester.ico'))
        except tk.TclError: pass
    style=ttk.Style(root); style.theme_use('clam')
    style.configure('.',font=('Segoe UI',10),background=PANEL,foreground=TEXT)
    style.configure('TFrame',background=BG)
    style.configure('TCheckbutton',background=PANEL,foreground=TEXT,padding=(0,4))
    style.map('TCheckbutton',background=[('active',PANEL)],foreground=[('active',GOLD)])
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
    # Setup stays available in a reusable window; fields retain the same
    # variables and monitoring lock as the main application.
    settings_window=tk.Toplevel(root)
    settings_window.title('VaultVision — Settings')
    settings_window.configure(bg=BG)
    settings_window.geometry('680x540'); settings_window.minsize(640,520)
    settings_window.withdraw(); settings_window.transient(root)
    settings_window.protocol('WM_DELETE_WINDOW',settings_window.withdraw)
    settings_window.bind('<Escape>',lambda event:settings_window.withdraw())
    settings=tk.Frame(settings_window,bg=PANEL,padx=24,pady=22)
    settings.pack(fill='both',expand=True,padx=16,pady=16)
    label(settings,'Capture settings',TEXT,('Segoe UI',18,'bold')).grid(row=0,columnspan=2,sticky='w')
    label(settings,'Pause monitoring to edit setup. Settings are remembered on exit.',MUTED).grid(row=1,columnspan=2,sticky='w',pady=(6,18))
    settings.columnconfigure(1,weight=1)
    app.entries=[]
    fields=[('Capture method (screen / obs)',app.capture_method),('Screen monitor',app.monitor),
            ('OBS source',app.source),('WebSocket password',app.password),
            ('Save delay (seconds)',app.after)]
    for row,(title,var) in enumerate(fields,2):
        label(settings,title,MUTED).grid(row=row,column=0,sticky='w',padx=(0,16),pady=7)
        entry=ttk.Entry(settings,textvariable=var,show='●' if var is app.password else '')
        entry.grid(row=row,column=1,sticky='ew',pady=7); app.entries.append(entry)
    app.ocr_label=label(settings,'OCR: ready' if Path(app.tesseract.get()).is_file() else 'OCR: setup needed',MUTED)
    app.ocr_label.grid(row=7,column=0,sticky='w',pady=(12,0))
    app.ocr_button=ttk.Button(settings,text='Choose OCR executable…',command=app.choose_ocr)
    app.ocr_button.grid(row=7,column=1,sticky='e',pady=(12,0))
    ttk.Button(settings,text='Open activity log',command=app.open_activity_log).grid(row=8,columnspan=2,sticky='w',pady=(16,0))
    actions=tk.Frame(settings,bg=PANEL)
    actions.grid(row=10,columnspan=2,sticky='w',pady=(18,0))
    ttk.Button(actions,text='Save password',command=app.store_password).pack(side='left',padx=(0,8))
    ttk.Button(actions,text='Open password file',command=app.open_password_file).pack(side='left')
    ttk.Button(settings,text='Done',command=settings_window.withdraw).grid(row=11,columnspan=2,sticky='e',pady=(20,0))
    def open_settings():
        settings_window.deiconify(); settings_window.lift(); settings_window.focus_set()
    header=tk.Frame(root,bg=BG,padx=24,pady=18); header.pack(fill='x')
    logo=artwork('dark-and-darker-logo.png',(128,72))
    if logo is not None:
        tk.Label(header,image=logo,bg=BG,bd=0).pack(side='left',padx=(0,20))
        tk.Frame(header,bg=EDGE,width=1,height=48).pack(side='left',padx=(0,20))
    brand=tk.Frame(header,bg=BG); brand.pack(side='left')
    label(brand,'VAULTVISION',GOLD,('Palatino Linotype',25,'bold')).pack(anchor='w')
    label(brand,'DARK AND DARKER  •  COMBAT HIGHLIGHTS',MUTED,('Segoe UI',9)).pack(anchor='w',pady=(4,0))
    ttk.Button(header,text='Settings',command=open_settings).pack(side='right',padx=(20,0))
    app.status_label=label(header,'●  DISARMED',MUTED,('Segoe UI',10,'bold'))
    app.status_label.pack(side='right')
    body=tk.Frame(root,bg=BG,padx=24,pady=10); body.pack(fill='both',expand=True)
    body.columnconfigure(0,weight=0,minsize=290); body.columnconfigure(1,weight=1)
    body.rowconfigure(0,weight=1)
    left=tk.Frame(body,bg=PANEL,highlightbackground=EDGE,highlightthickness=1,padx=20,pady=22)
    left.grid(row=0,column=0,sticky='nsew',padx=(0,16))
    label(left,'SESSION',GOLD,('Segoe UI',9,'bold')).pack(anchor='w')
    app.phase_label=label(left,'Starting OBS',TEXT,('Segoe UI',15,'bold'),wraplength=250,justify='left')
    app.phase_label.pack(anchor='w',pady=(10,8))
    app.detail_label=label(left,'Preparing automatic highlights…',MUTED,wraplength=250,justify='left')
    app.detail_label.pack(anchor='w',pady=(0,14))
    app.character_label=label(left,'Character: automatic',TEXT,wraplength=250,justify='left')
    app.character_label.pack(anchor='w',pady=(0,20))
    app.heartbeat_label=label(left,'',MUTED,('Segoe UI',9),wraplength=250,justify='left')
    app.heartbeat_label.pack(anchor='w',pady=(0,14))
    app.start_button=ttk.Button(left,text='Automatic clips',style='Primary.TButton',command=app.toggle_monitoring)
    app.start_button.pack(fill='x')
    app.save_button=ttk.Button(left,text='Save clip now',command=app.manual_save)
    app.save_button.pack(fill='x',pady=(8,0))
    tk.Frame(left,bg=EDGE,height=1).pack(fill='x',pady=16)
    label(left,'CAPTURE',GOLD,('Segoe UI',9,'bold')).pack(anchor='w')
    ttk.Checkbutton(left,text='Include deaths',variable=app.capture_deaths).pack(anchor='w',pady=(12,8))
    delay_label=label(left,'',MUTED)
    delay_label.pack(anchor='w',pady=(0,12))
    def update_delay(*args):
        delay_label.configure(text='Save delay: '+app.after.get()+' seconds')
    app.after.trace_add('write',update_delay); update_delay()
    ttk.Button(left,text='Edit capture settings',command=open_settings).pack(fill='x')
    tk.Frame(left,bg=EDGE,height=1).pack(fill='x',pady=16)
    label(left,'OBS REPLAY BUFFER',GOLD,('Segoe UI',9,'bold')).pack(anchor='w')
    app.replay_label=label(left,'Checking OBS duration…',TEXT,('Segoe UI',12))
    app.replay_label.pack(anchor='w',pady=(8,6))
    label(left,'Clip length and location are set in OBS.',MUTED,justify='left',wraplength=240).pack(anchor='w')
    main=tk.Frame(body,bg=BG); main.grid(row=0,column=1,sticky='nsew')
    main.columnconfigure(0,weight=1); main.rowconfigure(0,weight=1)
    from clip_gallery import ClipGallery
    clips=tk.Frame(main,bg=PANEL,highlightbackground=EDGE,highlightthickness=1)
    clips.grid(row=0,column=0,sticky='nsew')
    app.gallery=ClipGallery(clips,app.say)
    wizard=artwork('wizard.png',(200,200))
    if wizard is not None:
        app.gallery.empty_art=wizard
        app.gallery.screen.configure(image=wizard,compound='top',text='Your next highlight belongs here\nSelect a replay below, or import a video.',font=('Segoe UI',11))
    app.saved_label=label(main,'No clips saved this session',MUTED,('Segoe UI',9),anchor='w',wraplength=650)
    app.saved_label.grid(row=1,column=0,sticky='ew',pady=(10,0))
    footer=tk.Frame(root,bg=BG,padx=24,pady=10); footer.pack(fill='x')
    label(footer,'Automatic combat highlights',MUTED,('Segoe UI',9)).pack(side='left')
    label(footer,'1080p  •  OBS replay buffer',MUTED,('Segoe UI',9)).pack(side='right')
