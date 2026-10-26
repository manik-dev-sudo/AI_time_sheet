# Auto Timesheet Desktop — Powered by Local Gemma & LM Studio

An intelligent desktop application that runs silently in the background, tracks your work activities (active windows, Excel sheet modifications, web form submissions, and sent emails), and uses a **locally hosted Gemma LLM via LM Studio** to generate structured, professional daily timesheets.

---

## Key Features

1. **Background Process & Activity Tracking**:
   - **Active Window & Focus Monitoring**: Records active applications, document titles, and time spent. Detects idle periods (>5 minutes) and pauses tracking automatically.
   - **Excel Spreadsheet Operations**: Automatically tracks `.xlsx`, `.xls`, `.csv`, and `.xlsm` files when they are **Created**, **Edited (Modified)**, **Renamed**, or **Deleted** across Desktop, Documents, Downloads, or custom directories.
   - **Web Activity & Form Submissions**: Lightweight companion browser extension captures visited URLs and form submissions (e.g. invoice forms, portal submissions, masking sensitive inputs).
   - **Webmail Sent Tracking**: Captures outgoing emails on **Gmail** and **Outlook Web**, recording recipients (`To:`, `Cc:`) and subjects.
   - **Local Daily Log (`activity_YYYY-MM-DD.txt`)**: All raw activities are recorded locally with timestamps.

2. **End-of-Day Gemma Analysis (via LM Studio)**:
   - Connects to LM Studio's local OpenAI-compatible endpoint (`http://localhost:1234/v1`).
   - Automatically discovers the loaded Gemma model (`gemma-2-9b-it`, `gemma-2-2b-it`, etc.).
   - Analyzes daily raw logs and outputs a structured **JSON timesheet** with work blocks, categories, time spent, and artifacts.
   - Includes a smart offline heuristic fallback so timesheets are always generated even if LM Studio is offline.

3. **Modern Python Desktop GUI**:
   - Sleek dark theme built with rounded card layouts and category color-coding.
   - **Timesheet View**: Daily executive summary, category breakdown pills, interactive work session cards.
   - **Live Activity Feed**: Real-time event log stream with filtering by event type and Notepad launcher.
   - **Settings View**: LM Studio URL, model auto-discovery, auto-analysis trigger time, and watched folders.
   - **System Tray Support**: Minimize to Windows system tray to keep running silently in the background.
   - **Export Options**: Export to **Excel (`.xlsx`)**, **JSON**, or copy Markdown report to clipboard.

---

## Architecture & Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                   Background Activity Tracker               │
│  - WindowMonitor (ctypes Windows API + Idle detection)      │
│  - FileMonitor (Watchdog / polling for Excel modifications)  │
│  - WebReceiver (Port 58432 HTTP API for Browser Extension)  │
└──────────────────────────────┬──────────────────────────────┘
                               │ Writes timestamped events
                               ▼
            ┌──────────────────────────────────────┐
            │   data/logs/activity_YYYY-MM-DD.txt   │
            └──────────────────┬───────────────────┘
                               │ Analyzed at End of Day
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 LM Studio Local Server                      │
│             http://localhost:1234/v1/chat/completions       │
│                  (Running Local Gemma Model)                │
└──────────────────────────────┬──────────────────────────────┘
                               │ Returns structured JSON
                               ▼
            ┌──────────────────────────────────────┐
            │ data/timesheets/timesheet_YYYY-MM-DD.json │
            └──────────────────┬───────────────────┘
                               │ Display & Export
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     Desktop GUI (App)                       │
│  - Timesheet Cards & Category Breakdown                     │
│  - Export to Excel (.xlsx), JSON, or Markdown               │
│  - System Tray background minimize                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Getting Started

### 1. Install Python Dependencies

Open PowerShell or Command Prompt in this folder:
```powershell
pip install -r requirements.txt
```

### 2. Set Up LM Studio (Local Gemma Model)

1. Download and install [LM Studio](https://lmstudio.ai/).
2. In LM Studio, search and download any Gemma model (e.g. `gemma-2-9b-it` or `gemma-2-2b-it`).
3. Click the **Local Server** tab (double-arrow icon `<->` on the left).
4. Select the Gemma model and click **Start Server**.
5. The server will run at `http://localhost:1234/v1`.

### 3. (Optional) Load Companion Browser Extension

To track web form submissions and Gmail/Outlook sent emails:
1. Open Google Chrome or Microsoft Edge and go to `chrome://extensions` or `edge://extensions`.
2. Toggle on **Developer mode** (top right corner).
3. Click **Load unpacked**.
4. Select the `browser_extension` folder inside this project directory.
5. The extension will show a green dot connecting to `127.0.0.1:58432`.

### 4. Run the Desktop Application

```powershell
python main.py
```

- Click **Minimize to Tray** to let it run quietly in the background all day.
- At the end of the day, open the dashboard and click **Generate Timesheet with Gemma**.
- Or enable **Automatic End-of-Day Generation** in the Settings tab to run automatically (e.g. at 18:00).

---

## Command Line Options

You can also run without GUI:
```powershell
# Run background activity tracker only (headless daemon)
python main.py --headless

# Trigger Gemma analysis for today from CLI
python main.py --analyze

# Trigger Gemma analysis for a specific past date
python main.py --analyze --date 2026-10-25
```

---

## File Structure

```
Auto_time_sheet/
├── main.py                     # Main application entry point
├── config.py                   # Configuration & settings manager
├── requirements.txt            # Python dependencies
├── tracker/
│   ├── activity_manager.py     # Coordinates window, file, and web listeners
│   ├── window_monitor.py       # Active window focus and idle detection
│   ├── file_monitor.py         # Excel (.xlsx, .xls, .csv) file event listener
│   ├── web_receiver.py         # HTTP receiver for browser extension
│   └── logger.py               # Writes activity_YYYY-MM-DD.txt and .jsonl
├── analyzer/
│   ├── gemma_client.py         # LM Studio OpenAI-compatible API client
│   ├── prompt_builder.py       # Summarizes daily raw logs for Gemma prompt
│   └── json_parser.py          # Validates & parses JSON timesheet output
├── ui/
│   ├── app.py                  # Main CustomTkinter desktop window
│   ├── timesheet_view.py       # Timesheet cards, summaries, and Excel export
│   ├── activity_view.py        # Real-time event log stream & filters
│   ├── settings_view.py        # LM Studio & folder configuration
│   └── tray_icon.py            # Windows System Tray minimize & menu
├── browser_extension/          # Companion Chrome/Edge Manifest V3 extension
│   ├── manifest.json
│   ├── background.js
│   ├── content.js
│   ├── popup.html
│   └── popup.js
├── data/
│   ├── logs/                   # Raw daily logs (activity_YYYY-MM-DD.txt)
│   ├── timesheets/             # Generated timesheets (timesheet_YYYY-MM-DD.json)
│   └── settings.json           # User configurations
└── tests/
    └── test_parser.py          # Unit tests
```
