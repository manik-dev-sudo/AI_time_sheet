import threading
import time
from datetime import datetime
from tracker.window_monitor import WindowMonitor
from tracker.file_monitor import FileMonitor
from tracker.web_receiver import WebReceiverServer
from tracker.logger import logger
from config import config

class ActivityManager:
    def __init__(self, on_auto_analyze=None):
        self.window_monitor = WindowMonitor(
            poll_interval=config.get("poll_interval_seconds", 3),
            idle_threshold=config.get("idle_threshold_seconds", 300)
        )
        self.file_monitor = FileMonitor(config.get("watched_directories", []))
        self.web_receiver = WebReceiverServer(config.get("web_receiver_port", 58432))

        self.on_auto_analyze = on_auto_analyze
        self.is_running = False
        self.is_paused = False
        self._scheduler_thread = None
        self._scheduler_running = False

    def start(self):
        if self.is_running:
            return

        print("[ActivityManager] Starting all monitoring services...")
        self.is_running = True
        self.is_paused = False

        # Start components
        self.window_monitor.start()
        self.file_monitor.start()
        self.web_receiver.start()

        # Start auto-analyze scheduler
        self._scheduler_running = True
        self._scheduler_thread = threading.Thread(target=self._schedule_loop, daemon=True, name="SchedulerThread")
        self._scheduler_thread.start()

        logger.log_event("SYSTEM", {"message": "Timesheet tracking service started."})

    def pause(self):
        if not self.is_running or self.is_paused:
            return
        self.is_paused = True
        self.window_monitor.pause()
        logger.log_event("SYSTEM", {"message": "Tracking temporarily paused by user."})

    def resume(self):
        if not self.is_running or not self.is_paused:
            return
        self.is_paused = False
        self.window_monitor.resume()
        logger.log_event("SYSTEM", {"message": "Tracking resumed by user."})

    def stop(self):
        if not self.is_running:
            return
        print("[ActivityManager] Stopping monitoring services...")
        self.is_running = False
        self._scheduler_running = False

        self.window_monitor.stop()
        self.file_monitor.stop()
        self.web_receiver.stop()

        logger.log_event("SYSTEM", {"message": "Timesheet tracking service stopped."})

    def _schedule_loop(self):
        """Checks if auto-analyze trigger time has arrived at end of day."""
        last_triggered_date = None

        while self._scheduler_running:
            try:
                if config.get("auto_analyze_enabled", False):
                    target_time = config.get("auto_analyze_time", "18:00")
                    now = datetime.now()
                    current_time_str = now.strftime("%H:%M")
                    today_str = now.strftime("%Y-%m-%d")

                    if current_time_str == target_time and last_triggered_date != today_str:
                        last_triggered_date = today_str
                        print(f"[ActivityManager] Triggering end-of-day Gemma analysis for {today_str}...")
                        if self.on_auto_analyze:
                            threading.Thread(target=self.on_auto_analyze, args=(today_str,), daemon=True).start()
            except Exception as e:
                print(f"[ActivityManager] Error in scheduler loop: {e}")

            time.sleep(30)
