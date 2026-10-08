"""Screen-only arming gate, with immediate spectator and delayed HUD-loss guards."""
import re
from detector import crop,ocr,NAME

SPECTATOR=(.86,.60,1,.71)
HEALTH=(.405,.939,.595,.975)
def read_name(image,executable):
    text=ocr(crop(image,NAME),executable,7)
    # A single HUD-sized token; reject sentences/background OCR.
    return text if re.fullmatch(r'[A-Za-z0-9_]{3,32}',text) else ''
def spectator_present(text):
    text=re.sub(r'[^a-z ]',' ',text.lower())
    return any(term in text for term in
               ('watch death cam','change view','report player','change target'))
def health_present(image):
    bar=crop(image,HEALTH).convert('RGB')
    pixels=list(bar.getdata())
    # Health fill or a long neutral metallic border (including an empty bar).
    red=sum(r>65 and r>g*1.6 and r>b*1.5 for r,g,b in pixels)
    if red>len(pixels)*.02: return True
    for y in range(bar.height):
        row=[bar.getpixel((x,y)) for x in range(bar.width)]
        neutral=sum(min(p)>65 and max(p)-min(p)<35 for p in row)
        if neutral>bar.width*.65: return True
    return False

class GameGate:
    def __init__(self,missing_seconds=5):
        self.armed=False; self.hits=0; self.candidate=''; self.missing_since=None
        self.missing_seconds=missing_seconds
    def update(self,name,health,spectator,now):
        previous=self.armed; reason=''
        if spectator:
            self.armed=False; self.hits=0; self.candidate=''; self.missing_since=None
            reason='spectator controls'
        elif not name and not health:
            self.hits=0; self.candidate=''
            if self.missing_since is None: self.missing_since=now
            if now-self.missing_since>=self.missing_seconds:
                self.armed=False; reason='name and health bar absent for five seconds'
        else:
            self.missing_since=None
            if not self.armed:
                if name and health:
                    self.hits=self.hits+1 if name==self.candidate else 1
                    self.candidate=name
                    if self.hits>=3: self.armed=True; reason='name and health bar confirmed'
                else: self.hits=0; self.candidate=''
        return self.armed,previous!=self.armed,reason
