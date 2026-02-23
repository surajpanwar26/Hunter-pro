#!/usr/bin/env python3
"""
LinkedIn Auto Job Applier - Background Scheduler Service

This script runs the job application scheduler in the background without
requiring the dashboard to be open. It can be run as a standalone service
or configured to start automatically via Windows Task Scheduler or cron.

Features:
- Runs independently of the dashboard
- Supports interval, daily, and weekly scheduling
- Desktop and email notifications
- Persistent state across restarts
- Graceful shutdown handling

Usage:
    python run_scheduler.py              # Run with current settings
    python run_scheduler.py --config     # Show current configuration
    python run_scheduler.py --once       # Run once and exit
    python run_scheduler.py --daemon     # Run as background daemon

Author: Suraj Panwar
"""

import sys
import os
import time
import signal
import argparse
import logging
import threading
from datetime import datetime
from modules.scheduler_runtime import apply_scheduled_runtime_overrides
from modules.scheduler_state import load_state, save_session_report as _save_state_report
from modules.bot_session import new_session, get_session_id

# ===== FIX ENCODING FOR TASK SCHEDULER =====
# When stdout is redirected (Task Scheduler, Start-Process, etc.), Python falls back
# to cp1252 on Windows which can't handle emojis/Unicode. Force UTF-8.
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# ===== ROBUST PATH SETUP =====
# Always resolve paths relative to THIS file, not cwd (Task Scheduler may use different cwd)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)  # Force cwd to project root so all relative paths work
sys.path.insert(0, SCRIPT_DIR)

# Ensure logs directory exists BEFORE setting up logging
LOGS_DIR = os.path.join(SCRIPT_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

# Setup logging with absolute paths (with retry for file lock contention on Windows)
LOG_FILE = os.path.join(LOGS_DIR, 'scheduler.log')

def _setup_logging():
    """Setup logging with retry — handles Windows file lock contention."""
    log_handlers = [logging.StreamHandler(sys.stdout)]
    log_file = LOG_FILE
    for attempt in range(3):
        try:
            fh = logging.FileHandler(log_file, encoding='utf-8')
            log_handlers.insert(0, fh)
            break
        except PermissionError:
            if attempt < 2:
                time.sleep(1)  # Wait for batch file handle to release
            else:
                # Fallback: use timestamped log file
                log_file = os.path.join(LOGS_DIR, f'scheduler_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
                try:
                    fh = logging.FileHandler(log_file, encoding='utf-8')
                    log_handlers.insert(0, fh)
                except Exception:
                    pass  # Console-only logging as last resort
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=log_handlers
    )

_setup_logging()
logger = logging.getLogger(__name__)


def setup_signal_handlers(scheduler):
    """Setup graceful shutdown handlers."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        scheduler.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    if sys.platform != 'win32':
        signal.signal(signal.SIGHUP, signal_handler)


def show_configuration():
    """Display current scheduler configuration."""
    try:
        from config import settings
        from config import pilot_settings
        
        print("\n" + "="*60)
        print("LinkedIn Auto Job Applier - Scheduler Configuration")
        print("="*60)
        
        # Pilot Mode Settings
        print("\n📌 PILOT MODE SETTINGS:")
        print(f"   Enabled: {getattr(settings, 'pilot_mode_enabled', False)}")
        print(f"   Resume Mode: {getattr(settings, 'pilot_resume_mode', 'default')}")
        print(f"   Max Applications: {getattr(settings, 'pilot_max_applications', 100)}")
        print(f"   Application Delay: {getattr(settings, 'pilot_application_delay', 30)}s")
        
        # Scheduling Settings
        print("\n⏰ SCHEDULING SETTINGS:")
        print(f"   Enabled: {getattr(settings, 'scheduling_enabled', False)}")
        print(f"   Schedule Type: {getattr(settings, 'schedule_type', 'interval')}")
        print(f"   Interval: {getattr(settings, 'schedule_interval_hours', 24)} hours")
        print(f"   Max Runtime: {getattr(settings, 'schedule_max_runtime', 60)} minutes")
        print(f"   Max Applications: {getattr(settings, 'schedule_max_applications', 50)}")
        print(f"   Resume Mode: {getattr(settings, 'schedule_resume_mode', 'preselected')}")
        
        # Advanced Settings from pilot_settings
        print("\n🔧 ADVANCED SETTINGS:")
        print(f"   Daily Times: {getattr(settings, 'schedule_daily_times', ['09:00'])}")
        print(f"   Weekly Schedule: {getattr(settings, 'schedule_weekly', {})}")
        print(f"   Notification Method: {getattr(pilot_settings, 'schedule_notification_method', 'desktop')}")
        print(f"   Daily Limit: {getattr(pilot_settings, 'daily_application_limit', 100)}")
        
        # State (via centralized state manager)
        print("\n📊 STATE FILE:")
        state_file = 'logs/scheduler_state.json'
        state = load_state()
        if state:
            print(f"   Last Run: {state.get('last_run', 'Never')}")
            print(f"   Next Run: {state.get('next_run', 'Not scheduled')}")
            print(f"   Total Applications: {state.get('total_applications', 0)}")
            print(f"   Session Count: {state.get('session_count', 0)}")
        else:
            print("   No state file found (first run)")
        
        print("\n" + "="*60)
        
    except Exception as e:
        logger.error(f"Error reading configuration: {e}")
        sys.exit(1)


def _check_chrome_alive(max_consecutive_failures: int = 5) -> bool:
    """Check if Chrome/Selenium is still responsive by testing the driver session.
    
    Uses a simple counter-based circuit breaker pattern:
    - Tracks consecutive connection failures
    - If failures exceed threshold, Chrome is considered dead
    - Resets counter on any successful operation
    
    Returns:
        bool: True if Chrome appears alive, False if dead
    """
    try:
        import runAiBot
        driver = getattr(runAiBot, 'driver', None)
        if driver is None:
            return True  # Can't check, assume OK (bot hasn't started yet)
        
        # Quick session check — if this throws, Chrome is dead
        _ = driver.title
        return True
    except Exception:
        return False


class _ChromeWatchdog:
    """Circuit breaker that detects a dead Chrome session and aborts early.
    
    Problem: When Chrome dies mid-session, Selenium retries endlessly
    (Feb 9 run wasted 17 minutes in NewConnectionError retry loop).
    
    Solution: Monitor for consecutive connection failures. Once the threshold
    is exceeded, signal the bot to stop immediately.
    """
    
    def __init__(self, max_consecutive_failures: int = 5, max_runtime_minutes: int = 60):
        self._consecutive_failures = 0
        self._max_failures = max_consecutive_failures
        self._max_runtime = max_runtime_minutes
        self._start_time = None
        self._chrome_dead = False
        self._monitor_thread = None
        self._stop_event = threading.Event()
    
    def start(self, session_start: datetime):
        """Start watchdog monitoring in background thread."""
        self._start_time = session_start
        self._stop_event.clear()
        self._chrome_dead = False
        self._consecutive_failures = 0
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="chrome-watchdog")
        self._monitor_thread.start()
        logger.info(f"  [Watchdog] Started (max_failures={self._max_failures}, max_runtime={self._max_runtime}min)")
    
    def stop(self):
        """Stop watchdog monitoring."""
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
    
    @property
    def is_chrome_dead(self) -> bool:
        return self._chrome_dead
    
    @property
    def is_runtime_exceeded(self) -> bool:
        if self._start_time and self._max_runtime > 0:
            elapsed = (datetime.now() - self._start_time).total_seconds() / 60
            return elapsed > self._max_runtime
        return False
    
    @property
    def should_abort(self) -> bool:
        return self._chrome_dead or self.is_runtime_exceeded
    
    @property
    def abort_reason(self) -> str:
        if self._chrome_dead:
            return f"chrome_dead (after {self._consecutive_failures} consecutive failures)"
        if self.is_runtime_exceeded:
            elapsed = (datetime.now() - self._start_time).total_seconds() / 60
            return f"max_runtime_exceeded ({elapsed:.0f}min > {self._max_runtime}min)"
        return ""
    
    def _monitor_loop(self):
        """Background loop: check Chrome health every 10 seconds."""
        while not self._stop_event.is_set():
            self._stop_event.wait(10)  # Check every 10 seconds
            if self._stop_event.is_set():
                break
            
            # Check runtime limit
            if self.is_runtime_exceeded:
                elapsed = (datetime.now() - self._start_time).total_seconds() / 60
                logger.warning(f"  [Watchdog] MAX RUNTIME EXCEEDED ({elapsed:.0f}min > {self._max_runtime}min)")
                self._signal_bot_stop("max_runtime_exceeded")
                break
            
            # Check Chrome health
            if _check_chrome_alive():
                self._consecutive_failures = 0  # Reset on success
            else:
                self._consecutive_failures += 1
                if self._consecutive_failures >= self._max_failures:
                    logger.error(f"  [Watchdog] CHROME DEAD — {self._consecutive_failures} consecutive failures")
                    self._chrome_dead = True
                    self._signal_bot_stop("chrome_dead")
                    break
                else:
                    logger.warning(f"  [Watchdog] Chrome check failed ({self._consecutive_failures}/{self._max_failures})")
    
    def _signal_bot_stop(self, reason: str):
        """Signal the bot to stop gracefully."""
        try:
            import runAiBot
            # Set the stop flag that the bot checks in its main loop
            if hasattr(runAiBot, 'stop_bot'):
                runAiBot.stop_bot()
                logger.info(f"  [Watchdog] Sent stop signal to bot (reason: {reason})")
            elif hasattr(runAiBot, 'botStopSignal'):
                runAiBot.botStopSignal = True
                logger.info(f"  [Watchdog] Set botStopSignal=True (reason: {reason})")
            else:
                logger.warning(f"  [Watchdog] No stop mechanism found on runAiBot (reason: {reason})")
        except Exception as e:
            logger.error(f"  [Watchdog] Failed to signal stop: {e}")


def run_once():
    """Run the job application bot once and exit.
    
    Fault-tolerant: catches ALL exceptions, logs everything,
    counts only SUCCESSFUL submissions, writes session report.
    
    Includes:
    - Circuit breaker for dead Chrome sessions (prevents 17-min retry loops)
    - Max runtime enforcement via background watchdog
    - Explicit resume mode override for scheduled runs
    - Deloitte DLP popup handling in background thread
    """
    session_start = datetime.now()
    session_ctx = new_session()
    session_report = {
        'start_time': session_start.isoformat(),
        'session_id': session_ctx.session_id,
        'end_time': None,
        'duration_minutes': 0,
        'successful_applications': 0,
        'failed_applications': 0,
        'skipped_jobs': 0,
        'target_applications': 0,
        'exit_reason': 'unknown',
        'errors': [],
    }
    watchdog = None
    
    logger.info("=" * 70)
    logger.info("  SCHEDULED SESSION STARTING")
    logger.info(f"  Session ID: {session_ctx.session_id}")
    logger.info(f"  Time: {session_start.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)
    
    try:
        # ===== STEP 1: Load settings =====
        logger.info("[1/6] Loading configuration...")
        try:
            from config import settings
        except Exception as e:
            logger.critical(f"FATAL: Cannot load config/settings.py: {e}")
            session_report['exit_reason'] = f'config_load_failed: {e}'
            session_report['errors'].append(f"Config load: {e}")
            _write_session_report(session_report, session_start)
            return
        
        max_apps = getattr(settings, 'schedule_max_applications', 9)
        max_runtime = getattr(settings, 'schedule_max_runtime', 60)
        session_report['target_applications'] = max_apps
        logger.info(f"  Target: {max_apps} successful applications")
        logger.info(f"  Schedule type: {getattr(settings, 'schedule_type', 'daily')}")
        logger.info(f"  Max runtime: {max_runtime} min")
        
        # ===== STEP 2: Import bot =====
        logger.info("[2/6] Importing bot module...")
        try:
            import runAiBot
        except Exception as e:
            logger.critical(f"FATAL: Cannot import runAiBot: {e}")
            session_report['exit_reason'] = f'import_failed: {e}'
            session_report['errors'].append(f"Import runAiBot: {e}")
            _write_session_report(session_report, session_start)
            return
        
        # ===== STEP 3: Force safety settings =====
        logger.info("[3/6] Configuring safety overrides...")
        
        schedule_resume_mode = getattr(settings, 'schedule_resume_mode', 'preselected')
        apply_scheduled_runtime_overrides(
            settings=settings,
            run_ai_bot=runAiBot,
            max_jobs=max_apps,
            schedule_resume_mode=schedule_resume_mode,
        )
        
        logger.info(f"  pilot_mode_enabled = True (forced)")
        logger.info(f"  pilot_resume_mode = '{schedule_resume_mode}' (from schedule_resume_mode)")
        logger.info(f"  pilot_max_applications = 0 (unlimited, deferred to max_jobs)")
        logger.info(f"  max_jobs_to_process = {max_apps} (SUCCESS-only counter)")
        logger.info(f"  pause_before_submit = False")
        logger.info(f"  pause_at_failed_question = False")
        
        # ===== STEP 4: Start Chrome Watchdog =====
        logger.info("[4/6] Starting Chrome watchdog & runtime enforcer...")
        watchdog = _ChromeWatchdog(
            max_consecutive_failures=5,
            max_runtime_minutes=max_runtime
        )
        watchdog.start(session_start)
        
        # ===== STEP 5: Record pre-run CSV counts =====
        logger.info("[5/6] Recording pre-run state...")
        applied_csv = os.path.join(SCRIPT_DIR, 'all excels', 'all_applied_applications_history.csv')
        failed_csv = os.path.join(SCRIPT_DIR, 'all excels', 'all_failed_applications_history.csv')
        
        pre_applied = _count_csv_rows(applied_csv)
        pre_failed = _count_csv_rows(failed_csv)
        logger.info(f"  Pre-run applied CSV: {pre_applied} rows")
        logger.info(f"  Pre-run failed CSV:  {pre_failed} rows")
        
        # ===== STEP 6: Run the bot =====
        logger.info("[6/6] Launching bot...")
        bot_error = None
        
        try:
            if hasattr(runAiBot, 'main'):
                runAiBot.main()
            elif hasattr(runAiBot, 'run'):
                runAiBot.run(total_runs=1)
            else:
                raise AttributeError("runAiBot has no main() or run() method")
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt — shutting down gracefully")
            session_report['exit_reason'] = 'keyboard_interrupt'
        except Exception as e:
            bot_error = e
            error_str = f"{type(e).__name__}: {e}"
            # Detect connection-refused errors (Chrome dead) and don't log full trace
            if 'NewConnectionError' in error_str or 'ConnectionRefusedError' in error_str:
                logger.error(f"Bot lost Chrome connection: {error_str[:200]}")
                session_report['exit_reason'] = 'chrome_connection_lost'
            else:
                logger.error(f"Bot raised exception: {error_str}")
                import traceback
                logger.error(traceback.format_exc())
                session_report['exit_reason'] = f'bot_exception: {error_str[:200]}'
            session_report['errors'].append(str(e)[:300])
        
        # ===== POST-RUN: Stop watchdog and collect results =====
        if watchdog:
            if watchdog.should_abort and session_report['exit_reason'] == 'unknown':
                session_report['exit_reason'] = f'watchdog_abort: {watchdog.abort_reason}'
            watchdog.stop()
        
        logger.info("=" * 70)
        logger.info("  SESSION RESULTS")
        logger.info("=" * 70)
        
        # Source 1: runAiBot module counters (in-memory, most accurate)
        mem_applied = getattr(runAiBot, 'easy_applied_count', 0) + getattr(runAiBot, 'external_jobs_count', 0)
        mem_failed = getattr(runAiBot, 'failed_count', 0)
        mem_skipped = getattr(runAiBot, 'skip_count', 0)
        mem_easy = getattr(runAiBot, 'easy_applied_count', 0)
        mem_external = getattr(runAiBot, 'external_jobs_count', 0)
        
        # Source 2: CSV row diff (ground truth — what actually got saved to disk)
        post_applied = _count_csv_rows(applied_csv)
        post_failed = _count_csv_rows(failed_csv)
        csv_new_applied = max(0, post_applied - pre_applied)
        csv_new_failed = max(0, post_failed - pre_failed)
        
        # Use the LOWER of the two as the conservative "definitely successful" count
        # If memory says 9 but CSV only has 7 new rows, trust CSV (disk truth)
        successful = min(mem_applied, csv_new_applied) if csv_new_applied > 0 else mem_applied
        
        session_report['successful_applications'] = successful
        session_report['failed_applications'] = max(mem_failed, csv_new_failed)
        session_report['skipped_jobs'] = mem_skipped
        
        if bot_error is None and session_report['exit_reason'] == 'unknown':
            if successful >= max_apps:
                session_report['exit_reason'] = f'target_reached ({successful}/{max_apps})'
            else:
                session_report['exit_reason'] = f'completed ({successful}/{max_apps})'
        
        logger.info(f"  ✅ SUCCESSFUL applications:  {successful}  (target: {max_apps})")
        logger.info(f"     - Easy Apply:             {mem_easy}")
        logger.info(f"     - External:               {mem_external}")
        logger.info(f"  ❌ Failed applications:       {session_report['failed_applications']}")
        logger.info(f"  ⏭️  Skipped jobs:             {mem_skipped}")
        logger.info(f"  📊 CSV verification:")
        logger.info(f"     - Applied CSV: {pre_applied} → {post_applied} (+{csv_new_applied})")
        logger.info(f"     - Failed CSV:  {pre_failed} → {post_failed} (+{csv_new_failed})")
        
        if successful < max_apps:
            logger.warning(f"  ⚠️ TARGET NOT MET: Got {successful}/{max_apps} successful applications")
            if mem_failed > 0:
                logger.warning(f"     {mem_failed} jobs failed — check failed CSV for details")
        
    except Exception as outer_err:
        # This catches truly catastrophic errors (import failures, etc.)
        logger.critical(f"CATASTROPHIC ERROR in run_once: {outer_err}")
        import traceback
        logger.critical(traceback.format_exc())
        session_report['exit_reason'] = f'catastrophic: {outer_err}'
        session_report['errors'].append(str(outer_err))
    
    finally:
        # ALWAYS write session report, even on crash
        _write_session_report(session_report, session_start)


def _count_csv_rows(csv_path: str) -> int:
    """Count data rows in a CSV file (excludes header). Returns 0 if file missing.
    
    Uses csv.reader for proper parsing — stack traces in quoted fields
    span multiple raw lines, so raw line counting inflates the count.
    """
    try:
        if not os.path.exists(csv_path):
            return 0
        import csv
        with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.reader(f)
            next(reader, None)  # skip header
            return sum(1 for _ in reader)
    except Exception as e:
        logger.warning(f"Could not count CSV rows in {csv_path}: {e}")
        return 0


def _write_session_report(report: dict, session_start: datetime):
    """Write a structured session report to the scheduler log and a JSON state file."""
    session_end = datetime.now()
    duration = (session_end - session_start).total_seconds() / 60
    report['end_time'] = session_end.isoformat()
    report['duration_minutes'] = round(duration, 1)
    
    logger.info("")
    logger.info(f"  ⏱️  Duration: {duration:.1f} minutes")
    logger.info(f"  🏁 Exit reason: {report['exit_reason']}")
    if report['errors']:
        logger.info(f"  ⚠️  Errors: {len(report['errors'])}")
        for err in report['errors'][:5]:
            logger.info(f"     - {str(err)[:150]}")
    logger.info("=" * 70)
    logger.info("  SESSION COMPLETE")
    logger.info("=" * 70)
    
    # Persist state via centralized state manager (single writer path)
    try:
        # scheduler_state.json is still referenced by this path for E2E compat
        state_file = os.path.join(LOGS_DIR, 'scheduler_state.json')
        _save_state_report(
            session_start=session_start,
            session_end=session_end,
            successful=report['successful_applications'],
            failed=report['failed_applications'],
            exit_reason=report['exit_reason'],
            errors=report['errors'][:5] if report['errors'] else [],
            session_id=report.get('session_id'),
        )
    except Exception as e:
        logger.warning(f"Could not save state file: {e}")
    
    # Send notification
    try:
        result_emoji = "✅" if report['successful_applications'] >= report['target_applications'] else "⚠️"
        msg = (f"{result_emoji} {report['successful_applications']}/{report['target_applications']} "
               f"applications in {duration:.0f}min | "
               f"Failed: {report['failed_applications']} | "
               f"Exit: {report['exit_reason']}")
        from modules.scheduler import JobScheduler
        scheduler = JobScheduler()
        scheduler._send_notification("Scheduled Job Session", msg)
    except Exception:
        pass  # Notification is best-effort


def run_daemon():
    """Run the scheduler as a background daemon."""
    logger.info("Starting scheduler daemon...")
    
    try:
        from modules.scheduler import JobScheduler
        from config import settings
        
        # Check if scheduling is enabled
        if not getattr(settings, 'scheduling_enabled', False):
            logger.warning("Scheduling is disabled in settings. Enable it first.")
            print("\n⚠️  Scheduling is disabled!")
            print("Enable it in the dashboard or set 'scheduling_enabled = True' in config/settings.py")
            sys.exit(1)
        
        # Create and start scheduler
        scheduler = JobScheduler()
        setup_signal_handlers(scheduler)
        
        logger.info("Scheduler daemon started")
        print("\n🚀 Scheduler daemon is running!")
        print("   Press Ctrl+C to stop")
        print("   Logs: logs/scheduler.log")
        print("   State: logs/scheduler_state.json\n")
        
        scheduler.start()
        
        # Keep main thread alive
        while scheduler.running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Scheduler error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def create_windows_task():
    """Create a Windows Task Scheduler task for the scheduler."""
    print("\n📋 WINDOWS TASK SCHEDULER SETUP")
    print("="*50)
    print("""
To run the scheduler automatically on Windows:

1. Open Task Scheduler (taskschd.msc)
2. Create Basic Task
3. Name: "LinkedIn Auto Job Applier"
4. Trigger: Choose your schedule (Daily/Weekly)
5. Action: Start a program
6. Program: python.exe (or full path to python)
7. Arguments: run_scheduler.py --once
8. Start in: {cwd}

PowerShell Command (Run as Admin):
```powershell
$action = New-ScheduledTaskAction -Execute "python.exe" -Argument "run_scheduler.py --once" -WorkingDirectory "{cwd}"
$trigger = New-ScheduledTaskTrigger -Daily -At 9am
Register-ScheduledTask -TaskName "LinkedIn Auto Job Applier" -Action $action -Trigger $trigger -Description "Runs LinkedIn job applications automatically"
```
""".format(cwd=os.getcwd()))


def create_cron_job():
    """Show instructions for creating a cron job."""
    print("\n📋 CRON JOB SETUP (Linux/macOS)")
    print("="*50)
    print(f"""
To run the scheduler automatically on Linux/macOS:

1. Open terminal
2. Run: crontab -e
3. Add one of these lines:

# Run daily at 9 AM
0 9 * * * cd {os.getcwd()} && /usr/bin/python3 run_scheduler.py --once >> logs/cron.log 2>&1

# Run every 4 hours
0 */4 * * * cd {os.getcwd()} && /usr/bin/python3 run_scheduler.py --once >> logs/cron.log 2>&1

# Run Monday to Friday at 8 AM
0 8 * * 1-5 cd {os.getcwd()} && /usr/bin/python3 run_scheduler.py --once >> logs/cron.log 2>&1

4. Save and exit

To check cron logs:
    tail -f logs/cron.log
""")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='LinkedIn Auto Job Applier - Background Scheduler',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_scheduler.py              # Run scheduler daemon
  python run_scheduler.py --config     # Show configuration
  python run_scheduler.py --once       # Run once and exit
  python run_scheduler.py --setup-windows  # Show Windows Task Scheduler setup
  python run_scheduler.py --setup-cron     # Show cron job setup
        """
    )
    
    parser.add_argument('--config', action='store_true',
                       help='Show current scheduler configuration')
    parser.add_argument('--once', action='store_true',
                       help='Run one session and exit')
    parser.add_argument('--daemon', action='store_true',
                       help='Run as background daemon (default)')
    parser.add_argument('--setup-windows', action='store_true',
                       help='Show Windows Task Scheduler setup instructions')
    parser.add_argument('--setup-cron', action='store_true',
                       help='Show cron job setup instructions')
    
    args = parser.parse_args()
    
    # Print header (ASCII-safe for Windows Task Scheduler / redirected stdout)
    print("""
===========================================================
|   LinkedIn Auto Job Applier - Background Scheduler        |
|   Automated job applications without the dashboard        |
===========================================================
    """)
    
    if args.config:
        show_configuration()
    elif args.once:
        run_once()
    elif args.setup_windows:
        create_windows_task()
    elif args.setup_cron:
        create_cron_job()
    else:
        # Default: run daemon
        run_daemon()


if __name__ == "__main__":
    main()
