"""Screen-only OCR and event state, shared by live and offline modes."""
import re, subprocess, tempfile, time
from pathlib import Path
from PIL import Image, ImageOps

# Ten feed rows extend to about y=220 at 1080p; include a margin.
FEED = (.68, 0, 1, .23)
NAME = (.455, .9, .55, .93)
def crop(image, box):
    w,h=image.size
    return image.crop(tuple(round(v*(w if i%2==0 else h)) for i,v in enumerate(box)))
def ocr(image, executable='tesseract', psm=6):
    image=ImageOps.grayscale(image.resize((image.width*3,image.height*3)))
    image=ImageOps.autocontrast(image)
    executable=executable.strip().strip('"')
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/'ocr.png'; image.save(p)
        output=Path(d)/'result'
        errors=Path(d)/'errors.txt'
        # File output avoids reliance on inherited console streams in a
        # PyInstaller --windowed application.
        try:
            with errors.open('wb') as error_file:
                r=subprocess.run(
                    [executable,str(p),str(output),'-l','eng','--psm',str(psm)],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=error_file, timeout=8,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        except FileNotFoundError as exc:
            raise RuntimeError('Tesseract was not found. Set the path to tesseract.exe in VaultVision.') from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError('Tesseract took longer than 8 seconds. Check the OCR installation.') from exc
        except OSError as exc:
            raise RuntimeError('Could not start Tesseract: '+str(exc)) from exc
        if r.returncode:
            details=errors.read_text(encoding='utf-8',errors='replace').strip()
            raise RuntimeError(f'Tesseract failed (exit {r.returncode}): '+(details or 'No diagnostic output. Check that the executable is Tesseract OCR and English language data is installed.'))
        result=output.with_suffix('.txt')
        if not result.exists():
            raise RuntimeError('Tesseract did not create OCR output. Check the executable path points to tesseract.exe.')
        return result.read_text(encoding='utf-8',errors='replace').strip()
def normalized(s): return re.sub(r'[^a-z0-9]','',s.lower())
def parse_feed(text):
    for line in text.splitlines():
        m=re.search(r'^\s*(.+?)\s+killed\s+([^()\[\]]+?)(?:\s*[\[(]([^\])]+)[\])]|$)',line,re.I)
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
            if current[key]>=1:
                self.seen[key]=now; e.update(kind=role,time=now); events.append(e)
                if role=='death': self.dead=True
        self.pending=current
        return events
