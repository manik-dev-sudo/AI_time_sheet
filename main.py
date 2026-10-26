import sys
import argparse
from pathlib import Path

def check_dependencies():
    missing = []
    try:
        import requests
    except ImportError:
        missing.append("requests")
    try:
        import customtkinter
    except ImportError:
        missing.append("customtkinter")
    try:
        import watchdog
    except ImportError:
        missing.append("watchdog")

    if missing:
        print("=" * 60)
        print("NOTICE: Some optional dependencies are missing:")
        for m in missing:
            print(f"  - {m}")
        print("\nTo install all dependencies, run:")
        print("  pip install -r requirements.txt")
        print("=" * 60)

def main():
    parser = argparse.ArgumentParser(description="Auto Timesheet Desktop Tracker & Gemma Analyzer")
    parser.add_argument("--headless", action="store_true", help="Run background activity capture only without desktop GUI")
    parser.add_argument("--analyze", action="store_true", help="Analyze today's activity log using Gemma and exit")
    parser.add_argument("--date", type=str, default=None, help="Date to analyze (YYYY-MM-DD)")
    args = parser.parse_args()

    check_dependencies()

    if args.analyze:
        from tracker.logger import logger
        from analyzer.gemma_client import GemmaClient
        date_str = args.date or logger.get_today_str()
        log_text = logger.read_log_text(date_str)
        if not log_text.strip():
            print(f"No activity log found for {date_str}.")
            return

        print(f"Connecting to LM Studio to analyze log for {date_str}...")
        client = GemmaClient()
        timesheet, msg = client.analyze_daily_log(date_str, log_text)
        print(msg)
        if timesheet:
            import json
            print(json.dumps(timesheet, indent=2))
        return

    if args.headless:
        import time
        from tracker.activity_manager import ActivityManager
        print("Starting Auto Timesheet tracker in headless daemon mode. Press Ctrl+C to stop.")
        manager = ActivityManager()
        manager.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping tracker...")
            manager.stop()
        return

    # Start Modern Desktop GUI
    try:
        from ui.app import MainApp
        app = MainApp()
        app.mainloop()
    except Exception as e:
        print(f"Error launching desktop GUI: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
