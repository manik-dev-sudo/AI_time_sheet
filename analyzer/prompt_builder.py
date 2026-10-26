"""
prompt_builder.py
Builds the structured prompt sent to the local Gemma LLM.
"""
from datetime import datetime
from pathlib import Path


def _load_log(date_str: str) -> str:
    """Read the raw activity log for a given date."""
    log_path = Path(__file__).resolve().parent.parent / "data" / "logs" / f"activity_{date_str}.txt"
    if log_path.exists():
        return log_path.read_text(encoding="utf-8", errors="ignore")
    return ""


def build_gemma_prompt(date_str: str, raw_log_text: str) -> tuple[str, str]:
    """
    Returns (system_prompt, user_prompt) for the timesheet generation task.
    The caller may combine them into one message for Gemma compatibility.
    """
    system_prompt = (
        "You are an expert productivity analyst and timesheet generator.\n"
        "Your job is to read a raw computer activity log and produce a structured JSON timesheet.\n\n"
        "RULES:\n"
        "1. Create ONE separate entry for EACH distinct type of work (email, Excel, browsing, forms, etc.).\n"
        "2. Do NOT merge different activities into one block.\n"
        "3. Classify entries using ONLY these categories:\n"
        "   - 'Communication & Email'  (Gmail, Outlook, email apps)\n"
        "   - 'Documentation & Excel'  (Excel, CSV, spreadsheet files)\n"
        "   - 'Admin & Forms'          (Google Forms, web forms, portals)\n"
        "   - 'Research & Web'         (browsing, ChatGPT, search engines)\n"
        "   - 'Development'            (IDE, LM Studio, code editors, terminals)\n"
        "   - 'Other'                  (anything that doesn't fit above)\n"
        "4. Use REAL timestamps from the log for start_time and end_time (HH:MM format).\n"
        "5. Include only windows with duration >= 5 seconds.\n"
        "6. Skip system/idle entries (Auto Timesheet Desktop, Taskbar, Desktop, Search).\n"
        "7. List specific file names, URLs, or email subjects in the 'artifacts' array.\n\n"
        "OUTPUT FORMAT (strict JSON, no markdown, no explanation, no trailing commas):\n"
        "{\n"
        '  "date": "YYYY-MM-DD",\n'
        '  "summary": "One sentence summary of the day.",\n'
        '  "total_hours_tracked": 0.0,\n'
        '  "entries": [\n'
        "    {\n"
        '      "id": 1,\n'
        '      "start_time": "HH:MM",\n'
        '      "end_time": "HH:MM",\n'
        '      "duration_minutes": 0,\n'
        '      "project": "Short project name",\n'
        '      "category": "Category from the list above",\n'
        '      "activity": "Describe what was done.",\n'
        '      "artifacts": ["filename.xlsx", "subject line", "URL"]\n'
        "    }\n"
        "  ],\n"
        '  "categories_summary": {\n'
        '    "Communication & Email": 0.0,\n'
        '    "Documentation & Excel": 0.0,\n'
        '    "Admin & Forms": 0.0,\n'
        '    "Research & Web": 0.0,\n'
        '    "Development": 0.0,\n'
        '    "Other": 0.0\n'
        "  }\n"
        "}"
    )

    user_prompt = (
        f"Generate a timesheet for {date_str}.\n\n"
        f"RAW ACTIVITY LOG:\n"
        f"{'=' * 60}\n"
        f"{raw_log_text.strip()}\n"
        f"{'=' * 60}\n\n"
        "Return ONLY the JSON timesheet. No explanation, no markdown code fences."
    )

    return system_prompt, user_prompt


def build_combined_gemma_prompt(date_str: str, raw_log_text: str) -> str:
    """
    Single combined prompt for Gemma models that don't support system role.
    Merges system instruction and user task into one user message.
    """
    sys_prompt, user_prompt = build_gemma_prompt(date_str, raw_log_text)
    return (
        f"{sys_prompt}\n\n"
        "========================================\n"
        f"TASK:\n{user_prompt}"
    )


def get_log_for_date(date_str: str) -> str:
    """Public helper: load the raw activity log text for a given YYYY-MM-DD date."""
    return _load_log(date_str)
