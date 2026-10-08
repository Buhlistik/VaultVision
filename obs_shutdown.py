"""Graceful Windows OBS shutdown; never force-kill a recording process."""
import ctypes
from ctypes import wintypes
import os

def close_obs_windows():
    if os.name!='nt': return 0
    import psutil
    pids={p.pid for p in psutil.process_iter(['name'])
          if (p.info.get('name') or '').lower()=='obs64.exe'}
    if not pids: return 0
    user=ctypes.WinDLL('user32',use_last_error=True)
    callback_type=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    user.EnumWindows.argtypes=[callback_type,wintypes.LPARAM]
    user.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
    user.GetWindowTextLengthW.argtypes=[wintypes.HWND]
    user.GetWindowTextW.argtypes=[wintypes.HWND,wintypes.LPWSTR,ctypes.c_int]
    user.PostMessageW.argtypes=[wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM]
    found=[]
    def visit(hwnd,param):
        pid=wintypes.DWORD()
        user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
        if pid.value in pids:
            title=ctypes.create_unicode_buffer(user.GetWindowTextLengthW(hwnd)+1)
            user.GetWindowTextW(hwnd,title,len(title))
            if title.value.upper().startswith('OBS'):
                found.append(hwnd)
        return True
    callback=callback_type(visit)
    user.EnumWindows(callback,0)
    count=sum(bool(user.PostMessageW(hwnd,0x0010,0,0)) for hwnd in found)
    if pids and not count:
        raise RuntimeError('Could not request OBS shutdown. Close OBS from its tray icon.')
    return count
