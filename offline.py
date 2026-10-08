"""Replay a recording through the same detector without connecting to OBS."""
import argparse,json,subprocess,tempfile
from pathlib import Path
from PIL import Image
from detector import Detector,crop,ocr,FEED,NAME

def main():
    p=argparse.ArgumentParser(); p.add_argument('video'); p.add_argument('--start',type=float,default=0); p.add_argument('--duration',type=float,default=15); p.add_argument('--name',default=''); a=p.parse_args()
    detector=Detector(a.name); events=[]
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-ss',str(a.start),'-i',a.video,'-t',str(a.duration),'-vf','fps=2',str(Path(d)/'%05d.png')],check=True)
        for i,path in enumerate(sorted(Path(d).glob('*.png'))):
            image=Image.open(path); now=a.start+i/2
            if not a.name: detector.update_name(ocr(crop(image,NAME),psm=7))
            for event in detector.process(ocr(crop(image,FEED)),now):
                events.append(event); print(json.dumps(event),flush=True)
    print(json.dumps({'active_name':detector.name,'events':len(events)}))
if __name__=='__main__': main()
