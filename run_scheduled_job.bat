@echo off
REM ============================================================
REM  LinkedIn Auto Job Applier - Scheduled Task Runner
REM  Called by Windows Task Scheduler daily at 9 AM
REM  Fault-tolerant: logs errors, validates environment first
REM ============================================================

REM Force correct working directory (handles Task Scheduler launching from System32)
cd /d "C:\Users\surpanwar\Desktop\Hunter pro\Auto_job_applier_linkedIn"
if errorlevel 1 (
    echo [%date% %time%] FATAL: Cannot cd to project directory >> "%USERPROFILE%\scheduler_fatal.log"
    exit /b 1
)

REM Ensure logs directory exists
if not exist "logs" mkdir logs

REM Force UTF-8 encoding for Python stdout/stderr (prevents UnicodeEncodeError
REM when Task Scheduler redirects output — cp1252 can't handle emojis/box chars)
set "PYTHONIOENCODING=utf-8"

REM Use separate log for batch messages (Python owns scheduler.log via FileHandler)
set "BATCH_LOG=logs\scheduler_batch.log"

REM Timestamp for this run
echo. >> "%BATCH_LOG%"
echo ================================================================== >> "%BATCH_LOG%"
echo [%date% %time%] BATCH LAUNCHER: Starting scheduled job >> "%BATCH_LOG%"
echo ================================================================== >> "%BATCH_LOG%"

REM Detect Python: prefer venv, fall back to system
set "PYTHON="
if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
    echo [%date% %time%] Using venv Python >> "%BATCH_LOG%"
) else if exist "C:\Users\surpanwar\AppData\Local\Python\pythoncore-3.14-64\python.exe" (
    set "PYTHON=C:\Users\surpanwar\AppData\Local\Python\pythoncore-3.14-64\python.exe"
    echo [%date% %time%] Using system Python >> "%BATCH_LOG%"
) else (
    echo [%date% %time%] FATAL: No Python found! >> "%BATCH_LOG%"
    exit /b 1
)

REM Verify Python works
"%PYTHON%" -c "print('Python OK')" >nul 2>&1
if errorlevel 1 (
    echo [%date% %time%] FATAL: Python executable broken >> "%BATCH_LOG%"
    exit /b 1
)

REM Verify settings.py exists
if not exist "config\settings.py" (
    echo [%date% %time%] FATAL: config\settings.py missing >> "%BATCH_LOG%"
    exit /b 1
)

REM Verify runAiBot.py exists
if not exist "runAiBot.py" (
    echo [%date% %time%] FATAL: runAiBot.py missing >> "%BATCH_LOG%"
    exit /b 1
)

REM Run the scheduler (--once = single session, then exit)
REM Python's logging.FileHandler writes to scheduler.log — do NOT redirect stdout there
echo [%date% %time%] Launching: %PYTHON% run_scheduler.py --once >> "%BATCH_LOG%"
"%PYTHON%" run_scheduler.py --once 2>> "%BATCH_LOG%"
set EXIT_CODE=%errorlevel%

REM Log exit status
if %EXIT_CODE% EQU 0 (
    echo [%date% %time%] BATCH LAUNCHER: Session completed successfully (exit 0) >> "%BATCH_LOG%"
) else (
    echo [%date% %time%] BATCH LAUNCHER: Session exited with code %EXIT_CODE% >> "%BATCH_LOG%"
)

exit /b %EXIT_CODE%
