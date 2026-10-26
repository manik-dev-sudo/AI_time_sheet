import os
import time
import threading
from pathlib import Path
from tracker.logger import logger
from config import config

# Supported Excel extensions
EXCEL_EXTS = {".xlsx", ".xls", ".csv", ".xlsm"}

class ExcelFileHandler:
    def __init__(self):
        self.last_events = {}  # (filepath, action) -> timestamp
        self.debounce_seconds = 5.0

    def should_process(self, file_path, action):
        p = Path(file_path)
        # Ignore temp lock files like ~$Book1.xlsx
        if p.name.startswith("~$") or p.name.startswith(".~"):
            return False

        if p.suffix.lower() not in EXCEL_EXTS:
            return False

        key = (str(file_path), action)
        now = time.time()
        last_time = self.last_events.get(key, 0)
        if now - last_time < self.debounce_seconds:
            return False

        self.last_events[key] = now
        return True

    def on_created(self, file_path):
        if self.should_process(file_path, "CREATED"):
            p = Path(file_path)
            logger.log_event("FILE_EXCEL", {
                "action": "CREATED",
                "filename": p.name,
                "path": str(p.parent)
            })

    def on_modified(self, file_path):
        if self.should_process(file_path, "MODIFIED"):
            p = Path(file_path)
            logger.log_event("FILE_EXCEL", {
                "action": "MODIFIED",
                "filename": p.name,
                "path": str(p.parent)
            })

    def on_deleted(self, file_path):
        if self.should_process(file_path, "DELETED"):
            p = Path(file_path)
            logger.log_event("FILE_EXCEL", {
                "action": "DELETED",
                "filename": p.name,
                "path": str(p.parent)
            })

    def on_moved(self, src_path, dest_path):
        src_p = Path(src_path)
        dest_p = Path(dest_path)
        # Check if source or destination was an Excel file
        if dest_p.suffix.lower() in EXCEL_EXTS and not dest_p.name.startswith("~$"):
            logger.log_event("FILE_EXCEL", {
                "action": "RENAMED_OR_MOVED",
                "filename": dest_p.name,
                "old_name": src_p.name,
                "path": str(dest_p.parent)
            })


class FileMonitor:
    def __init__(self, watch_paths=None):
        self.watch_paths = watch_paths or config.get("watched_directories", [])
        self.handler = ExcelFileHandler()
        self.observer = None
        self._thread = None
        self._running = False

    def start(self):
        self._running = True
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            handler_instance = self.handler

            class WatchdogBridge(FileSystemEventHandler):
                def on_created(self, event):
                    if not event.is_directory:
                        handler_instance.on_created(event.src_path)

                def on_modified(self, event):
                    if not event.is_directory:
                        handler_instance.on_modified(event.src_path)

                def on_deleted(self, event):
                    if not event.is_directory:
                        handler_instance.on_deleted(event.src_path)

                def on_moved(self, event):
                    if not event.is_directory:
                        handler_instance.on_moved(event.src_path, event.dest_path)

            self.observer = Observer()
            watch_count = 0
            for path_str in self.watch_paths:
                if os.path.exists(path_str):
                    self.observer.schedule(WatchdogBridge(), path=path_str, recursive=True)
                    watch_count += 1

            if watch_count > 0:
                self.observer.start()
                print(f"[FileMonitor] Watchdog started observing {watch_count} directories.")
                return

        except ImportError:
            print("[FileMonitor] watchdog package not installed. Starting fallback directory scanner.")
        except Exception as e:
            print(f"[FileMonitor] Error starting watchdog observer: {e}. Starting fallback directory scanner.")

        # Fallback polling scanner
        self._start_fallback_scanner()

    def _start_fallback_scanner(self):
        def scan_loop():
            # Snapshot: filepath -> mtime
            file_snapshot = {}

            def take_snapshot():
                snap = {}
                for root_dir in self.watch_paths:
                    if not os.path.exists(root_dir):
                        continue
                    try:
                        for entry in os.scandir(root_dir):
                            if entry.is_file():
                                p = Path(entry.path)
                                if p.suffix.lower() in EXCEL_EXTS and not p.name.startswith("~$"):
                                    try:
                                        snap[entry.path] = entry.stat().st_mtime
                                    except OSError:
                                        pass
                    except Exception:
                        pass
                return snap

            file_snapshot = take_snapshot()

            while self._running:
                time.sleep(5)
                try:
                    current_snap = take_snapshot()
                    # Check created
                    for path, mtime in current_snap.items():
                        if path not in file_snapshot:
                            self.handler.on_created(path)
                        elif mtime != file_snapshot[path]:
                            self.handler.on_modified(path)

                    # Check deleted
                    for path in file_snapshot:
                        if path not in current_snap:
                            self.handler.on_deleted(path)

                    file_snapshot = current_snap
                except Exception as e:
                    print(f"[FileMonitor Fallback] Error in scanner: {e}")

        self._thread = threading.Thread(target=scan_loop, daemon=True, name="FallbackFileScanner")
        self._thread.start()

    def stop(self):
        self._running = False
        if self.observer:
            try:
                self.observer.stop()
                self.observer.join(timeout=2)
            except Exception:
                pass
