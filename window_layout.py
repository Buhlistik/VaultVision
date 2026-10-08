"""Bounds of the monitor containing the existing Windows app window."""
def monitor_bounds(hwnd):
    import ctypes
    from ctypes import wintypes
    class MonitorInfo(ctypes.Structure):
        _fields_=[('size',wintypes.DWORD),('monitor',wintypes.RECT),('work',wintypes.RECT),('flags',wintypes.DWORD)]
    user=ctypes.windll.user32
    user.MonitorFromWindow.argtypes=[wintypes.HWND,wintypes.DWORD]
    user.MonitorFromWindow.restype=wintypes.HANDLE
    user.GetMonitorInfoW.argtypes=[wintypes.HANDLE,ctypes.POINTER(MonitorInfo)]
    user.GetMonitorInfoW.restype=wintypes.BOOL
    info=MonitorInfo(); info.size=ctypes.sizeof(info)
    monitor=user.MonitorFromWindow(hwnd,2)
    if not user.GetMonitorInfoW(monitor,ctypes.byref(info)): raise ctypes.WinError()
    rect=info.monitor
    return rect.left,rect.top,rect.right-rect.left,rect.bottom-rect.top
