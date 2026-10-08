"""Local password document shared across executable updates."""
import os
from pathlib import Path

def password_path():
    base=Path(os.environ.get('LOCALAPPDATA', Path.home()/'.local'/'share'))
    return base/'VaultVision'/'obs-websocket-password.txt'

def load_password():
    path=password_path()
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        path.write_text('',encoding='utf-8')
    return path.read_text(encoding='utf-8-sig').rstrip('\r\n')

def save_password(password):
    if '\n' in password or '\r' in password:
        raise ValueError('Use a single-line password.')
    path=password_path()
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(password,encoding='utf-8')
