import sys
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from tracker.activity_manager import ActivityManager
from analyzer.gemma_client import GemmaClient
from ui.timesheet_view import TimesheetView
from ui.activity_view import ActivityView
from ui.settings_view import SettingsView
from ui.tray_icon import TrayManager

# Appearance configuration
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Auto Timesheet Desktop — Local Gemma Analysis")
        self.geometry("1060x740")
        self.minsize(880, 600)

        # Clients and managers
        self.gemma_client = GemmaClient()
        self.activity_manager = ActivityManager(on_auto_analyze=self._on_auto_analyze_trigger)

        # Start tracking in background
        self.activity_manager.start()

        # Build Interface
        self._setup_ui()

        # Initialize System Tray
        self.tray_manager = TrayManager(
            app_window=self,
            on_show=self.show_window,
            on_toggle_track=self.activity_view._toggle_tracking,
            on_analyze=self.timesheet_view.analyze_current_date,
            on_exit=self.exit_application
        )
        self.tray_manager.start()

        # Override close button to minimize to tray
        self.protocol("WM_DELETE_WINDOW", self.on_close_button)

    def _setup_ui(self):
        # 1. Top Global Navigation Bar
        self.top_bar = ctk.CTkFrame(self, height=54, corner_radius=0, fg_color="#0f172a")
        self.top_bar.pack(fill="x", side="top")

        # Logo and Title
        title_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        title_frame.pack(side="left", padx=16, pady=8)

        lbl_logo = ctk.CTkLabel(
            title_frame, text="⏱ Auto Timesheet", font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#ffffff"
        )
        lbl_logo.pack(side="left")

        lbl_badge = ctk.CTkLabel(
            title_frame, text=" LM Studio / Gemma ", font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#4f46e5", text_color="#ffffff", corner_radius=6
        )
        lbl_badge.pack(side="left", padx=10)

        # Minimize to Tray Button
        self.btn_minimize = ctk.CTkButton(
            self.top_bar, text="Minimize to Tray", width=120, height=32,
            fg_color="#334155", hover_color="#475569", command=self.minimize_to_tray
        )
        self.btn_minimize.pack(side="right", padx=16, pady=8)

        # 2. Main Tab View
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=12, pady=(4, 12))

        tab_timesheet = self.tabview.add("Timesheet")
        tab_activity = self.tabview.add("Live Activity Feed")
        tab_settings = self.tabview.add("Settings")

        # Initialize Sub-Views
        self.timesheet_view = TimesheetView(tab_timesheet, gemma_client=self.gemma_client)
        self.timesheet_view.pack(fill="both", expand=True)

        self.activity_view = ActivityView(tab_activity, activity_manager=self.activity_manager)
        self.activity_view.pack(fill="both", expand=True)

        self.settings_view = SettingsView(tab_settings, gemma_client=self.gemma_client)
        self.settings_view.pack(fill="both", expand=True)

    def _on_auto_analyze_trigger(self, date_str):
        """Called automatically at scheduled end-of-day time."""
        print(f"[MainApp] Executing scheduled Gemma analysis for {date_str}...")
        self.timesheet_view.analyze_current_date()

    def minimize_to_tray(self):
        self.withdraw()

    def show_window(self):
        self.after(0, self._restore)

    def _restore(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def on_close_button(self):
        # Minimize to tray instead of quitting directly
        self.withdraw()

    def exit_application(self):
        print("[MainApp] Exiting application...")
        self.activity_manager.stop()
        self.tray_manager.stop()
        self.quit()
        self.destroy()
        sys.exit(0)
