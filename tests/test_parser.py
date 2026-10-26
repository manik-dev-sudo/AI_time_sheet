import os
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analyzer.prompt_builder import build_gemma_prompt
from analyzer.json_parser import parse_timesheet_json, generate_fallback_timesheet


class TestTimesheetLogic(unittest.TestCase):
    def setUp(self):
        self.sample_log = """[2026-10-26 09:00:15] [WINDOW] App: excel.exe | Title: Q3_Revenue_Forecast.xlsx | Duration: 1800s
[2026-10-26 09:30:20] [FILE_EXCEL] Action: MODIFIED | File: Q3_Revenue_Forecast.xlsx | Path: C:\\Users\\DemoUser\\Desktop
[2026-10-26 10:15:00] [WEB_VISIT] Title: Vendor Portal Invoices | URL: https://vendor.portal.com/invoices
[2026-10-26 10:18:30] [WEB_FORM] URL: https://vendor.portal.com/invoices | Form: invoice_upload_form | Fields Filled: [invoice_number, amount, department]
[2026-10-26 11:30:00] [WEBMAIL_SENT] Service: Gmail | To: accounting@company.com | Subject: Invoices for Q3 Review
[2026-10-26 12:00:00] [SYSTEM] User is IDLE (no input for 320s). Tracking paused.
"""

    def test_prompt_builder(self):
        sys_prompt, user_prompt = build_gemma_prompt("2026-10-26", self.sample_log)
        self.assertIn("Q3_Revenue_Forecast.xlsx", user_prompt)
        self.assertIn("accounting@company.com", user_prompt)
        self.assertIn("invoice_upload_form", user_prompt)
        self.assertIn("JSON", sys_prompt)

    def test_json_parser_clean(self):
        raw_llm_output = """```json
{
  "date": "2026-10-26",
  "summary": "Completed financial forecast model and submitted vendor invoices.",
  "total_hours_tracked": 3.0,
  "productive_hours": 2.8,
  "categories_summary": {
    "Documentation & Excel": 1.5,
    "Admin & Forms": 0.5,
    "Communication & Email": 0.8
  },
  "entries": [
    {
      "id": 1,
      "start_time": "09:00",
      "end_time": "10:30",
      "duration_minutes": 90,
      "project": "Finance",
      "category": "Documentation & Excel",
      "activity": "Edited Q3 Revenue Forecast spreadsheet",
      "artifacts": ["Q3_Revenue_Forecast.xlsx"]
    }
  ]
}
```"""
        data, err = parse_timesheet_json(raw_llm_output, "2026-10-26")
        self.assertIsNone(err)
        self.assertIsNotNone(data)
        self.assertEqual(data["date"], "2026-10-26")
        self.assertEqual(len(data["entries"]), 1)
        self.assertEqual(data["entries"][0]["project"], "Finance")

    def test_fallback_generator(self):
        fallback = generate_fallback_timesheet(self.sample_log, "2026-10-26")
        self.assertEqual(fallback["date"], "2026-10-26")
        self.assertTrue(len(fallback["entries"]) >= 3)
        categories = [e["category"] for e in fallback["entries"]]
        self.assertIn("Documentation & Excel", categories)
        self.assertIn("Admin & Forms", categories)
        self.assertIn("Communication & Email", categories)

    def test_fallback_with_window_logs_and_spaces_in_filename(self):
        real_user_log = """[2026-10-26 06:37:01] [WINDOW] App: chrome.exe | Title: Inbox (78) - demo.user@example.com - Gmail - Google Chrome | Duration: 144s
[2026-10-26 06:38:35] [WINDOW] App: EXCEL.EXE | Title: PERSONAL (version 1) - Excel | Duration: 15s
[2026-10-26 06:39:09] [FILE_EXCEL] Action: MODIFIED | File: first book to write.xlsx | Path: C:\\Users\\DemoUser\\Documents
[2026-10-26 06:40:59] [WINDOW] App: EXCEL.EXE | Title: first book to write - Excel | Duration: 108s
[2026-10-26 06:42:20] [WINDOW] App: chrome.exe | Title: Untitled form - Google Forms - Google Chrome | Duration: 18s
[2026-10-26 06:45:59] [WINDOW] App: chrome.exe | Title: ChatGPT - Google Chrome | Duration: 54s
[2026-10-26 06:48:53] [WINDOW] App: LM Studio.exe | Title: LM Studio | Duration: 108s
"""
        fallback = generate_fallback_timesheet(real_user_log, "2026-10-26")
        self.assertEqual(fallback["date"], "2026-10-26")
        self.assertTrue(len(fallback["entries"]) >= 4, f"Expected at least 4 distinct tasks, got {len(fallback['entries'])}")

        categories = [e["category"] for e in fallback["entries"]]
        self.assertIn("Communication & Email", categories)
        self.assertIn("Documentation & Excel", categories)
        self.assertIn("Admin & Forms", categories)
        self.assertIn("Research & Web", categories)

        # Check full filename was preserved (not chopped to 'first')
        excel_entry = next(e for e in fallback["entries"] if e["category"] == "Documentation & Excel")
        self.assertIn("first book to write.xlsx", excel_entry["artifacts"])


if __name__ == "__main__":
    unittest.main()
