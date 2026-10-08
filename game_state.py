"""Screen-only arming gate, with immediate spectator and delayed HUD-loss guards."""
import re
from detector import crop,ocr,NAME,parse_feed,normalized
from difflib import SequenceMatcher

SPECTATOR=(.85,.575,1,.715)
DEATH_MENU=(.35,.16,.66,.39)
LOBBY_BADGE=(32/1920,12/1080,105/1920,79/1080)
LOBBY_NAV=(140/1920,15/1080,940/1920,65/1080)

def lobby_badge_candidate(image):
    badge=crop(image,LOBBY_BADGE).convert('RGB')
    pixels=list(badge.getdata())
    gold=sum(r>90 and g>60 and r>g*1.1 and g>b*1.3 for r,g,b in pixels)
    return bool(pixels) and gold/len(pixels)>.45

def lobby_present(image,executable):
    if not lobby_badge_candidate(image): return False
    text=re.sub(r'[^a-z]','',ocr(crop(image,LOBBY_NAV),executable,6).lower())
    return sum(word in text for word in ('season','religion','skills','stash'))>=3

HEALTH=(780/1920,1020/1080,1140/1920,1043/1080)
def read_name(image,executable):
    text=ocr(crop(image,NAME),executable,7)
    # The narrow text band can still include a fragment of a nearby key icon.
    # Ignore short icon tokens; OCR can insert a space within a long username.
    tokens=re.findall(r'[A-Za-z0-9_]+',text)
    names=[token for token in tokens if 3<=len(token)<=32]
    name=''.join(names)
    return name if 3<=len(name)<=32 else ''
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
    # A health fill is a contiguous horizontal red strip, not scattered warm
    # scenery or a gray border. Require aligned runs across multiple rows.
    minimum=max(8,round(bar.width*.10))
    previous=None; consecutive=0
    for y in range(bar.height):
        run=0; best=0; end=0
        for x in range(bar.width):
            r,g,b=bar.getpixel((x,y))
            run=run+1 if r>65 and r>g*2 and r>b*2 else 0
            if run>best: best=run; end=x
        interval=(end-best+1,end)
        if best>=minimum:
            overlap=previous is not None and min(interval[1],previous[1])-max(interval[0],previous[0])+1>=minimum
            consecutive=consecutive+1 if overlap else 1
            if consecutive>=max(3,round(bar.height*.20)): return True
            previous=interval
        else:
            previous=None; consecutive=0
    return False

class GameGate:
    def __init__(self,missing_seconds=5):
        self.armed=False; self.hits=0; self.candidate=''; self.missing_since=None
        self.missing_seconds=missing_seconds; self.spectating=False
        self.lobby_hits=0; self.in_lobby=False
    def update(self,name,health,spectator,now,lobby=False):
        previous=self.armed; reason=''
        self.lobby_hits=self.lobby_hits+1 if lobby else 0
        self.in_lobby=self.lobby_hits>=2
        if lobby:
            # Suppress events immediately; two confirmations release the
            # spectator latch without shortening the floor-transition timeout.
            self.armed=False; self.hits=0; self.candidate=''; self.missing_since=None
            if self.in_lobby: self.spectating=False
            reason='lobby detected'
        elif spectator:
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
