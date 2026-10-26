import sys
import time
import threading
import ctypes
from ctypes import wintypes
from tracker.logger import logger
from config import config

# Windows API constants and types for ctypes fallback
user32 = ctypes.windll.user32 if sys.platform == "win32" else None
kernel32 = ctypes.windll.kernel32 if sys.platform == "win32" else None

class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.UINT),
        ('dwTime', wintypes.DWORD),
    ]

def get_idle_duration_seconds():
    """Returns the time in seconds since the last user mouse/keyboard input."""
    if not user32:
        return 0
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if user32.GetLastInputInfo(ctypes.byref(lii)):
        millis = kernel32.GetTickCount() - lii.dwTime
        return millis / 1000.0
    return 0

def get_active_window_info():
    """Returns (app_name, window_title) for the foreground window using Win32 API."""
    if not user32:
        return ("Unknown", "Unknown")

    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return (None, None)

    # Get Window Title
    length = user32.GetWindowTextLengthW(hwnd)
    buff = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buff, length + 1)
    title = buff.value.strip()

    # Get Process Name
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    app_name = "Unknown"

    # Try psutil or process query handle if possible
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    h_proc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if h_proc:
        try:
            # QueryFullProcessImageNameW
            proc_buf = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(1024)
            if hasattr(kernel32, "QueryFullProcessImageNameW"):
                if kernel32.QueryFullProcessImageNameW(h_proc, 0, proc_buf, ctypes.byref(size)):
                    full_path = proc_buf.value
                    app_name = full_path.split("\\")[-1]
        finally:
            kernel32.CloseHandle(h_proc)

    return (app_name, title)


class WindowMonitor(threading.Thread):
    def __init__(self, poll_interval=2.0, idle_threshold=300):
        super().__init__(daemon=True, name="WindowMonitorThread")
        self.poll_interval = poll_interval
        self.idle_threshold = idle_threshold
        self._running = False
        self._paused = False

        self.current_app = None
        self.current_title = None
        self.current_start_time = None
        self.is_idle = False

    def run(self):
        self._running = True
        self.current_start_time = time.time()

        while self._running:
            try:
                if self._paused:
                    time.sleep(self.poll_interval)
                    continue

                # Check idle status
                idle_sec = get_idle_duration_seconds()
                if idle_sec > self.idle_threshold:
                    if not self.is_idle:
                        self.is_idle = True
                        self._flush_current_window()
                        logger.log_event("SYSTEM", {"message": f"User is IDLE (no input for {int(idle_sec)}s). Tracking paused."})
                    time.sleep(self.poll_interval)
                    continue
                else:
                    if self.is_idle:
                        self.is_idle = False
                        self.current_start_time = time.time()
                        logger.log_event("SYSTEM", {"message": "User resumed activity."})

                # Check active window
                app, title = get_active_window_info()

                # Filter out empty or system shell noise
                if not title or title in ["Task Switching", "Running applications"]:
                    time.sleep(self.poll_interval)
                    continue

                if app != self.current_app or title != self.current_title:
                    # Active window changed -> flush previous window duration
                    self._flush_current_window()
                    self.current_app = app
                    self.current_title = title
                    self.current_start_time = time.time()

            except Exception as e:
                print(f"[WindowMonitor] Error in polling loop: {e}")

            time.sleep(self.poll_interval)

        # Final flush on stop
        self._flush_current_window()

    def _flush_current_window(self):
        if self.current_app and self.current_title and self.current_start_time:
            duration = int(time.time() - self.current_start_time)
            # Only record if held focus for at least 3 seconds to avoid task-switch flickers
            if duration >= 3:
                logger.log_event("WINDOW", {
                    "app": self.current_app,
                    "title": self.current_title
                }, duration_seconds=duration)
        self.current_start_time = time.time()

    def pause(self):
        self._paused = True
        self._flush_current_window()

    def resume(self):
        self.current_start_time = time.time()
        self._paused = False

    def stop(self):
        self._running = False
