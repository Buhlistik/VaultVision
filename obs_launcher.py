"""Launch OBS once with the requested replay/tray flags."""
import subprocess
from pathlib import Path

OBS_EXE=Path(r'C:\Program Files\obs-studio\bin\64bit\obs64.exe')

def launch_obs():
    import psutil
    for process in psutil.process_iter(['name']):
        if (process.info.get('name') or '').lower()=='obs64.exe':
            return False
    if not OBS_EXE.is_file():
        raise FileNotFoundError('OBS was not found at '+str(OBS_EXE))
    subprocess.Popen([str(OBS_EXE),'--startreplaybuffer','--minimize-to-tray'],
                     cwd=str(OBS_EXE.parent),stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return True
