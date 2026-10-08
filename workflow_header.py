"""A compact live route from OBS readiness to a saved highlight."""
import tkinter as tk

class WorkflowHeader(tk.Frame):
    def __init__(self,parent):
        super().__init__(parent,bg='#0d0f12')
        self.status=tk.Label(self,text='●  PREPARING',bg='#0d0f12',fg='#c7a96b',font=('Segoe UI',9,'bold'),anchor='w')
        self.status.pack(fill='x')
        self.canvas=tk.Canvas(self,height=65,width=1,bg='#0d0f12',bd=0,highlightthickness=0)
        self.canvas.pack(fill='x',expand=True)
        self.state=(0,False,'Starting OBS')
        self.canvas.bind('<Configure>',lambda event:self.draw())
    def update_stage(self,stage,paused,heading):
        state=(stage,paused,heading)
        if state!=self.state: self.state=state; self.draw()
    def draw(self):
        canvas=self.canvas; canvas.delete('all')
        stage,paused,heading=self.state; width=max(100,canvas.winfo_width())
        steps=('OBS ready','Find match','Read name','Watch feed','Save clip')
        xs=[width*(index+.5)/5 for index in range(5)]
        for index in range(4):
            canvas.create_line(xs[index]+10,18,xs[index+1]-10,18,
                               fill='#776547' if index<stage else '#30343b',width=2)
        for index,(x,title) in enumerate(zip(xs,steps)):
            color='#c7a96b' if index<=stage and not paused else '#77756e'
            if index==stage:
                canvas.create_oval(x-13,5,x+13,31,outline='#776547' if not paused else '#4b4d52',width=2)
            canvas.create_oval(x-8,10,x+8,26,fill=color if index<=stage else '#252931',outline='')
            canvas.create_text(x,18,text='✓' if index<stage else str(index+1),fill='#0d0f12' if index<=stage else '#92979f',font=('Segoe UI',8,'bold'))
            canvas.create_text(x,43,text=title,fill=color if index==stage else '#92979f',width=max(30,width/5-8),font=('Segoe UI',9))
