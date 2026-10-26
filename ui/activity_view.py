import os
import subprocess
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from tracker.logger import logger
from config import config

class ActivityView(ctk.CTkFrame):
    def __init__(self, master, activity_manager, **kwargs):
        super().__init__(master, **kwargs)
        self.activity_manager = activity_manager
        self.event_filter = "ALL"
        self.total_event_count = 0

        self._setup_ui()
        self._load_existing_logs()

        # Connect live listener
        logger.add_listener(self.on_live_event)

    def _setup_ui(self):
        # 1. Top Control & Status Toolbar
        self.toolbar = ctk.CTkFrame(self, corner_radius=8, fg_color="#1e293b")
        self.toolbar.pack(fill="x", padx=15, pady=(15, 8))

        # Status Badge
        self.status_indicator = ctk.CTkLabel(
            self.toolbar, text="● Tracker Active", font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#34d399"
        )
        self.status_indicator.pack(side="left", padx=16, pady=10)

        self.btn_toggle_track = ctk.CTkButton(
            self.toolbar, text="Pause Tracking", width=120, height=32,
            fg_color="#ef4444", hover_color="#dc2626", command=self._toggle_tracking
        )
        self.btn_toggle_track.pack(side="left", padx=8)

        self.lbl_counter = ctk.CTkLabel(
            self.toolbar, text="Events logged today: 0", font=ctk.CTkFont(size=12),
            text_color="#94a3b8"
        )
        self.lbl_counter.pack(side="left", padx=16)

        self.btn_open_txt = ctk.CTkButton(
            self.toolbar, text="Open TXT Log File", width=130, height=32,
            fg_color="#334155", hover_color="#475569", command=self._open_txt_log
        )
        self.btn_open_txt.pack(side="right", padx=16)

        # 2. Filter Bar
        self.filter_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.filter_bar.pack(fill="x", padx=15, pady=4)

        ctk.CTkLabel(self.filter_bar, text="Filter: ", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")

        self.filter_var = ctk.StringVar(value="ALL")
        filters = [
            ("All Events", "ALL"),
            ("Excel Spreadsheets", "FILE_EXCEL"),
            ("Web Forms", "WEB_FORM"),
            ("Webmail Sent", "WEBMAIL_SENT"),
            ("Window Switches", "WINDOW")
        ]

        for label, val in filters:
            btn = ctk.CTkRadioButton(
                self.filter_bar, text=label, variable=self.filter_var, value=val,
                command=self._on_filter_changed, font=ctk.CTkFont(size=12)
            )
            btn.pack(side="left", padx=8)

        # 3. Live Log Text Area / Feed
        self.log_textbox = ctk.CTkTextbox(
            self, corner_radius=8, font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word", fg_color="#0f172a", text_color="#e2e8f0"
        )
        self.log_textbox.pack(fill="both", expand=True, padx=15, pady=(4, 15))

    def _toggle_tracking(self):
        if self.activity_manager.is_paused:
            self.activity_manager.resume()
            self.status_indicator.configure(text="● Tracker Active", text_color="#34d399")
            self.btn_toggle_track.configure(text="Pause Tracking", fg_color="#ef4444", hover_color="#dc2626")
        else:
            self.activity_manager.pause()
            self.status_indicator.configure(text="⏸ Tracker Paused", text_color="#f59e0b")
            self.btn_toggle_track.configure(text="Resume Tracking", fg_color="#10b981", hover_color="#059669")

    def _open_txt_log(self):
        txt_path, _ = logger.get_log_paths()
        if not txt_path.exists():
            messagebox.showinfo("No Log File", "No log file has been created yet today.")
            return

        try:
            os.startfile(str(txt_path))
        except Exception as e:
            messagebox.showerror("Error Opening Log", f"Could not open file: {e}")

    def _on_filter_changed(self):
        self.event_filter = self.filter_var.get()
        self._load_existing_logs()

    def _load_existing_logs(self):
        self.log_textbox.delete("1.0", "end")
        raw_text = logger.read_log_text()
        if not raw_text:
            self.log_textbox.insert("end", "[System] Activity tracker started. Waiting for user events...\n")
            self.total_event_count = 0
            self.lbl_counter.configure(text="Events logged today: 0")
            return

        lines = raw_text.splitlines()
        self.total_event_count = len(lines)
        self.lbl_counter.configure(text=f"Events logged today: {self.total_event_count}")

        display_lines = []
        for line in lines:
            if self.event_filter == "ALL":
                display_lines.append(line)
            elif f"[{self.event_filter}]" in line:
                display_lines.append(line)

        self.log_textbox.insert("end", "\n".join(display_lines) + "\n")
        self.log_textbox.see("end")

    def on_live_event(self, event_dict, formatted_line):
        def update_ui():
            self.total_event_count += 1
            self.lbl_counter.configure(text=f"Events logged today: {self.total_event_count}")

            if self.event_filter == "ALL" or f"[{self.event_filter}]" in formatted_line:
                self.log_textbox.insert("end", formatted_line + "\n")
                self.log_textbox.see("end")

        try:
            self.after(0, update_ui)
        except Exception:
            pass
