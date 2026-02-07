'''
Job Application Scheduler Module
================================
Provides scheduling capabilities for automated job application runs.
Supports interval, daily, and weekly scheduling with system tray integration.

Author: Suraj Panwar
'''

import os
import sys
import json
import time
import logging
import threading
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict, List, Any
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class JobScheduler:
    """
    Manages scheduled job application runs.
    Supports interval-based, daily, and weekly scheduling.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self.config = self._load_config()
        self._running = False
        self.running = False  # Public attribute for external access
        self._scheduler_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._current_session_start: Optional[datetime] = None
        self._applications_this_session = 0
        self._callbacks: Dict[str, List[Callable]] = {
            'on_start': [],
            'on_complete': [],
            'on_error': [],
            'on_session_start': [],
            'on_session_end': []
        }
        self._state_file = Path("logs/scheduler_state.json")
        self._load_state()
    
    def _get_default_config_path(self) -> str:
        """Get path to default config file."""
        return os.path.join(os.path.dirname(__file__), '..', 'config', 'pilot_settings.py')
    
    def _load_config(self) -> Dict[str, Any]:
        """Load scheduling configuration from settings."""
        try:
            # Try to import from config module
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from config import settings
            from config import pilot_settings
            
            return {
                'enabled': getattr(settings, 'scheduling_enabled', False),
                'schedule_type': getattr(settings, 'schedule_type', 'interval'),
                'interval_hours': getattr(settings, 'schedule_interval_hours', 4),
                'daily_times': getattr(settings, 'schedule_daily_times', ['09:00', '17:00']),
                'weekly': getattr(settings, 'schedule_weekly', {}),
                'max_runtime': getattr(settings, 'schedule_max_runtime', 120),
                'max_applications': getattr(settings, 'schedule_max_applications', 50),
                'pilot_mode': getattr(settings, 'pilot_mode_enabled', False),
                'pilot_resume_mode': getattr(settings, 'pilot_resume_mode', 'tailored'),
                'notify_on_start': getattr(pilot_settings, 'schedule_notify_on_start', True),
                'notify_on_complete': getattr(pilot_settings, 'schedule_notify_on_complete', True),
                'notify_on_error': getattr(pilot_settings, 'schedule_notify_on_error', True),
                'notification_method': getattr(pilot_settings, 'schedule_notification_method', 'desktop'),
                'daily_limit': getattr(pilot_settings, 'daily_application_limit', 100),
            }
        except ImportError as e:
            logger.warning(f"Could not load config: {e}, using defaults")
            return {
                'enabled': False,
                'schedule_type': 'interval',
                'interval_hours': 4,
                'daily_times': ['09:00', '17:00'],
                'weekly': {},
                'max_runtime': 120,
                'max_applications': 50,
                'pilot_mode': False,
                'pilot_resume_mode': 'tailored',
                'notify_on_start': True,
                'notify_on_complete': True,
                'notify_on_error': True,
                'notification_method': 'desktop',
                'daily_limit': 100,
            }
    
    def _load_state(self):
        """Load scheduler state from disk."""
        try:
            if self._state_file.exists():
                with open(self._state_file, 'r') as f:
                    state = json.load(f)
                    self._applications_today = state.get('applications_today', 0)
                    self._last_run_date = state.get('last_run_date', None)
                    self._last_run_time = state.get('last_run_time', None)
            else:
                self._applications_today = 0
                self._last_run_date = None
                self._last_run_time = None
        except Exception as e:
            logger.error(f"Error loading state: {e}")
            self._applications_today = 0
            self._last_run_date = None
            self._last_run_time = None
    
    def _save_state(self):
        """Save scheduler state to disk."""
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            next_run = self.get_next_run_time()
            state = {
                'applications_today': self._applications_today,
                'last_run_date': self._last_run_date,
                'last_run_time': datetime.now().isoformat(),
                'next_scheduled_run': next_run.isoformat() if next_run else None
            }
            with open(self._state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving state: {e}")
    
    def register_callback(self, event: str, callback: Callable):
        """Register a callback for scheduler events."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    def _emit(self, event: str, *args, **kwargs):
        """Emit an event to registered callbacks."""
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in callback for {event}: {e}")
    
    def get_next_run_time(self) -> Optional[datetime]:
        """Calculate the next scheduled run time."""
        if not self.config.get('enabled', False):
            return None
        
        now = datetime.now()
        schedule_type = self.config.get('schedule_type', 'interval')
        
        if schedule_type == 'interval':
            hours = self.config.get('interval_hours', 4)
            if self._last_run_time:
                try:
                    last = datetime.fromisoformat(self._last_run_time)
                    next_run = last + timedelta(hours=hours)
                    if next_run > now:
                        return next_run
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing last run time: {e}")
            return now + timedelta(hours=hours)
        
        elif schedule_type == 'daily':
            times = self.config.get('daily_times', ['09:00'])
            today = now.date()
            
            for time_str in sorted(times):
                try:
                    hour, minute = map(int, time_str.split(':'))
                    scheduled = datetime.combine(today, datetime.min.time().replace(hour=hour, minute=minute))
                    if scheduled > now:
                        return scheduled
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing daily time '{time_str}': {e}")
                    continue
            
            # All times today have passed, schedule for tomorrow
            if times:
                try:
                    hour, minute = map(int, times[0].split(':'))
                    tomorrow = today + timedelta(days=1)
                    return datetime.combine(tomorrow, datetime.min.time().replace(hour=hour, minute=minute))
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing tomorrow's time: {e}")
            return now + timedelta(days=1)
        
        elif schedule_type == 'weekly':
            weekly = self.config.get('weekly', {})
            days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            current_day_idx = now.weekday()
            
            # Check remaining times today and future days
            for day_offset in range(8):  # Check up to 7 days ahead
                check_day_idx = (current_day_idx + day_offset) % 7
                day_name = days[check_day_idx]
                times = weekly.get(day_name, [])
                
                check_date = now.date() + timedelta(days=day_offset)
                
                for time_str in sorted(times):
                    try:
                        hour, minute = map(int, time_str.split(':'))
                        scheduled = datetime.combine(check_date, datetime.min.time().replace(hour=hour, minute=minute))
                        if scheduled > now:
                            return scheduled
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Error parsing weekly time '{time_str}': {e}")
                        continue
            
            return None
        
        return None
    
    def should_run_now(self) -> bool:
        """Check if the scheduler should trigger a run now."""
        next_run = self.get_next_run_time()
        if not next_run:
            return False
        
        now = datetime.now()
        # Run if we're within 1 minute of scheduled time
        return abs((next_run - now).total_seconds()) < 60
    
    def can_run_today(self) -> bool:
        """Check if we can still run today (haven't exceeded daily limit)."""
        today = datetime.now().date().isoformat()
        if self._last_run_date != today:
            # New day, reset counter
            self._applications_today = 0
            self._last_run_date = today
            self._save_state()
        
        return self._applications_today < self.config.get('daily_limit', 100)
    
    def start(self):
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler is already running")
            return
        
        self._running = True
        self.running = True  # Update public attribute
        self._stop_event.clear()
        
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()
        
        logger.info("Scheduler started")
        self._emit('on_start')
        self._send_notification("Scheduler Started", "Job application scheduler is now running.")
    
    def stop(self):
        """Stop the scheduler."""
        if not self._running:
            return
        
        self._running = False
        self.running = False  # Update public attribute
        self._stop_event.set()
        
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        
        logger.info("Scheduler stopped")
        self._save_state()
    
    def _scheduler_loop(self):
        """Main scheduler loop - runs in a background thread."""
        logger.info("Scheduler loop started")
        
        while self._running and not self._stop_event.is_set():
            try:
                if self.should_run_now() and self.can_run_today():
                    logger.info("Triggering scheduled run")
                    self._run_session()
                
                # Sleep for 30 seconds between checks
                self._stop_event.wait(30)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                self._emit('on_error', str(e))
                self._stop_event.wait(60)  # Wait longer on error
    
    def _run_session(self):
        """Execute a scheduled job application session."""
        self._current_session_start = datetime.now()
        self._applications_this_session = 0
        
        logger.info("Starting scheduled session")
        self._emit('on_session_start', self._current_session_start)
        self._send_notification("Session Started", "Scheduled job application session has started.")
        
        try:
            # Run the bot
            success = self._execute_bot()
            
            # Update state
            self._last_run_time = datetime.now().isoformat()
            self._save_state()
            
            if success:
                self._emit('on_session_end', {
                    'applications': self._applications_this_session,
                    'duration': (datetime.now() - self._current_session_start).total_seconds(),
                    'status': 'success'
                })
                self._send_notification(
                    "Session Complete", 
                    f"Applied to {self._applications_this_session} jobs successfully."
                )
            else:
                self._emit('on_error', 'Session ended with errors')
                self._send_notification("Session Error", "Session ended with errors. Check logs.")
                
        except Exception as e:
            logger.error(f"Error in session: {e}")
            self._emit('on_error', str(e))
            self._send_notification("Session Error", f"Error: {str(e)[:100]}")
    
    def _execute_bot(self) -> bool:
        """Execute the job application bot with max_runtime and max_applications enforcement."""
        try:
            # Import and run the bot module
            import runAiBot
            import threading
            from config import settings
            
            # Set pilot mode for automated operation
            runAiBot.pause_before_submit = False
            runAiBot.pause_at_failed_question = False
            
            # Ensure bot has a stop event for graceful shutdown
            if not getattr(runAiBot, '_stop_event', None):
                import threading as _th
                runAiBot.set_stop_event(_th.Event())
            
            # Set limits
            max_jobs = self.config.get('max_applications', 50)
            max_runtime_minutes = self.config.get('max_runtime', 120)
            
            # Enforce max_applications: write to settings so check_pilot_limit_reached() picks it up
            if max_jobs > 0:
                settings.schedule_max_applications = max_jobs
                # Also set max_jobs_to_process so the bot's limit checker enforces it
                current_max = getattr(settings, 'max_jobs_to_process', 0)
                if current_max == 0 or max_jobs < current_max:
                    settings.max_jobs_to_process = max_jobs
            
            # Track session
            session_start = time.time()
            bot_error = [None]
            
            def run_bot():
                try:
                    if hasattr(runAiBot, 'main'):
                        runAiBot.main()
                except Exception as e:
                    bot_error[0] = e
            
            # Run the bot in a thread so we can enforce max_runtime
            bot_thread = threading.Thread(target=run_bot, daemon=True)
            bot_thread.start()
            
            # Wait for completion or timeout
            timeout_seconds = max_runtime_minutes * 60 if max_runtime_minutes > 0 else None
            bot_thread.join(timeout=timeout_seconds)
            
            if bot_thread.is_alive():
                # Timeout reached — signal the bot to stop gracefully
                logger.warning(f"Max runtime ({max_runtime_minutes}min) reached — sending stop signal")
                if hasattr(runAiBot, 'stop_bot'):
                    runAiBot.stop_bot()
                elif hasattr(runAiBot, '_stop_event') and runAiBot._stop_event:
                    runAiBot._stop_event.set()
                # Give the bot a few seconds to shut down gracefully
                bot_thread.join(timeout=30)
                if bot_thread.is_alive():
                    logger.warning("Bot did not stop gracefully within 30s after timeout")
            
            # Log session stats
            elapsed = (time.time() - session_start) / 60
            apps_done = getattr(runAiBot, 'easy_applied_count', 0) + getattr(runAiBot, 'external_jobs_count', 0)
            self._applications_this_session = apps_done
            logger.info(f"Session completed: {apps_done} applications in {elapsed:.1f} minutes")
            logger.info(f"Max limits: {max_jobs} applications, {max_runtime_minutes} minutes")
            
            if bot_error[0]:
                logger.error(f"Bot raised error: {bot_error[0]}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Bot execution error: {e}")
            return False
    
    def _send_notification(self, title: str, message: str):
        """Send a notification based on configured method."""
        method = self.config.get('notification_method', 'desktop')
        
        if method in ('desktop', 'both'):
            self._send_desktop_notification(title, message)
        
        if method in ('email', 'both'):
            self._send_email_notification(title, message)
    
    def _send_desktop_notification(self, title: str, message: str):
        """Send a desktop notification."""
        try:
            if sys.platform == 'win32':
                # Windows toast notification
                try:
                    from win10toast import ToastNotifier
                    toaster = ToastNotifier()
                    toaster.show_toast(title, message, duration=5, threaded=True)
                except ImportError:
                    # Fallback to PowerShell
                    ps_script = f'''
                    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
                    $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
                    $textNodes = $template.GetElementsByTagName("text")
                    $textNodes[0].AppendChild($template.CreateTextNode("{title}")) | Out-Null
                    $textNodes[1].AppendChild($template.CreateTextNode("{message}")) | Out-Null
                    $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
                    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Job Application Bot").Show($toast)
                    '''
                    subprocess.run(['powershell', '-Command', ps_script], capture_output=True)
            elif sys.platform == 'darwin':
                # macOS notification
                subprocess.run([
                    'osascript', '-e',
                    f'display notification "{message}" with title "{title}"'
                ])
            else:
                # Linux notification
                subprocess.run(['notify-send', title, message])
        except Exception as e:
            logger.error(f"Desktop notification error: {e}")
    
    def _send_email_notification(self, title: str, message: str):
        """Send an email notification."""
        try:
            from config import pilot_settings as ps
            
            if not ps.schedule_email_to:
                return
            
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart()
            msg['From'] = ps.schedule_email_username
            msg['To'] = ps.schedule_email_to
            msg['Subject'] = f"Job Bot: {title}"
            
            body = f"""
            {title}
            {'='*50}
            
            {message}
            
            Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            
            ---
            This is an automated message from your LinkedIn Job Application Bot.
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(ps.schedule_email_smtp_server, ps.schedule_email_smtp_port) as server:
                server.starttls()
                server.login(ps.schedule_email_username, ps.schedule_email_password)
                server.send_message(msg)
            
            logger.info("Email notification sent")
        except Exception as e:
            logger.error(f"Email notification error: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status."""
        next_run = self.get_next_run_time()
        session_info = None
        if self._current_session_start is not None:
            session_info = {
                'active': True,
                'start_time': self._current_session_start.isoformat(),
                'applications': self._applications_this_session
            }
        
        return {
            'running': self._running,
            'enabled': self.config.get('enabled', False),
            'schedule_type': self.config.get('schedule_type', 'interval'),
            'next_run': next_run.isoformat() if next_run else None,
            'last_run': self._last_run_time,
            'applications_today': self._applications_today,
            'daily_limit': self.config.get('daily_limit', 100),
            'current_session': session_info
        }
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update scheduler configuration."""
        self.config.update(new_config)
        self._save_state()
        logger.info("Scheduler configuration updated")
    
    def run_now(self):
        """Manually trigger a session run."""
        if not self.can_run_today():
            logger.warning("Daily limit reached, cannot run")
            return False
        
        # Run in separate thread to not block
        thread = threading.Thread(target=self._run_session, daemon=True)
        thread.start()
        return True


class SchedulerService:
    """
    Background service that runs the scheduler independently.
    Can be started as a Windows service or daemon.
    """
    
    def __init__(self):
        self.scheduler = JobScheduler()
        self._service_running = False
    
    def start_service(self):
        """Start the scheduler service."""
        self._service_running = True
        self.scheduler.start()
        
        logger.info("Scheduler service started")
        
        # Keep running until stopped
        try:
            while self._service_running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt, stopping service")
        finally:
            self.stop_service()
    
    def stop_service(self):
        """Stop the scheduler service."""
        self._service_running = False
        self.scheduler.stop()
        logger.info("Scheduler service stopped")


# Singleton instance
_scheduler_instance: Optional[JobScheduler] = None


def get_scheduler() -> JobScheduler:
    """Get the global scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = JobScheduler()
    return _scheduler_instance


def start_scheduler():
    """Start the global scheduler."""
    get_scheduler().start()


def stop_scheduler():
    """Stop the global scheduler."""
    if _scheduler_instance:
        _scheduler_instance.stop()


if __name__ == "__main__":
    # Run as standalone service
    service = SchedulerService()
    service.start_service()
