import os
import json
import threading
from datetime import datetime
from pathlib import Path
from config import LOGS_DIR

class ActivityLogger:
    def __init__(self, logs_dir=LOGS_DIR):
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._listeners = []

    def get_today_str(self):
        return datetime.now().strftime("%Y-%m-%d")

    def get_log_paths(self, date_str=None):
        if not date_str:
            date_str = self.get_today_str()
        txt_path = self.logs_dir / f"activity_{date_str}.txt"
        jsonl_path = self.logs_dir / f"activity_{date_str}.jsonl"
        return txt_path, jsonl_path

    def add_listener(self, callback):
        """Register a callback for live UI stream: callback(event_dict, formatted_line)"""
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def remove_listener(self, callback):
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)

    def log_event(self, event_type, details, duration_seconds=None):
        """
        Logs an activity event.
        event_type: 'WINDOW', 'FILE_EXCEL', 'WEB_VISIT', 'WEB_FORM', 'WEBMAIL_SENT', 'SYSTEM'
        details: dict of relevant fields
        """
        now = datetime.now()
        timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")

        event = {
            "timestamp": timestamp_str,
            "type": event_type,
            "duration_seconds": duration_seconds,
            "details": details
        }

        # Format human-readable line for the .txt file
        formatted_line = self._format_line(event)

        with self._lock:
            txt_path, jsonl_path = self.get_log_paths(now.strftime("%Y-%m-%d"))

            try:
                with open(txt_path, "a", encoding="utf-8") as f:
                    f.write(formatted_line + "\n")
            except Exception as e:
                print(f"[ActivityLogger] Error writing txt log: {e}")

            try:
                with open(jsonl_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(event) + "\n")
            except Exception as e:
                print(f"[ActivityLogger] Error writing jsonl log: {e}")

            # Notify live listeners (for UI)
            for listener in list(self._listeners):
                try:
                    listener(event, formatted_line)
                except Exception as e:
                    print(f"[ActivityLogger] Error calling listener: {e}")

        return event

    def _format_line(self, event):
        t = event["timestamp"]
        etype = event["type"]
        d = event["details"]
        dur = event.get("duration_seconds")
        dur_str = f" | Duration: {dur}s" if dur is not None and dur > 0 else ""

        if etype == "WINDOW":
            app = d.get("app", "Unknown")
            title = d.get("title", "")
            return f"[{t}] [WINDOW] App: {app} | Title: {title}{dur_str}"

        elif etype == "FILE_EXCEL":
            action = d.get("action", "ACCESSED")
            filename = d.get("filename", "")
            path = d.get("path", "")
            return f"[{t}] [FILE_EXCEL] Action: {action} | File: {filename} | Path: {path}"

        elif etype == "WEB_VISIT":
            url = d.get("url", "")
            title = d.get("title", "")
            return f"[{t}] [WEB_VISIT] Title: {title} | URL: {url}"

        elif etype == "WEB_FORM":
            url = d.get("url", "")
            form_name = d.get("form_name", "unnamed_form")
            fields = d.get("fields", [])
            fields_str = ", ".join(fields) if isinstance(fields, list) else str(fields)
            return f"[{t}] [WEB_FORM] URL: {url} | Form: {form_name} | Fields Filled: [{fields_str}]"

        elif etype == "WEBMAIL_SENT":
            service = d.get("service", "Webmail")
            to_list = d.get("to", "")
            subject = d.get("subject", "(No Subject)")
            return f"[{t}] [WEBMAIL_SENT] Service: {service} | To: {to_list} | Subject: {subject}"

        else:
            msg = d.get("message", json.dumps(d))
            return f"[{t}] [{etype}] {msg}{dur_str}"

    def read_log_text(self, date_str=None):
        txt_path, _ = self.get_log_paths(date_str)
        if not txt_path.exists():
            return ""
        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading log file: {e}"

# Singleton logger
logger = ActivityLogger()
