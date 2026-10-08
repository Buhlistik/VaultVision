"""Graceful OBS shutdown, including its English active-outputs confirmation."""
import ctypes
from ctypes import wintypes
import os
import time


def stop_replay_buffer(connection, timeout=15):
    """Stop is asynchronous: wait for OBS to report the output inactive."""
    if connection.request('GetReplayBufferStatus')['outputActive']:
        connection.request('StopReplayBuffer')
    deadline = time.monotonic() + timeout
    while connection.request('GetReplayBufferStatus')['outputActive']:
        if time.monotonic() >= deadline:
            raise RuntimeError('OBS replay buffer did not finish stopping.')
        time.sleep(.2)


def confirm_exit_dialog(desktop, pid):
    """Invoke only Yes in OBS's known exit warning; no global keyboard input."""
    for dialog in desktop.windows(process=pid, title='Active Outputs'):
        texts = [item.window_text() for item in dialog.descendants(control_type='Text')]
        if not any('OBS is still currently active.' in text and
                   'All streams/recordings will be shut down.' in text for text in texts):
            continue
        buttons = [button for button in dialog.descendants(control_type='Button')
                   if button.window_text().replace('&', '').strip() == 'Yes']
        if len(buttons) == 1 and buttons[0].is_enabled():
            buttons[0].click()
            return True
    return False


def close_obs_windows(timeout=30):
    if os.name != 'nt':
        return 0
    import psutil
    processes = []
    for process in psutil.process_iter(['name']):
        if (process.info.get('name') or '').lower() == 'obs64.exe':
            processes.append(process)
    if not processes:
        return 0
    pids = {process.pid for process in processes}
    user = ctypes.WinDLL('user32', use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    found = []
    def visit(hwnd, param):
        pid = wintypes.DWORD()
        user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids:
            title = ctypes.create_unicode_buffer(user.GetWindowTextLengthW(hwnd) + 1)
            user.GetWindowTextW(hwnd, title, len(title))
            if title.value.upper().startswith('OBS'):
                found.append(hwnd)
        return True
    callback = callback_type(visit)
    user.EnumWindows(callback, 0)
    count = sum(bool(user.PostMessageW(hwnd, 0x0010, 0, 0)) for hwnd in found)
    if not count and any(process.is_running() for process in processes):
        raise RuntimeError('Could not request OBS shutdown. Close OBS from its tray icon.')

    # UIA is loaded only at shutdown. Qt exposes its dialog/buttons through UIA.
    # Initialize COM on this background thread before importing pywinauto.
    import comtypes
    comtypes.CoInitialize()
    try:
        from pywinauto import Desktop
        desktop = Desktop(backend='uia')
        deadline = time.monotonic() + timeout
        last_error = ''
        while True:
            running = [process for process in processes if process.is_running()]
            if not running:
                return count
            for process in running:
                try:
                    confirm_exit_dialog(desktop, process.pid)
                except Exception as exc:
                    # Windows can disappear between enumeration and invocation.
                    last_error = str(exc)
            if time.monotonic() >= deadline:
                detail = (' UI automation: ' + last_error) if last_error else ''
                raise RuntimeError('OBS did not exit within 30 seconds. Check for an open dialog. '
                                   'Automatic confirmation requires OBS in English and both apps '
                                   'running at the same permission level.' + detail)
            time.sleep(.2)
    finally:
        comtypes.CoUninitialize()
