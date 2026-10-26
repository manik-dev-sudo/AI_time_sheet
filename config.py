import os
import json
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = DATA_DIR / "logs"
TIMESHEETS_DIR = DATA_DIR / "timesheets"
SETTINGS_FILE = DATA_DIR / "settings.json"

for d in [DATA_DIR, LOGS_DIR, TIMESHEETS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Default Watched Paths (Common places user works on Excel sheets)
DEFAULT_WATCH_PATHS = [
    str(Path.home() / "Desktop"),
    str(Path.home() / "Documents"),
    str(Path.home() / "Downloads"),
]

DEFAULT_SETTINGS = {
    "lm_studio_url": "http://localhost:1234/v1",
    "lm_studio_model": "gemma",  # Will auto-detect or match available model
    "auto_analyze_time": "18:00",  # 6:00 PM
    "auto_analyze_enabled": False,
    "web_receiver_port": 58432,
    "idle_threshold_seconds": 300,  # 5 min idle window
    "poll_interval_seconds": 3,
    "watched_directories": [p for p in DEFAULT_WATCH_PATHS if os.path.exists(p)],
    "track_excel_extensions": [".xlsx", ".xls", ".csv", ".xlsm"],
    "filter_system_apps": True,
    "theme": "dark",
}

class ConfigManager:
    def __init__(self, settings_path=SETTINGS_FILE):
        self.settings_path = Path(settings_path)
        self.settings = self.load_settings()

    def load_settings(self):
        if self.settings_path.exists():
            try:
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    # Merge defaults with saved settings for any missing keys
                    merged = DEFAULT_SETTINGS.copy()
                    merged.update(saved)
                    return merged
            except Exception as e:
                print(f"[Config] Error loading settings: {e}. Using defaults.")
        return DEFAULT_SETTINGS.copy()

    def save_settings(self, new_settings=None):
        if new_settings:
            self.settings.update(new_settings)
        try:
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
            return True
        except Exception as e:
            print(f"[Config] Error saving settings: {e}")
            return False

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self.save_settings()

# Global singleton config
config = ConfigManager()
