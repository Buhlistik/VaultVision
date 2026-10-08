"""Screen-only OCR and event state, shared by live and offline modes."""
import re, subprocess, tempfile, time
from pathlib import Path
from PIL import Image, ImageOps

FEED = (.68, 0, 1, .16)
NAME = (.455, .9, .55, .93)
def crop(image, box):
    w,h=image.size
    return image.crop(tuple(round(v*(w if i%2==0 else h)) for i,v in enumerate(box)))
def ocr(image, executable='tesseract', psm=6):
    image=ImageOps.grayscale(image.resize((image.width*3,image.height*3)))
    image=ImageOps.autocontrast(image)
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/'ocr.png'; image.save(p)
        r=subprocess.run([executable,str(p),'stdout','--psm',str(psm)],capture_output=True,text=True,timeout=8)
        if r.returncode: raise RuntimeError(r.stderr.strip())
        return r.stdout.strip()
def normalized(s): return re.sub(r'[^a-z0-9]','',s.lower())
def parse_feed(text):
    for line in text.splitlines():
        m=re.search(r'^\s*(.+?)\s+killed\s+([^()]+?)(?:\s*\(([^)]+)\)|$)',line,re.I)
        if m: yield {'killer':m[1].strip(),'victim':m[2].strip(),'weapon':(m[3] or '').strip()}
class Detector:
    def __init__(self, name=''):
        self.name=name; self.candidate=''; self.name_hits=0; self.seen={}; self.pending={}; self.dead=False
    def update_name(self,text):
        candidate=re.sub(r'[^A-Za-z0-9_]','',text)
        if not 3<=len(candidate)<=32: return
        if candidate==self.candidate: self.name_hits+=1
        else: self.candidate=candidate; self.name_hits=1
        if self.name_hits>=3 and not self.dead: self.name=candidate
    def process(self,text,now):
        self.seen={k:t for k,t in self.seen.items() if now-t<180}
        current={}; events=[]
        for e in parse_feed(text):
            role='kill' if normalized(e['killer'])==normalized(self.name) else 'death' if normalized(e['victim'])==normalized(self.name) else None
            if not role or not self.name: continue
            key=(normalized(e['killer']),normalized(e['victim']))
            if key in self.seen: self.seen[key]=now; continue
            current[key]=self.pending.get(key,0)+1
            if current[key]>=2:
                self.seen[key]=now; e.update(kind=role,time=now); events.append(e)
                if role=='death': self.dead=True
        self.pending=current
        return events
