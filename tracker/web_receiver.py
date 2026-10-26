import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from tracker.logger import logger
from config import config

class WebReceiverHandler(BaseHTTPRequestHandler):
    def _set_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/status":
            self.send_response(200)
            self._set_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {"status": "ok", "service": "AutoTimeSeriesTracker", "active": True}
            self.wfile.write(json.dumps(response).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/event":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")

            try:
                data = json.loads(body)
                event_type = data.get("type", "WEB_EVENT")
                details = data.get("details", {})
                duration = data.get("duration_seconds")

                # Validate & sanitize event types
                if event_type in ["WEB_VISIT", "WEB_FORM", "WEBMAIL_SENT"]:
                    logger.log_event(event_type, details, duration_seconds=duration)
                    self.send_response(200)
                    self._set_cors_headers()
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
                else:
                    self.send_response(400)
                    self.end_headers()
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                print(f"[WebReceiver] Error processing event: {e}")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Silence default HTTP server console noise
        return


class WebReceiverServer:
    def __init__(self, port=None):
        self.port = port or config.get("web_receiver_port", 58432)
        self.server = None
        self._thread = None

    def start(self):
        try:
            self.server = HTTPServer(("127.0.0.1", self.port), WebReceiverHandler)
            self._thread = threading.Thread(target=self.server.serve_forever, daemon=True, name="WebReceiverThread")
            self._thread.start()
            print(f"[WebReceiver] Listening on http://127.0.0.1:{self.port} for browser extension events.")
        except Exception as e:
            print(f"[WebReceiver] Failed to start HTTP server on port {self.port}: {e}")

    def stop(self):
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
            except Exception:
                pass
