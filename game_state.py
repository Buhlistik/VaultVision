"""Screen-only arming gate, with immediate spectator and delayed HUD-loss guards."""
import re
from detector import crop,ocr,NAME,parse_feed,normalized
from difflib import SequenceMatcher

SPECTATOR=(.85,.575,1,.715)
DEATH_MENU=(.35,.16,.66,.39)
HEALTH=(.405,.939,.595,.975)
def read_name(image,executable):
    text=ocr(crop(image,NAME),executable,7)
    # A single HUD-sized token; reject sentences/background OCR.
    return text if re.fullmatch(r'[A-Za-z0-9_]{3,32}',text) else ''
def spectator_present(text):
    text=re.sub(r'[^a-z]','',text.lower())
    phrases=('watchdeathcam','changeview','reportplayer','changetarget','thirdpersoncam')
    return any(phrase in text for phrase in phrases)

def death_menu_present(text):
    text=re.sub(r'[^a-z]','',text.lower())
    return 'adventureover' in text or 'continuespectating' in text

def recover_death(image,executable,identity,now):
    """A confirmed death UI permits a tolerant victim read, never kill attribution."""
    wanted=normalized(identity)
    if len(wanted)<6: return None
    # Rows have fixed 20-pixel spacing at 1080p. Read newest rows first
    # separately so background textures cannot merge the entire feed.
    for row in reversed(range(10)):
        y=20+20*row
        region=crop(image,(.765,y/1080,1,(y+20)/1080))
        for event in parse_feed(ocr(region,executable,7)):
            victim=normalized(event['victim'])
            if abs(len(victim)-len(wanted))>2: continue
            if SequenceMatcher(None,victim,wanted).ratio()<.84: continue
            event.update(victim=identity,kind='death',time=now)
            return event
    return None
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
        self.missing_seconds=missing_seconds; self.spectating=False
    def update(self,name,health,spectator,now):
        previous=self.armed; reason=''
        if spectator:
            self.spectating=True
            self.armed=False; self.hits=0; self.candidate=''; self.missing_since=None
            reason='spectator controls'
        elif self.spectating:
            self.armed=False; self.hits=0; self.candidate=''
            if not name and not health:
                if self.missing_since is None: self.missing_since=now
                if now-self.missing_since>=self.missing_seconds:
                    self.spectating=False; self.missing_since=None
            else: self.missing_since=None
        elif not name and not health:
            self.hits=0; self.candidate=''
            if self.missing_since is None: self.missing_since=now
            if now-self.missing_since>=self.missing_seconds:
                self.armed=False; reason=f'name and health bar absent for {self.missing_seconds:g} seconds'
        else:
            self.missing_since=None
            if not self.armed:
                if health:
                    self.hits+=1
                    if self.hits>=3: self.armed=True; reason='health bar confirmed; spectator UI absent'
                else: self.hits=0; self.candidate=''
        return self.armed,previous!=self.armed,reason
