"""Launch the modern dashboard to control the bot."""
import sys
import socket
import atexit
import subprocess
import time

# Single instance check using socket binding
LOCK_PORT = 47823  # Arbitrary port for single instance lock

_lock_socket = None

def acquire_single_instance_lock():
    """Ensure only one instance of the dashboard is running."""
    global _lock_socket
    try:
        _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _lock_socket.bind(('127.0.0.1', LOCK_PORT))
        _lock_socket.listen(1)
        return True
    except socket.error:
        return False

def release_lock():
    """Release the single instance lock."""
    global _lock_socket
    if _lock_socket:
        try:
            _lock_socket.close()
        except Exception:
            pass

def cleanup_stale_chrome_sessions():
    """Clean up any stale Chrome/ChromeDriver processes from previous sessions."""
    try:
        if sys.platform == 'win32':
            # Kill stale chromedriver processes
            subprocess.run(['taskkill', '/F', '/IM', 'chromedriver.exe'], 
                          capture_output=True, timeout=5)
            time.sleep(0.5)
        print("Cleaned up stale Chrome sessions")
    except Exception as e:
        print(f"Note: Chrome cleanup skipped: {e}")

# Register cleanup
atexit.register(release_lock)

if __name__ == "__main__":
    # Check for existing instance
    if not acquire_single_instance_lock():
        # Try to show a message to the user
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()  # Hide the main window
            messagebox.showwarning(
                "Already Running",
                "LinkedIn Auto Job Applier is already running!\n\n"
                "Check your taskbar for the existing window."
            )
            root.destroy()
        except Exception:
            print("ERROR: Dashboard is already running in another window!")
        sys.exit(1)
    
    # Import dashboard module (does NOT start Chrome)
    from modules.dashboard.dashboard import BotDashboard, BotController
    
    import threading
    import subprocess
    
    # Create a lazy bot runner that only imports runAiBot when needed
    class LazyBotRunner:
        """Lazy loader for bot - only imports runAiBot when start is called."""
        def __init__(self):
            self._bot_module = None
            self._bot_thread = None
            self._running = False
            self._paused = False
            self._stop_event = threading.Event()
            self._pilot_mode = False
            self._applications_count = 0
            self._pilot_max_applications = 100
            self._on_thread_finished = None  # Callback when bot thread finishes
        
        def _get_bot(self):
            if self._bot_module is None:
                # CRITICAL: Force reimport of runAiBot for fresh state
                # First remove it from cache if it exists
                if 'runAiBot' in sys.modules:
                    print("Removing cached runAiBot module for fresh import...")
                    # Also clear dependent modules that might hold Chrome references
                    modules_to_clear = [k for k in sys.modules.keys() 
                                       if k.startswith('modules.open_chrome') or k == 'runAiBot']
                    for mod in modules_to_clear:
                        try:
                            del sys.modules[mod]
                        except KeyError:
                            pass
                
                # Import runAiBot fresh - this triggers Chrome creation
                print("Importing runAiBot (this will start Chrome)...")
                import runAiBot
                self._bot_module = runAiBot
            return self._bot_module
        
        def start_bot_thread(self) -> bool:
            """Start the bot in a separate thread. Returns True if started, False if already running."""
            if self._running and self._bot_thread and self._bot_thread.is_alive():
                return False  # Already running
            
            # CRITICAL: Clean up any stale Chrome sessions before starting
            cleanup_stale_chrome_sessions()
            
            # Load pilot mode settings from config
            try:
                from config import settings
                self._pilot_mode = getattr(settings, 'pilot_mode_enabled', False)
                self._pilot_max_applications = getattr(settings, 'pilot_max_applications', 100)
                self._applications_count = 0
                if self._pilot_mode:
                    print(f"🚀 PILOT MODE ENABLED - Will apply to up to {self._pilot_max_applications} jobs automatically")
            except Exception as e:
                print(f"Warning: Could not load pilot settings: {e}")
            
            # Ensure clean state before starting
            self._stop_event.clear()
            self._running = True
            self._paused = False
            
            # CRITICAL: Clear any stale bot module reference to force fresh import
            # This ensures we get a fresh Chrome session every time
            if self._bot_module is not None:
                print("Clearing previous bot module reference for fresh start...")
                self._bot_module = None
            
            def run_bot():
                try:
                    print("Starting bot thread...")
                    bot = self._get_bot()
                    
                    # Set stop event reference in bot module if supported
                    if hasattr(bot, 'set_stop_event'):
                        bot.set_stop_event(self._stop_event)
                    
                    # Run the bot's main function
                    if hasattr(bot, 'main'):
                        bot.main()
                    elif hasattr(bot, 'run'):
                        bot.run(total_runs=1)
                    elif hasattr(bot, 'apply_to_jobs'):
                        from config.search import search_terms
                        bot.apply_to_jobs(search_terms)
                        
                except Exception as e:
                    print(f"Bot error: {e}")
                    import traceback
                    traceback.print_exc()
                finally:
                    self._running = False
                    self._paused = False
                    print("Bot thread finished")
                    # Notify dashboard that thread has finished
                    if self._on_thread_finished:
                        try:
                            self._on_thread_finished()
                        except Exception:
                            pass
            
            self._bot_thread = threading.Thread(target=run_bot, daemon=True)
            self._bot_thread.start()
            return True
        
        def start_bot(self):
            """Alias for start_bot_thread for compatibility."""
            return self.start_bot_thread()
        
        def stop_bot(self):
            """Stop the bot and clean up Chrome processes properly."""
            import time
            import gc
            
            print("Stopping bot - beginning cleanup...")
            
            # 1. Signal the bot to stop via the SAME event object the bot thread holds
            self._stop_event.set()
            self._running = False
            self._paused = False
            
            # 2. Signal bot module to stop if supported
            if self._bot_module and hasattr(self._bot_module, 'stop_bot'):
                try:
                    self._bot_module.stop_bot()
                except Exception as e:
                    print(f"Warning: stop_bot signal error: {e}")
            
            # 3. Also reset pause flag in bot module
            if self._bot_module and hasattr(self._bot_module, '_pause_flag'):
                try:
                    self._bot_module._pause_flag = False
                except Exception:
                    pass
            
            # 4. Wait for bot thread to respond to stop signal (longer timeout)
            if self._bot_thread and self._bot_thread.is_alive():
                print("Waiting for bot thread to finish (up to 10s)...")
                self._bot_thread.join(timeout=10)
                if self._bot_thread.is_alive():
                    print("Bot thread still alive after 10s - proceeding with force cleanup")
            
            # 5. CRITICAL: Reset the Chrome session in open_chrome module
            # Use force=True to ensure cleanup happens even during operation
            try:
                from modules.open_chrome import reset_chrome_session, set_auto_reset_allowed
                set_auto_reset_allowed(True)  # Re-enable auto-reset for cleanup
                reset_chrome_session(force=True)  # Force cleanup with process termination
                print("Chrome session reset via module")
            except Exception as e:
                print(f"Warning: Could not reset chrome session via module: {e}")
            
            # 6. Force kill any remaining processes (belt and suspenders approach)
            try:
                if sys.platform == 'win32':
                    # Kill chromedriver first (it holds connections to Chrome)
                    subprocess.run(['taskkill', '/F', '/IM', 'chromedriver.exe'], 
                                   capture_output=True, timeout=5)
                    time.sleep(0.5)
                    # Kill all Chrome processes with tree kill
                    subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe', '/T'], 
                                   capture_output=True, timeout=5)
                else:
                    subprocess.run(['pkill', '-9', '-f', 'chromedriver'], capture_output=True, timeout=5)
                    time.sleep(0.5)
                    subprocess.run(['pkill', '-9', '-f', 'chrome'], capture_output=True, timeout=5)
            except Exception as e:
                print(f"Warning: Process kill error: {e}")
            
            # 7. Wait for ports to be released
            time.sleep(2)
            
            # 8. Clear the bot module reference so next start is fresh
            self._bot_module = None
            self._bot_thread = None
            
            # 9. Force garbage collection to release any held references
            gc.collect()
            
            # 10. IMPORTANT: Clear the SAME stop_event (don't recreate it)
            # Recreating would orphan the reference the bot thread holds
            self._stop_event.clear()
            
            print("Bot stopped - Chrome session fully cleaned up, ready for restart")
        
        def pause_bot(self):
            """Toggle pause state of the bot."""
            self._paused = not self._paused
            if self._bot_module and hasattr(self._bot_module, 'pause_bot'):
                self._bot_module.pause_bot()
            return self._paused
        
        def skip_job(self):
            """Skip the current job."""
            if self._bot_module and hasattr(self._bot_module, 'skip_job'):
                self._bot_module.skip_job()
        
        def is_running(self) -> bool:
            """Check if bot is currently running."""
            return bool(self._running and self._bot_thread and self._bot_thread.is_alive())
        
        def is_paused(self) -> bool:
            """Check if bot is paused."""
            return self._paused
        
        def set_pilot_mode(self, enabled: bool, max_applications: int = 100):
            """Set pilot mode (fully automated, no confirmations)."""
            self._pilot_mode = enabled
            self._pilot_max_applications = max_applications
            if enabled:
                print(f"🚀 Pilot mode enabled - max {max_applications} applications")
            else:
                print("🛑 Pilot mode disabled")
        
        def is_pilot_mode(self) -> bool:
            """Check if pilot mode is enabled."""
            return self._pilot_mode
        
        def get_applications_count(self) -> int:
            """Get the current application count in pilot mode."""
            return self._applications_count
        
        def increment_applications_count(self):
            """Increment the applications count in pilot mode."""
            self._applications_count += 1
            if self._pilot_mode and self._applications_count >= self._pilot_max_applications:
                print(f"🎯 Reached pilot mode limit: {self._applications_count} applications")
                self.stop_bot()
    
    # Create controller and dashboard
    runner = LazyBotRunner()
    controller = BotController(runner)
    dashboard = BotDashboard(controller)
    dashboard.mainloop()
