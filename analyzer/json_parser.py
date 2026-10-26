import os
import re
import json
from pathlib import Path
from datetime import datetime, timedelta
from config import TIMESHEETS_DIR


def extract_json_string(text):
    """Extracts JSON substring from LLM response, stripping markdown fences and preambles."""
    if not text:
        return ""
    text = text.strip()

    # Look for ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Look for outermost opening { and closing }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end+1].strip()

    return text


def repair_json_string(json_str):
    """Attempts lightweight repairs on common LLM JSON syntax mistakes."""
    if not json_str:
        return "{}"

    # Strip JS/C-style comments
    json_str = re.sub(r"//.*?\n", "\n", json_str)
    json_str = re.sub(r"/\*[\s\S]*?\*/", "", json_str)

    # Remove trailing commas before } or ]
    json_str = re.sub(r",\s*([\]}])", r"\1", json_str)

    # Fix unquoted keys if simple (e.g. {date: "2026-10-26"})
    json_str = re.sub(r'(?<=[{,\s])([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'"\1":', json_str)

    return json_str


def parse_timesheet_json(raw_response_text, date_str=None):
    """
    Parses LLM response into validated timesheet dictionary.
    Returns (timesheet_dict, error_message).
    """
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    clean_text = extract_json_string(raw_response_text)
    repaired_text = repair_json_string(clean_text)

    try:
        data = json.loads(repaired_text)
    except Exception as e1:
        # Fallback repair: try fixing unescaped newlines in strings
        try:
            sanitized = re.sub(r'(?<!\\)\n', r'\\n', repaired_text)
            data = json.loads(sanitized)
        except Exception:
            return None, f"JSON parsing failed: {e1}\nSnippet: {clean_text[:250]}"

    # Validate essential schema fields
    if not isinstance(data, dict):
        return None, "Parsed JSON is not an object/dictionary."

    data["date"] = data.get("date", date_str)
    data["summary"] = data.get("summary", "Daily activities analyzed.")
    entries_raw = data.get("entries", [])
    if not isinstance(entries_raw, list) or len(entries_raw) == 0:
        return None, "JSON contains no 'entries' list or entries is empty."

    # Ensure each entry has required fields
    normalized_entries = []
    total_minutes = 0
    for idx, item in enumerate(entries_raw, start=1):
        if not isinstance(item, dict):
            continue
        try:
            duration_min = int(item.get("duration_minutes", 30))
        except (ValueError, TypeError):
            duration_min = 30
        total_minutes += duration_min

        entry = {
            "id": item.get("id", idx),
            "start_time": str(item.get("start_time", "09:00")),
            "end_time": str(item.get("end_time", "09:30")),
            "duration_minutes": duration_min,
            "project": str(item.get("project", "General Work")),
            "category": str(item.get("category", "General")),
            "activity": str(item.get("activity", "Computer activity recorded.")),
            "artifacts": item.get("artifacts", []) if isinstance(item.get("artifacts"), list) else []
        }
        normalized_entries.append(entry)

    if not normalized_entries:
        return None, "No valid entries could be parsed from JSON."

    data["entries"] = normalized_entries

    # Recalculate totals if missing or zero
    if "total_hours_tracked" not in data or not data["total_hours_tracked"]:
        data["total_hours_tracked"] = round(total_minutes / 60.0, 1)

    if "productive_hours" not in data or not data["productive_hours"]:
        data["productive_hours"] = data["total_hours_tracked"]

    # Ensure categories_summary is populated
    if "categories_summary" not in data or not data["categories_summary"]:
        cat_sums = {}
        for e in normalized_entries:
            c = e["category"]
            cat_sums[c] = round(cat_sums.get(c, 0) + (e["duration_minutes"] / 60.0), 1)
        data["categories_summary"] = cat_sums

    return data, None


def save_timesheet_to_file(timesheet_dict, date_str=None):
    """Saves timesheet dictionary to data/timesheets/timesheet_YYYY-MM-DD.json"""
    if not date_str:
        date_str = timesheet_dict.get("date", datetime.now().strftime("%Y-%m-%d"))

    TIMESHEETS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = TIMESHEETS_DIR / f"timesheet_{date_str}.json"
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(timesheet_dict, f, indent=2)
        return out_path
    except Exception as e:
        print(f"[JSON Parser] Error saving timesheet file: {e}")
        return None


def load_timesheet_from_file(date_str=None):
    """Loads existing timesheet JSON for given date."""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    path = TIMESHEETS_DIR / f"timesheet_{date_str}.json"
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def classify_event(event_type, details):
    """
    Classifies an activity log event into a timesheet category and project name.
    Returns: (category, project, activity_desc, artifact)
    """
    if event_type == "FILE_EXCEL":
        filename = details.get("filename", "")
        action = details.get("action", "EDITED")
        return (
            "Documentation & Excel",
            "Spreadsheet Management",
            f"Excel operation: {action} {filename}",
            filename
        )

    if event_type == "WEBMAIL_SENT":
        to_addr = details.get("to", "")
        subj = details.get("subject", "(No Subject)")
        return (
            "Communication & Email",
            "Client & Team Communications",
            f"Sent email to {to_addr}: {subj}",
            to_addr
        )

    if event_type == "WEB_FORM":
        form_name = details.get("form_name", "Web Form")
        url = details.get("url", "")
        return (
            "Admin & Forms",
            "Web Operations & Forms",
            f"Submitted online form: {form_name}",
            url
        )

    if event_type == "WEB_VISIT":
        title = details.get("title", "")
        url = details.get("url", "")
        lower_title = title.lower()
        if "mail" in lower_title or "inbox" in lower_title:
            return ("Communication & Email", "Email & Messaging", f"Webmail: {title}", url)
        if "form" in lower_title or "survey" in lower_title:
            return ("Admin & Forms", "Web Operations & Forms", f"Online Form: {title}", url)
        return ("Research & Web", "Web Research", f"Visited: {title}", url)

    if event_type == "WINDOW":
        app = details.get("app", "").lower()
        title = details.get("title", "")
        lower_title = title.lower()

        # Excel
        if "excel" in app or "excel" in lower_title or any(ext in lower_title for ext in [".xlsx", ".xls", ".csv"]):
            sheet_name = title.split(" - Excel")[0].strip() if " - Excel" in title else title
            return (
                "Documentation & Excel",
                "Spreadsheet Management",
                f"Worked on spreadsheet: {sheet_name}",
                sheet_name
            )

        # Chrome / Edge / Browsers
        if any(b in app for b in ["chrome", "msedge", "firefox", "brave", "opera"]):
            # Email in browser
            if any(k in lower_title for k in ["gmail", "outlook", "mail", "inbox", "sent mail"]):
                return (
                    "Communication & Email",
                    "Email & Communications",
                    f"Email correspondence: {title.replace(' - Google Chrome', '').replace(' - Microsoft Edge', '')}",
                    "Webmail"
                )
            # Forms in browser
            if any(k in lower_title for k in ["forms", "google forms", "portal", "survey", "questionnaire"]):
                clean_title = title.replace(" - Google Chrome", "").replace(" - Google Forms", "")
                return (
                    "Admin & Forms",
                    "Web Operations & Forms",
                    f"Filled/managed online form: {clean_title}",
                    clean_title
                )
            # AI & Research in browser
            if any(k in lower_title for k in ["chatgpt", "claude", "gemini", "search", "stackoverflow", "github", "documentation", "shopping", "setup"]):
                clean_title = title.replace(" - Google Chrome", "")
                return (
                    "Research & Web",
                    "Online Research & AI Tools",
                    f"Web research: {clean_title}",
                    clean_title
                )
            return (
                "Research & Web",
                "Web Browsing",
                f"Browser activity: {title.replace(' - Google Chrome', '')}",
                None
            )

        # Development tools
        if any(dev in app for dev in ["code.exe", "pycharm", "idea", "antigravity", "devenv", "python", "cmd.exe", "powershell", "lm studio"]):
            if "lm studio" in app or "lm studio" in lower_title:
                return ("Development", "Local AI & Model Setup", "Configuring local LLM in LM Studio", "LM Studio")
            if "antigravity" in app or "antigravity" in lower_title:
                return ("Development", "Software Development", f"Coding in IDE: {title.split(' - ')[0]}", None)
            return ("Development", "Software Development", f"Development activity ({app}): {title}", None)

        # General desktop app
        return ("General", "Desktop Operations", f"Desktop activity ({app}): {title}", None)

    return ("General", "General Operations", f"Activity: {event_type}", None)


def generate_fallback_timesheet(raw_log_text, date_str=None):
    """
    Comprehensive rule-based timesheet generator used if LM Studio / Gemma is offline or fails.
    Accurately parses Excel file events, web forms, emails, and active window events,
    calculating real start/end timestamps and grouping activities into distinct tasks.
    """
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    lines = raw_log_text.strip().splitlines()
    if not lines:
        return {
            "date": date_str,
            "summary": "No activity recorded for this date.",
            "total_hours_tracked": 0.0,
            "productive_hours": 0.0,
            "categories_summary": {},
            "entries": []
        }

    # Parse raw events
    parsed_events = []
    excel_files_seen = set()

    for line in lines:
        # Match timestamp: [YYYY-MM-DD HH:MM:SS]
        ts_match = re.match(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]\s*\[(\w+)\]\s*(.*)", line)
        if not ts_match:
            continue

        ts_str, etype, rest = ts_match.groups()
        try:
            dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
        except Exception:
            continue

        duration_sec = 0
        dur_m = re.search(r"Duration:\s*(\d+)s", rest)
        if dur_m:
            duration_sec = int(dur_m.group(1))

        details = {}
        if etype == "FILE_EXCEL":
            file_m = re.search(r"File:\s*([^|\r\n]+?)\s*(?:\||$)", rest)
            action_m = re.search(r"Action:\s*([^|\r\n]+?)\s*(?:\||$)", rest)
            if file_m:
                fname = file_m.group(1).strip()
                act = action_m.group(1).strip() if action_m else "MODIFIED"
                details = {"filename": fname, "action": act}
                excel_files_seen.add(fname)
        elif etype == "WINDOW":
            app_m = re.search(r"App:\s*([^|\r\n]+?)\s*(?:\||$)", rest)
            title_m = re.search(r"Title:\s*([^|\r\n]+?)\s*(?:\|Duration:|$)", rest)
            app = app_m.group(1).strip() if app_m else "Unknown"
            title = title_m.group(1).strip() if title_m else ""
            details = {"app": app, "title": title}
        elif etype == "WEBMAIL_SENT":
            to_m = re.search(r"To:\s*([^|\r\n]+?)\s*(?:\||$)", rest)
            subj_m = re.search(r"Subject:\s*(.*)", rest)
            details = {
                "to": to_m.group(1).strip() if to_m else "Unknown",
                "subject": subj_m.group(1).strip() if subj_m else "(No Subject)"
            }
        elif etype == "WEB_FORM":
            url_m = re.search(r"URL:\s*([^|\r\n]+?)\s*(?:\||$)", rest)
            form_m = re.search(r"Form:\s*([^|\r\n]+?)\s*(?:\||$)", rest)
            details = {
                "url": url_m.group(1).strip() if url_m else "",
                "form_name": form_m.group(1).strip() if form_m else "Web Form"
            }
        elif etype == "WEB_VISIT":
            url_m = re.search(r"URL:\s*([^|\r\n]+?)\s*(?:\||$)", rest)
            title_m = re.search(r"Title:\s*([^|\r\n]+?)\s*(?:\||$)", rest)
            details = {
                "url": url_m.group(1).strip() if url_m else "",
                "title": title_m.group(1).strip() if title_m else "Webpage"
            }
        else:
            continue

        cat, proj, desc, artifact = classify_event(etype, details)
        parsed_events.append({
            "datetime": dt,
            "etype": etype,
            "duration_sec": max(duration_sec, 3),
            "category": cat,
            "project": proj,
            "description": desc,
            "artifact": artifact
        })

    if not parsed_events:
        return {
            "date": date_str,
            "summary": "No identifiable tasks found in activity log.",
            "total_hours_tracked": 0.0,
            "productive_hours": 0.0,
            "categories_summary": {},
            "entries": []
        }

    # Group into sessions by (category, project)
    # A new session begins if the category/project changes or if idle gap > 20 minutes
    sessions = []
    current_session = None

    for ev in parsed_events:
        # Ignore system desktop flickers under 4s unless it has an artifact
        if ev["duration_sec"] < 4 and not ev["artifact"] and ev["category"] == "General":
            continue

        key = (ev["category"], ev["project"])

        if current_session is None:
            current_session = {
                "category": ev["category"],
                "project": ev["project"],
                "start_dt": ev["datetime"],
                "end_dt": ev["datetime"] + timedelta(seconds=ev["duration_sec"]),
                "total_sec": ev["duration_sec"],
                "descriptions": [ev["description"]],
                "artifacts": [ev["artifact"]] if ev["artifact"] else []
            }
        else:
            gap = (ev["datetime"] - current_session["end_dt"]).total_seconds()
            same_group = (current_session["category"] == ev["category"])

            if same_group and gap < 1200:  # Within 20 minutes of same category
                # Extend current session
                current_session["end_dt"] = max(current_session["end_dt"], ev["datetime"] + timedelta(seconds=ev["duration_sec"]))
                current_session["total_sec"] += ev["duration_sec"]
                if ev["description"] not in current_session["descriptions"]:
                    current_session["descriptions"].append(ev["description"])
                if ev["artifact"] and ev["artifact"] not in current_session["artifacts"]:
                    current_session["artifacts"].append(ev["artifact"])
            else:
                # Flush current session and start new
                sessions.append(current_session)
                current_session = {
                    "category": ev["category"],
                    "project": ev["project"],
                    "start_dt": ev["datetime"],
                    "end_dt": ev["datetime"] + timedelta(seconds=ev["duration_sec"]),
                    "total_sec": ev["duration_sec"],
                    "descriptions": [ev["description"]],
                    "artifacts": [ev["artifact"]] if ev["artifact"] else []
                }

    if current_session:
        sessions.append(current_session)

    # Filter out empty or trivial sessions (< 10 seconds and no artifacts)
    filtered_sessions = [s for s in sessions if s["total_sec"] >= 15 or len(s["artifacts"]) > 0]
    if not filtered_sessions:
        filtered_sessions = sessions

    # Convert sessions to final timesheet entries
    entries = []
    total_minutes = 0

    for idx, s in enumerate(filtered_sessions, start=1):
        # Calculate duration in minutes (round up to at least 5 minutes for timesheet readability)
        span_minutes = max(5, int((s["end_dt"] - s["start_dt"]).total_seconds() / 60.0))
        total_minutes += span_minutes

        start_time_str = s["start_dt"].strftime("%H:%M")
        end_time_str = s["end_dt"].strftime("%H:%M")
        if start_time_str == end_time_str:
            end_time_str = (s["start_dt"] + timedelta(minutes=span_minutes)).strftime("%H:%M")

        # Pick the most informative description
        desc_list = s["descriptions"]
        if len(desc_list) == 1:
            activity_summary = desc_list[0]
        else:
            activity_summary = "; ".join(desc_list[:3])

        entries.append({
            "id": idx,
            "start_time": start_time_str,
            "end_time": end_time_str,
            "duration_minutes": span_minutes,
            "project": s["project"],
            "category": s["category"],
            "activity": activity_summary,
            "artifacts": s["artifacts"][:5]
        })

    total_hours = round(total_minutes / 60.0, 1)

    # Category summaries
    cat_summary = {}
    for e in entries:
        c = e["category"]
        cat_summary[c] = round(cat_summary.get(c, 0) + (e["duration_minutes"] / 60.0), 1)

    distinct_projects = list(dict.fromkeys([e["project"] for e in entries]))
    summary_text = (
        f"Timesheet analyzed from daily activity logs ({len(entries)} tasks across {len(distinct_projects)} areas: "
        f"{', '.join(distinct_projects[:3])})."
    )

    return {
        "date": date_str,
        "summary": summary_text,
        "total_hours_tracked": total_hours,
        "productive_hours": total_hours,
        "categories_summary": cat_summary,
        "entries": entries
    }
