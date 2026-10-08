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
    root.geometry('1480x850'); root.minsize(1120,760)
    root.configure(bg=BG)
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
    settings_window.geometry('680x640'); settings_window.minsize(640,600)
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
            ('Character override',app.name),('Save delay (seconds)',app.after),
            ('HUD absence timeout (seconds)',app.hud_timeout),('Tesseract executable',app.tesseract)]
    for row,(title,var) in enumerate(fields,2):
        label(settings,title,MUTED).grid(row=row,column=0,sticky='w',padx=(0,16),pady=7)
        entry=ttk.Entry(settings,textvariable=var,show='●' if var is app.password else '')
        entry.grid(row=row,column=1,sticky='ew',pady=7); app.entries.append(entry)
    actions=tk.Frame(settings,bg=PANEL)
    actions.grid(row=10,columnspan=2,sticky='w',pady=(18,0))
    ttk.Button(actions,text='Save password',command=app.store_password).pack(side='left',padx=(0,8))
    ttk.Button(actions,text='Open password file',command=app.open_password_file).pack(side='left')
    ttk.Button(settings,text='Done',command=settings_window.withdraw).grid(row=11,columnspan=2,sticky='e',pady=(20,0))
    def open_settings():
        settings_window.deiconify(); settings_window.lift(); settings_window.focus_set()
    header=tk.Frame(root,bg=BG,padx=24,pady=18); header.pack(fill='x')
    brand=tk.Frame(header,bg=BG); brand.pack(side='left')
    label(brand,'VaultVision',GOLD,('Georgia',24,'bold')).pack(anchor='w')
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
    label(left,'Ready for the dungeon',TEXT,('Segoe UI',16,'bold')).pack(anchor='w',pady=(10,8))
    label(left,'Automatic highlights while you play.\nDetection pauses in the lobby\nand while spectating.',MUTED,justify='left').pack(anchor='w',pady=(0,22))
    app.character_label=label(left,'Character: automatic',TEXT,wraplength=250,justify='left')
    app.character_label.pack(anchor='w',pady=(0,20))
    app.start_button=ttk.Button(left,text='Start monitoring',style='Primary.TButton',command=app.start)
    app.start_button.pack(fill='x')
    ttk.Button(left,text='Pause monitoring',command=app.stop.set).pack(fill='x',pady=8)
    ttk.Button(left,text='Save replay now',command=app.manual.set).pack(fill='x')
    tk.Frame(left,bg=EDGE,height=1).pack(fill='x',pady=24)
    label(left,'CAPTURE',GOLD,('Segoe UI',9,'bold')).pack(anchor='w')
    ttk.Checkbutton(left,text='Include deaths',variable=app.capture_deaths).pack(anchor='w',pady=(12,8))
    delay_label=label(left,'',MUTED)
    delay_label.pack(anchor='w',pady=(0,12))
    def update_delay(*args):
        delay_label.configure(text='Save delay: '+app.after.get()+' seconds')
    app.after.trace_add('write',update_delay); update_delay()
    ttk.Button(left,text='Edit capture settings',command=open_settings).pack(fill='x')
    tk.Frame(left,bg=EDGE,height=1).pack(fill='x',pady=24)
    label(left,'OBS REPLAY BUFFER',GOLD,('Segoe UI',9,'bold')).pack(anchor='w')
    app.replay_label=label(left,'Checking OBS duration…',TEXT,('Segoe UI',12))
    app.replay_label.pack(anchor='w',pady=(8,6))
    label(left,'Clip duration and save location\nare set in OBS.',MUTED,justify='left').pack(anchor='w')
    main=tk.Frame(body,bg=BG); main.grid(row=0,column=1,sticky='nsew')
    main.columnconfigure(0,weight=1); main.rowconfigure(0,weight=1)
    from clip_gallery import ClipGallery
    clips=tk.Frame(main,bg=PANEL,highlightbackground=EDGE,highlightthickness=1)
    clips.grid(row=0,column=0,sticky='nsew')
    app.gallery=ClipGallery(clips,app.say)
    activity=tk.Frame(main,bg=PANEL,highlightbackground=EDGE,highlightthickness=1,padx=16,pady=12)
    activity.grid(row=1,column=0,sticky='ew',pady=(12,0))
    log_header=tk.Frame(activity,bg=PANEL); log_header.pack(fill='x')
    label(log_header,'ACTIVITY',MUTED,('Segoe UI',9,'bold')).pack(side='left')
    logs=tk.Frame(activity,bg=PANEL); logs.pack(fill='x',pady=(8,0))
    app.log=tk.Text(logs,height=5,width=48,state='disabled',bg='#101216',fg=TEXT,
                    font=('Consolas',9),relief='flat',borderwidth=0,padx=10,pady=8,
                    selectbackground='#4c4030',wrap='word')
    scroll=ttk.Scrollbar(logs,command=app.log.yview); app.log.configure(yscrollcommand=scroll.set)
    scroll.pack(side='right',fill='y'); app.log.pack(side='left',fill='x',expand=True)
    app.log.tag_configure('kill',foreground='#d7be7d'); app.log.tag_configure('error',foreground='#ed9382')
    def toggle_log():
        if logs.winfo_manager():
            logs.pack_forget(); log_toggle.configure(text='Show')
        else:
            logs.pack(fill='x',pady=(8,0)); log_toggle.configure(text='Hide')
    log_toggle=tk.Button(log_header,text='Hide',command=toggle_log,bg=PANEL,fg=MUTED,
                         activebackground=PANEL,activeforeground=GOLD,bd=0,cursor='hand2')
    log_toggle.pack(side='right')
    footer=tk.Frame(root,bg=BG,padx=24,pady=10); footer.pack(fill='x')
    label(footer,'Automatic combat highlights',MUTED,('Segoe UI',9)).pack(side='left')
    label(footer,'1080p  •  OBS replay buffer',MUTED,('Segoe UI',9)).pack(side='right')
