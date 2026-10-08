"""Ten isolated killfeed rows with semantic identities independent of row position."""
import hashlib,re
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from detector import crop,ocr,parse_feed,normalized,same_ocr_name

def row_box(row):
    return (.70,(20+20*row)/1080,1,(40+20*row)/1080)

def event_key(event):
    tokens=event['killer'].split()
    return normalized(tokens[-1] if tokens else ''),normalized(event['victim'])

def matches(a,b):
    ka,va=event_key(a); kb,vb=event_key(b)
    # Matching existing entries may tolerate OCR drift; this never attributes
    # a new kill to the player. Live attribution remains exact in Detector.
    return same_ocr_name(ka,kb) and same_ocr_name(va,vb)

def line(event):
    weapon=event.get('weapon','')
    return event['killer']+' killed '+event['victim']+(' ['+weapon+']' if weapon else '')

class RowTracker:
    def __init__(self):
        self.rows={}; self.next_id=0; self.last_shift=0
    def reset(self):
        self.rows={}; self.last_shift=0
    def update(self,observations):
        parsed={}
        for row,text in observations.items():
            events=list(parse_feed(text))
            if len(events)==1: parsed[row]=events[0]
        # Vote for a common upward shift. Empty slots append without movement;
        # full feeds can move several rows between captures.
        votes={}
        for row,event in parsed.items():
            candidates=[(old_row,track) for old_row,track in self.rows.items() if old_row>=row and matches(event,track['event'])]
            exact=[item for item in candidates if event_key(event)==event_key(item[1]['event'])]
            for old_row,track in exact or candidates:
                shift=old_row-row
                votes[shift]=votes.get(shift,0)+1
        shift=max(votes,key=lambda amount:(votes[amount],-amount)) if votes else 0
        confident=bool(votes) and (shift==0 or votes[shift]>=2)
        self.last_shift=shift if confident else 0
        result={}
        used=set()
        for row,event in parsed.items():
            previous=None
            predicted=self.rows.get(row+shift) if confident else None
            if predicted and matches(event,predicted['event']): previous=predicted
            if previous is None:
                # One clear entry is enough to keep its identity while moving,
                # but cannot be used to carry other unreadable rows along.
                candidates=[track for old_row,track in self.rows.items()
                            if old_row>=row and matches(event,track['event']) and track['id'] not in used]
                if candidates: previous=candidates[0]
            if previous:
                track=previous; used.add(track['id'])
                # Preserve a previously clean read instead of replacing it
                # with a one-character OCR mutation after a row shift.
            else:
                self.next_id+=1
                track={'id':self.next_id,'event':event}
            result[row]=track
        if confident:
            for old_row,track in self.rows.items():
                row=old_row-shift
                if 0<=row<10 and row not in parsed and track['id'] not in used:
                    # Only retain an unreadable slot when at least two other
                    # rows confirm the same alignment, and never across a reset.
                    if votes[shift]>=2:
                        result[row]=track; used.add(track['id'])
        self.rows=result
        return '\n'.join(line(track['event']) for row,track in sorted(result.items()))

class RowFeedReader:
    def __init__(self):
        self.pool=ThreadPoolExecutor(max_workers=2,thread_name_prefix='feed-row')
        self.cache={}; self.tracker=RowTracker()
    def reset(self):
        self.cache={}; self.tracker.reset()
    def read(self,image,executable,recognize=None):
        recognize=recognize or ocr
        crops={row:crop(image,row_box(row)) for row in range(10)}
        hashes={row:hashlib.blake2b(region.tobytes(),digest_size=8).digest() for row,region in crops.items()}
        results={}; tasks={}
        for row,region in crops.items():
            cached=self.cache.get(row)
            if cached and cached[0]==hashes[row]: results[row]=cached[1]
            else: tasks[row]=self.pool.submit(recognize,region,executable,7)
        for row,task in tasks.items(): results[row]=task.result()
        self.cache={row:(hashes[row],text) for row,text in results.items()}
        return self.tracker.update(results)
    def close(self):
        self.pool.shutdown(wait=True,cancel_futures=True)
