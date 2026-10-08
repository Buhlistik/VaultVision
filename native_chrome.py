"""Apply VaultVision colors to native Windows captions and borders."""
import sys
import tkinter as tk

def colorref(hex_color):
    value=hex_color.lstrip('#')
    red,green,blue=(int(value[i:i+2],16) for i in (0,2,4))
    return red | green<<8 | blue<<16

def theme_titlebar(window,caption='#171a1f',text='#c7a96b',border='#35312a'):
    if sys.platform!='win32': return
    def apply(event=None):
        if event is not None and event.widget is not window: return
        try:
            import ctypes
            from ctypes import wintypes
            user=ctypes.windll.user32
            user.GetAncestor.argtypes=[wintypes.HWND,wintypes.UINT]
            user.GetAncestor.restype=wintypes.HWND
            hwnd=user.GetAncestor(window.winfo_id(),2)  # Tk's native wrapper.
            if not hwnd: return
            setter=ctypes.windll.dwmapi.DwmSetWindowAttribute
            setter.argtypes=[wintypes.HWND,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD]
            setter.restype=ctypes.c_long
            dark=wintypes.BOOL(True)
            setter(hwnd,20,ctypes.byref(dark),ctypes.sizeof(dark))
            for attribute,color in ((34,border),(35,caption),(36,text)):
                value=wintypes.DWORD(colorref(color))
                # Unsupported Windows versions retain their native fallback.
                setter(hwnd,attribute,ctypes.byref(value),ctypes.sizeof(value))
        except (OSError,AttributeError,tk.TclError):
            pass
    window.bind('<Map>',apply,add='+')
    window.after_idle(apply)
