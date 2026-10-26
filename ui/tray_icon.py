import threading
from pathlib import Path

class TrayManager:
    def __init__(self, app_window, on_show, on_toggle_track, on_analyze, on_exit):
        self.app_window = app_window
        self.on_show = on_show
        self.on_toggle_track = on_toggle_track
        self.on_analyze = on_analyze
        self.on_exit = on_exit
        self.icon = None
        self._thread = None

    def create_tray_image(self):
        """Creates a modern circular clock/timesheet icon in PIL."""
        try:
            from PIL import Image, ImageDraw
            img = Image.new("RGBA", (64, 64), color=(0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            # Draw rounded circular badge
            draw.ellipse((4, 4, 60, 60), fill="#6366f1", outline="#4338ca", width=2)
            # Clock hands
            draw.line((32, 32, 32, 14), fill="#ffffff", width=4)
            draw.line((32, 32, 46, 32), fill="#ffffff", width=3)
            # Center pin
            draw.ellipse((28, 28, 36, 36), fill="#ffffff")
            return img
        except ImportError:
            return None

    def start(self):
        try:
            import pystray
            image = self.create_tray_image()
            if not image:
                return

            menu = pystray.Menu(
                pystray.MenuItem("Open Dashboard", lambda: self.on_show()),
                pystray.MenuItem("Toggle Pause/Resume", lambda: self.on_toggle_track()),
                pystray.MenuItem("Analyze Today's Timesheet", lambda: self.on_analyze()),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Exit Application", lambda: self.on_exit())
            )

            self.icon = pystray.Icon("AutoTimeSeries", image, "Auto Timesheet Tracker", menu)
            self._thread = threading.Thread(target=self.icon.run, daemon=True, name="TrayIconThread")
            self._thread.start()
        except ImportError:
            print("[TrayManager] pystray or Pillow not installed. Running without system tray.")
        except Exception as e:
            print(f"[TrayManager] Error starting system tray: {e}")

    def stop(self):
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass
