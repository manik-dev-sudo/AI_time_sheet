import json
from pathlib import Path
from datetime import datetime
import requests
from config import config, LOGS_DIR
from analyzer.prompt_builder import build_gemma_prompt, build_combined_gemma_prompt
from analyzer.json_parser import parse_timesheet_json, save_timesheet_to_file, generate_fallback_timesheet


class GemmaClient:
    def __init__(self, base_url=None, model_name=None):
        self.base_url = (base_url or config.get("lm_studio_url", "http://localhost:1234/v1")).rstrip("/")
        self.model_name = model_name or config.get("lm_studio_model", "")

    def _write_debug_log(self, text):
        try:
            debug_path = LOGS_DIR / "llm_debug.log"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(debug_path, "a", encoding="utf-8") as f:
                f.write(f"\n--- [{timestamp}] ---\n{text}\n")
        except Exception:
            pass

    def test_connection(self):
        """
        Tests connection to LM Studio and discovers loaded models.
        Returns: (success: bool, message: str, models: list)
        """
        try:
            url = f"{self.base_url}/models"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("id") for m in data.get("data", []) if "id" in m]
                if models:
                    msg = f"Connected to LM Studio! Available model(s): {', '.join(models)}"
                    return True, msg, models
                else:
                    return True, "Connected to LM Studio, but no model is currently loaded. Please load a model in LM Studio.", []
            else:
                return False, f"LM Studio responded with HTTP {resp.status_code}: {resp.text}", []
        except requests.exceptions.ConnectionError:
            return False, f"Cannot connect to LM Studio at {self.base_url}. Ensure LM Studio local server is started (port 1234).", []
        except Exception as e:
            return False, f"Connection error: {e}", []

    def get_effective_model(self):
        """Discovers current active model from LM Studio if not explicitly set."""
        if self.model_name:
            return self.model_name

        success, _, models = self.test_connection()
        if success and models:
            for m in models:
                if "gemma" in m.lower():
                    return m
            return models[0]
        return "gemma"

    def analyze_daily_log(self, date_str, raw_log_text, use_fallback_on_error=True):
        """
        Sends the daily activity log to local Gemma via LM Studio API.
        If LM Studio is unreachable or output cannot be parsed, falls back to
        the comprehensive rule-based activity log parser.
        Returns: (timesheet_dict, status_message)
        """
        if not raw_log_text.strip():
            return None, "Raw log is empty. No activity recorded for this day."

        model = self.get_effective_model()
        url = f"{self.base_url}/chat/completions"

        # Prepare prompts
        # For maximum compatibility with Gemma models (which do not support a 'system' role),
        # we format system instructions and user task into a single user message.
        combined_prompt = build_combined_gemma_prompt(date_str, raw_log_text)

        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": combined_prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 3000,
        }

        self._write_debug_log(f"REQUEST URL: {url}\nMODEL: {model}\nPROMPT LENGTH: {len(combined_prompt)} chars")

        try:
            print(f"[GemmaClient] Sending request to {url} with model '{model}'...")
            resp = requests.post(url, json=payload, timeout=120)

            # If HTTP 400 (e.g. system role or format error), retry with split messages if needed
            if resp.status_code != 200:
                self._write_debug_log(f"HTTP ERROR {resp.status_code}: {resp.text}")
                # Try fallback or split messages
                system_prompt, user_prompt = build_gemma_prompt(date_str, raw_log_text)
                retry_payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 3000
                }
                retry_resp = requests.post(url, json=retry_payload, timeout=90)
                if retry_resp.status_code == 200:
                    resp = retry_resp

            if resp.status_code == 200:
                res_data = resp.json()
                content = res_data["choices"][0]["message"]["content"]
                self._write_debug_log(f"RESPONSE CONTENT ({len(content)} chars):\n{content}")

                parsed_data, err = parse_timesheet_json(content, date_str)

                if parsed_data:
                    parsed_data["_generated_by"] = f"Gemma ({model})"
                    saved_path = save_timesheet_to_file(parsed_data, date_str)
                    return parsed_data, f"Timesheet successfully generated by Gemma ({model}) and saved to {saved_path.name}"
                else:
                    self._write_debug_log(f"PARSER ERROR: {err}\nRAW RESPONSE:\n{content}")
                    if use_fallback_on_error:
                        fallback = generate_fallback_timesheet(raw_log_text, date_str)
                        fallback["_generated_by"] = f"Smart Heuristic (Gemma output formatting error: {err[:80]})"
                        save_timesheet_to_file(fallback, date_str)
                        return fallback, f"Gemma response could not be parsed as valid JSON ({err}). Generated smart timesheet from activity log."
                    return None, f"Failed to parse Gemma output: {err}"
            else:
                err_msg = f"LM Studio API returned HTTP {resp.status_code}: {resp.text[:150]}"
                print(f"[GemmaClient] {err_msg}")
                self._write_debug_log(f"FAILED: {err_msg}")
                if use_fallback_on_error:
                    fallback = generate_fallback_timesheet(raw_log_text, date_str)
                    fallback["_generated_by"] = f"Smart Heuristic (LM Studio HTTP {resp.status_code})"
                    save_timesheet_to_file(fallback, date_str)
                    return fallback, f"LM Studio error ({resp.status_code}). Generated timesheet via smart activity log parser."
                return None, err_msg

        except requests.exceptions.ConnectionError:
            err_msg = f"Could not connect to LM Studio at {self.base_url}. Is LM Studio server running?"
            print(f"[GemmaClient] {err_msg}")
            self._write_debug_log(f"CONNECTION ERROR: {err_msg}")
            if use_fallback_on_error:
                fallback = generate_fallback_timesheet(raw_log_text, date_str)
                fallback["_generated_by"] = "Smart Heuristic (LM Studio not connected)"
                save_timesheet_to_file(fallback, date_str)
                return fallback, "LM Studio is offline. Generated timesheet from activity logs using smart parser."
            return None, err_msg

        except Exception as e:
            err_msg = f"Unexpected error during Gemma analysis: {e}"
            print(f"[GemmaClient] {err_msg}")
            self._write_debug_log(f"EXCEPTION: {err_msg}")
            if use_fallback_on_error:
                fallback = generate_fallback_timesheet(raw_log_text, date_str)
                fallback["_generated_by"] = f"Smart Heuristic (Exception: {str(e)[:60]})"
                save_timesheet_to_file(fallback, date_str)
                return fallback, f"Analysis error ({e}). Generated timesheet from activity log."
            return None, err_msg
