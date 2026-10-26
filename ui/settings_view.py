import os
import threading
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk

from config import config, BASE_DIR, LOGS_DIR
from analyzer.gemma_client import GemmaClient

class SettingsView(ctk.CTkScrollableFrame):
    def __init__(self, master, gemma_client=None, **kwargs):
        super().__init__(master, **kwargs)
        self.gemma_client = gemma_client or GemmaClient()

        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        # 1. LM Studio & Gemma Section
        card_lm = ctk.CTkFrame(self, corner_radius=10, fg_color="#1e293b")
        card_lm.pack(fill="x", padx=15, pady=10)

        lbl_lm_title = ctk.CTkLabel(
            card_lm, text="LM Studio & Local Gemma Model",
            font=ctk.CTkFont(size=15, weight="bold"), text_color="#38bdf8"
        )
        lbl_lm_title.pack(anchor="w", padx=16, pady=(12, 6))

        # URL
        row_url = ctk.CTkFrame(card_lm, fg_color="transparent")
        row_url.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row_url, text="LM Studio Base URL:", width=150, anchor="w").pack(side="left")
        self.entry_url = ctk.CTkEntry(row_url, placeholder_text="http://localhost:1234/v1")
        self.entry_url.pack(side="left", fill="x", expand=True)

        # Model Name
        row_model = ctk.CTkFrame(card_lm, fg_color="transparent")
        row_model.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(row_model, text="Model Identifier:", width=150, anchor="w").pack(side="left")
        self.entry_model = ctk.CTkEntry(row_model, placeholder_text="e.g. gemma-2-9b-it or leave blank to auto-detect")
        self.entry_model.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.btn_detect_model = ctk.CTkButton(
            row_model, text="Auto-Detect", width=100, fg_color="#475569",
            command=self._detect_models
        )
        self.btn_detect_model.pack(side="right")

        # Test Connection Button & Status
        row_test = ctk.CTkFrame(card_lm, fg_color="transparent")
        row_test.pack(fill="x", padx=16, pady=(10, 14))

        self.btn_test = ctk.CTkButton(
            row_test, text="Test LM Studio Connection", fg_color="#6366f1", hover_color="#4f46e5",
            command=self._test_connection
        )
        self.btn_test.pack(side="left")

        self.lbl_test_result = ctk.CTkLabel(row_test, text="", font=ctk.CTkFont(size=12))
        self.lbl_test_result.pack(side="left", padx=14)

        # 2. Automated End-of-Day Schedule Section
        card_sched = ctk.CTkFrame(self, corner_radius=10, fg_color="#1e293b")
        card_sched.pack(fill="x", padx=15, pady=10)

        lbl_sched_title = ctk.CTkLabel(
            card_sched, text="End-of-Day Automatic Timesheet Generation",
            font=ctk.CTkFont(size=15, weight="bold"), text_color="#38bdf8"
        )
        lbl_sched_title.pack(anchor="w", padx=16, pady=(12, 6))

        row_sched = ctk.CTkFrame(card_sched, fg_color="transparent")
        row_sched.pack(fill="x", padx=16, pady=(4, 14))

        self.var_auto_enabled = ctk.BooleanVar(value=False)
        self.chk_auto = ctk.CTkCheckBox(
            row_sched, text="Automatically trigger Gemma analysis daily at:",
            variable=self.var_auto_enabled
        )
        self.chk_auto.pack(side="left")

        self.entry_time = ctk.CTkEntry(row_sched, width=80, placeholder_text="18:00")
        self.entry_time.pack(side="left", padx=10)

        ctk.CTkLabel(row_sched, text="(24-hour format, e.g. 18:00 for 6:00 PM)", text_color="#94a3b8").pack(side="left")

        # 3. Watched Directories (Excel File Tracking)
        card_dirs = ctk.CTkFrame(self, corner_radius=10, fg_color="#1e293b")
        card_dirs.pack(fill="x", padx=15, pady=10)

        lbl_dirs_title = ctk.CTkLabel(
            card_dirs, text="Watched Directories (Excel Created / Edited / Deleted)",
            font=ctk.CTkFont(size=15, weight="bold"), text_color="#38bdf8"
        )
        lbl_dirs_title.pack(anchor="w", padx=16, pady=(12, 4))

        self.txt_dirs = ctk.CTkTextbox(card_dirs, height=90, font=ctk.CTkFont(family="Consolas", size=12))
        self.txt_dirs.pack(fill="x", padx=16, pady=6)

        row_dir_btns = ctk.CTkFrame(card_dirs, fg_color="transparent")
        row_dir_btns.pack(fill="x", padx=16, pady=(4, 14))

        btn_add_dir = ctk.CTkButton(row_dir_btns, text="Add Folder", width=100, command=self._add_directory)
        btn_add_dir.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(row_dir_btns, text="Monitors .xlsx, .xls, .csv, and .xlsm files in these folders.", text_color="#94a3b8").pack(side="left")

        # 4. Companion Browser Extension Setup Card
        card_ext = ctk.CTkFrame(self, corner_radius=10, fg_color="#1e293b")
        card_ext.pack(fill="x", padx=15, pady=10)

        lbl_ext_title = ctk.CTkLabel(
            card_ext, text="Companion Browser Extension (Web Forms & Webmail Sent)",
            font=ctk.CTkFont(size=15, weight="bold"), text_color="#38bdf8"
        )
        lbl_ext_title.pack(anchor="w", padx=16, pady=(12, 4))

        ext_guide = (
            "To capture website form submissions and outgoing Gmail/Outlook emails:\n"
            "1. Open Chrome or Edge and navigate to chrome://extensions (or edge://extensions).\n"
            "2. Turn ON 'Developer mode' (top right toggle).\n"
            "3. Click 'Load unpacked' and select the 'browser_extension' folder inside this project.\n"
            "4. The extension communicates locally with this app over port 58432."
        )
        lbl_ext_desc = ctk.CTkLabel(
            card_ext, text=ext_guide, justify="left", font=ctk.CTkFont(size=12),
            text_color="#cbd5e1"
        )
        lbl_ext_desc.pack(anchor="w", padx=16, pady=4)

        row_ext_btns = ctk.CTkFrame(card_ext, fg_color="transparent")
        row_ext_btns.pack(fill="x", padx=16, pady=(4, 14))

        btn_open_ext_dir = ctk.CTkButton(
            row_ext_btns, text="Open Extension Folder in Explorer",
            fg_color="#334155", hover_color="#475569", command=self._open_ext_folder
        )
        btn_open_ext_dir.pack(side="left")

        # 5. Save Button
        self.btn_save = ctk.CTkButton(
            self, text="Save All Settings", height=42, font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#10b981", hover_color="#059669", command=self._save_settings
        )
        self.btn_save.pack(fill="x", padx=15, pady=(15, 25))

    def _load_values(self):
        self.entry_url.insert(0, config.get("lm_studio_url", "http://localhost:1234/v1"))
        self.entry_model.insert(0, config.get("lm_studio_model", ""))
        self.var_auto_enabled.set(config.get("auto_analyze_enabled", False))
        self.entry_time.insert(0, config.get("auto_analyze_time", "18:00"))

        dirs = config.get("watched_directories", [])
        self.txt_dirs.delete("1.0", "end")
        self.txt_dirs.insert("end", "\n".join(dirs))

    def _add_directory(self):
        chosen = filedialog.askdirectory(title="Select Folder to Watch for Excel Spreadsheets")
        if chosen:
            current = self.txt_dirs.get("1.0", "end").strip()
            dirs = [d for d in current.splitlines() if d]
            if chosen not in dirs:
                dirs.append(chosen)
                self.txt_dirs.delete("1.0", "end")
                self.txt_dirs.insert("end", "\n".join(dirs))

    def _open_ext_folder(self):
        ext_path = BASE_DIR / "browser_extension"
        try:
            os.startfile(str(ext_path))
        except Exception as e:
            messagebox.showerror("Error", f"Could not open directory: {e}")

    def _test_connection(self):
        url = self.entry_url.get().strip()
        self.lbl_test_result.configure(text="Connecting to LM Studio...", text_color="#fbbf24")

        def worker():
            client = GemmaClient(base_url=url)
            success, msg, models = client.test_connection()

            def update_ui():
                if success:
                    self.lbl_test_result.configure(text=f"✓ Connected! Found {len(models)} model(s).", text_color="#34d399")
                    if models and not self.entry_model.get().strip():
                        # Fill first model
                        self.entry_model.delete(0, "end")
                        self.entry_model.insert(0, models[0])
                else:
                    self.lbl_test_result.configure(text="✗ Connection failed.", text_color="#f87171")
                    messagebox.showerror("Connection Failed", msg)

            self.after(0, update_ui)

        threading.Thread(target=worker, daemon=True).start()

    def _detect_models(self):
        url = self.entry_url.get().strip()
        client = GemmaClient(base_url=url)
        success, msg, models = client.test_connection()
        if success and models:
            self.entry_model.delete(0, "end")
            self.entry_model.insert(0, models[0])
            messagebox.showinfo("Model Detected", f"Auto-selected model: {models[0]}\nAll available: {', '.join(models)}")
        else:
            messagebox.showwarning("Model Detection", msg)

    def _save_settings(self):
        url = self.entry_url.get().strip()
        model = self.entry_model.get().strip()
        auto_enabled = self.var_auto_enabled.get()
        auto_time = self.entry_time.get().strip() or "18:00"

        dirs_raw = self.txt_dirs.get("1.0", "end").strip()
        watched_dirs = [d.strip() for d in dirs_raw.splitlines() if d.strip()]

        config.set("lm_studio_url", url)
        config.set("lm_studio_model", model)
        config.set("auto_analyze_enabled", auto_enabled)
        config.set("auto_analyze_time", auto_time)
        config.set("watched_directories", watched_dirs)

        self.gemma_client.base_url = url
        self.gemma_client.model_name = model

        messagebox.showinfo("Saved", "Settings updated successfully!")
