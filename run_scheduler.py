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
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/scheduler.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)


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
        
        # Advanced Settings from pilot_settings
        print("\n🔧 ADVANCED SETTINGS:")
        print(f"   Daily Times: {getattr(pilot_settings, 'schedule_daily_times', ['09:00'])}")
        print(f"   Weekly Schedule: {getattr(pilot_settings, 'schedule_weekly', {})}")
        print(f"   Notification Method: {getattr(pilot_settings, 'schedule_notification_method', 'desktop')}")
        print(f"   Daily Limit: {getattr(pilot_settings, 'daily_application_limit', 100)}")
        
        # State
        print("\n📊 STATE FILE:")
        state_file = 'logs/scheduler_state.json'
        if os.path.exists(state_file):
            import json
            with open(state_file, 'r') as f:
                state = json.load(f)
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


def run_once():
    """Run the job application bot once and exit."""
    logger.info("Running one-time job application session...")
    
    try:
        from config import settings
        
        # Check if pilot mode is enabled
        pilot_mode = getattr(settings, 'pilot_mode_enabled', False)
        max_apps = getattr(settings, 'pilot_max_applications', 50)
        
        logger.info(f"Pilot Mode: {pilot_mode}, Max Applications: {max_apps}")
        
        # Import and run the bot
        import runAiBot
        
        start_time = datetime.now()
        logger.info(f"Starting bot at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if hasattr(runAiBot, 'main'):
            runAiBot.main()
        elif hasattr(runAiBot, 'run'):
            runAiBot.run(total_runs=1)
        elif hasattr(runAiBot, 'apply_to_jobs'):
            from config.search import search_terms
            runAiBot.apply_to_jobs(search_terms)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() / 60
        logger.info(f"Session completed in {duration:.1f} minutes")
        
        # Send completion notification
        try:
            from modules.scheduler import JobScheduler
            scheduler = JobScheduler()
            scheduler._send_notification(
                "Job Application Session Complete",
                f"Session ran for {duration:.1f} minutes"
            )
        except Exception:
            pass
        
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


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
    
    # Print header
    print("""
╔═══════════════════════════════════════════════════════════╗
║   LinkedIn Auto Job Applier - Background Scheduler        ║
║   Automated job applications without the dashboard        ║
╚═══════════════════════════════════════════════════════════╝
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
