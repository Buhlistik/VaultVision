"""Wrapped clip cards and a borderless scrollbar drawn in the app palette."""
import tkinter as tk

BG='#13161b'; INK='#e7dfcd'; MUTED='#92979f'; GOLD='#c7a96b'

class ClipList(tk.Frame):
    def __init__(self,parent):
        super().__init__(parent,bg=BG,bd=0,highlightthickness=0)
        self.entries={}; self.selected=None; self.bounds=[]; self.drag_offset=0
        self.canvas=tk.Canvas(self,bg=BG,bd=0,highlightthickness=0,width=1,takefocus=True)
        self.scroll=tk.Canvas(self,bg=BG,bd=0,highlightthickness=0,width=8)
        self.scroll.pack(side='right',fill='y',padx=(6,0))
        self.canvas.pack(side='left',fill='both',expand=True)
        self.canvas.configure(yscrollcommand=self.scroll_changed)
        self.canvas.bind('<Configure>',lambda e:self.redraw())
        self.scroll.bind('<Configure>',lambda e:self.scroll_changed(*self.canvas.yview()))
        self.canvas.bind('<Button-1>',self.click)
        self.canvas.bind('<MouseWheel>',lambda e:self.canvas.yview_scroll(-int(e.delta/120),'units'))
        self.canvas.bind('<Button-4>',lambda e:self.canvas.yview_scroll(-1,'units'))
        self.canvas.bind('<Button-5>',lambda e:self.canvas.yview_scroll(1,'units'))
        self.canvas.bind('<Up>',lambda e:self.step(-1))
        self.canvas.bind('<Down>',lambda e:self.step(1))
        self.scroll.bind('<Button-1>',self.start_drag)
        self.scroll.bind('<B1-Motion>',self.drag)
    def get_children(self): return tuple(self.entries)
    def delete(self,*ids):
        for iid in ids: self.entries.pop(iid,None)
        if self.selected not in self.entries: self.selected=None
        self.redraw()
    def insert(self,parent,position,iid,text,tags=()):
        kind,_,title=text.strip().partition('  ·  ')
        self.entries[iid]=(title or kind,kind if title else '')
        self.redraw()
    def selection(self): return (self.selected,) if self.selected is not None else ()
    def selection_set(self,iid):
        if iid not in self.entries: return
        self.selected=iid; self.redraw()
        self.event_generate('<<TreeviewSelect>>')
    def redraw(self):
        self.canvas.delete('all'); self.bounds=[]
        width=max(40,self.canvas.winfo_width()); y=0
        for iid,(title,kind) in self.entries.items():
            text=self.canvas.create_text(14,y+12,text=title,anchor='nw',width=max(20,width-28),
                                         fill=INK,font=('Segoe UI',10,'bold'))
            box=self.canvas.bbox(text); bottom=box[3]+8
            if kind:
                detail=self.canvas.create_text(14,bottom,text=kind,anchor='nw',width=max(20,width-28),
                                               fill=GOLD if iid==self.selected else MUTED,font=('Segoe UI',9))
                bottom=self.canvas.bbox(detail)[3]+12
            else: bottom+=4
            background=self.canvas.create_rectangle(0,y,width,bottom,fill='#302d27' if iid==self.selected else '#1b1f26',outline='')
            self.canvas.tag_lower(background)
            if iid==self.selected: self.canvas.create_rectangle(0,y,3,bottom,fill=GOLD,outline='')
            self.bounds.append((iid,y,bottom)); y=bottom+8
        if not self.entries:
            self.canvas.create_text(14,20,text='No clips yet\nYour saved highlights will appear here.',anchor='nw',
                                    width=max(20,width-28),fill=MUTED,font=('Segoe UI',10))
        self.canvas.configure(scrollregion=(0,0,width,max(1,y)),yscrollincrement=24)
    def click(self,event):
        self.canvas.focus_set(); y=self.canvas.canvasy(event.y)
        for iid,top,bottom in self.bounds:
            if top<=y<=bottom: self.selection_set(iid); break
    def step(self,direction):
        keys=list(self.entries)
        if not keys: return 'break'
        index=keys.index(self.selected) if self.selected in keys else (-1 if direction>0 else len(keys))
        self.selection_set(keys[max(0,min(len(keys)-1,index+direction))])
        for iid,top,bottom in self.bounds:
            if iid==self.selected:
                view=self.canvas.canvasy(0); height=self.canvas.winfo_height()
                if top<view or bottom>view+height:
                    total=float(self.canvas.cget('scrollregion').split()[3])
                    self.canvas.yview_moveto(max(0,(top if top<view else bottom-height)/total))
        return 'break'
    def scroll_changed(self,first,last):
        first,last=float(first),float(last); self.scroll.delete('all')
        if last-first>=.999: return
        height=max(1,self.scroll.winfo_height()); size=min(height,max(28,(last-first)*height))
        top=first/max(.001,1-(last-first))*(height-size)
        self.thumb=(top,top+size)
        self.scroll.create_rectangle(2,top,6,top+size,fill='#686054',outline='')
    def start_drag(self,event):
        top,bottom=getattr(self,'thumb',(0,0))
        self.drag_offset=event.y-top if top<=event.y<=bottom else (bottom-top)/2
        self.drag(event)
    def drag(self,event):
        first,last=self.canvas.yview(); height=max(1,self.scroll.winfo_height())
        size=min(height,max(28,(last-first)*height))
        fraction=max(0,min(1,(event.y-self.drag_offset)/max(1,height-size)))
        self.canvas.yview_moveto(fraction*max(0,1-(last-first)))
