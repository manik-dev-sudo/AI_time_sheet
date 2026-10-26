@echo off
echo Starting Auto Timesheet Desktop...
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo An error occurred. If dependencies are missing, run:
    echo pip install -r requirements.txt
    pause
)
