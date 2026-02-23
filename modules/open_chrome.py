'''
Author:     Suraj Panwar
LinkedIn:   https://www.linkedin.com/in/surajpanwar/

Copyright (C) 2024-2026 Suraj Panwar

License:    GNU Affero General Public License
            https://www.gnu.org/licenses/agpl-3.0.en.html
            
GitHub:     https://github.com/surajpanwar/Auto_job_applier_linkedIn

Modified by: Suraj Panwar

version:    26.01.20.5.08
'''

from modules.helpers import get_default_temp_profile, make_directories
from config.settings import run_in_background, stealth_mode, disable_extensions, safe_mode, file_name, failed_file_name, logs_folder_path, generated_resume_path
from config.questions import default_resume_path

import os

# Import pilot mode setting to skip alerts
try:
    from config.settings import pilot_mode_enabled
except ImportError:
    pilot_mode_enabled = False
if stealth_mode:
    import undetected_chromedriver as uc
else: 
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    # from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from modules.helpers import find_default_profile_directory, critical_error_log, print_lg
from selenium.common.exceptions import SessionNotCreatedException

def createChromeSession(isRetry: bool = False):
    make_directories([file_name,failed_file_name,logs_folder_path+"/screenshots",default_resume_path,generated_resume_path+"/temp"])
    # Set up WebDriver with Chrome Profile
    options = uc.ChromeOptions() if stealth_mode else Options()
    if run_in_background:   options.add_argument("--headless")
    if disable_extensions:  options.add_argument("--disable-extensions")
    
    # Performance optimizations for faster startup
    options.add_argument("--disable-gpu")  # Reduces startup time
    options.add_argument("--no-sandbox")  # Faster startup (safe in controlled env)
    options.add_argument("--disable-dev-shm-usage")  # Prevents shared memory issues
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-infobars")  # Removes "Chrome is being controlled" bar
    options.add_argument("--disable-blink-features=AutomationControlled")
    # Reduce startup logging
    options.add_argument("--log-level=3")  # Only fatal errors
    options.add_argument("--silent")
    
    # === ENHANCED ANTI-DETECTION OPTIONS ===
    # These help bypass LinkedIn's automation detection
    options.add_argument("--disable-web-security")  # May help with CSP issues
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--disable-features=IsolateOrigins,site-per-process")
    # Set realistic window size
    options.add_argument("--window-size=1920,1080")
    # Add language to appear more human
    options.add_argument("--lang=en-US,en")
    
    # NOTE: add_experimental_option is NOT compatible with undetected_chromedriver
    # Only add these for regular Selenium mode
    if not stealth_mode:
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

    print_lg("IF YOU HAVE MORE THAN 10 TABS OPENED, PLEASE CLOSE OR BOOKMARK THEM! Or it's highly likely that application will just open browser and not do anything!")
    
    # Profile selection priority:
    # 1. If retry → guest/temp profile
    # 2. If system profile available and not safe_mode → use system profile
    #    (undetected_chromedriver copies it, so no conflict with user's Chrome)
    # 3. If pilot_mode and project chrome_profile_pilot exists → use that
    # 4. Otherwise → guest/temp profile
    profile_dir = find_default_profile_directory()
    if isRetry:
        print_lg("Will login with a guest profile, browsing history will not be saved in the browser!")
        options.add_argument(f"--user-data-dir={get_default_temp_profile()}")
    elif profile_dir and not safe_mode:
        options.add_argument(f"--user-data-dir={profile_dir}")
    elif pilot_mode_enabled:
        # In pilot/scheduler mode, try the project-local chrome_profile_pilot directory
        pilot_profile = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chrome_profile_pilot")
        if os.path.exists(pilot_profile):
            print_lg(f"Using pilot Chrome profile: {pilot_profile}")
            options.add_argument(f"--user-data-dir={pilot_profile}")
        else:
            print_lg("Logging in with a guest profile, Web history will not be saved!")
            options.add_argument(f"--user-data-dir={get_default_temp_profile()}")
    else:
        print_lg("Logging in with a guest profile, Web history will not be saved!")
        options.add_argument(f"--user-data-dir={get_default_temp_profile()}")
    if stealth_mode:
        # Detect Chrome version to use matching ChromeDriver
        chrome_version = None
        try:
            import subprocess
            import re
            # Try to get Chrome version from registry (Windows)
            result = subprocess.run(
                ['reg', 'query', 'HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon', '/v', 'version'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                match = re.search(r'(\d+)\.\d+\.\d+\.\d+', result.stdout)
                if match:
                    chrome_version = int(match.group(1))
                    print_lg(f"Detected Chrome version: {chrome_version}")
        except Exception as e:
            print_lg(f"Could not detect Chrome version: {e}")
        
        print_lg("Downloading Chrome Driver... This may take some time. Undetected mode requires download every run!")
        try:
            if chrome_version:
                driver = uc.Chrome(options=options, version_main=chrome_version, use_subprocess=True)
            else:
                driver = uc.Chrome(options=options, use_subprocess=True)
            
            # === CRITICAL: Remove automation indicators to avoid LinkedIn detection ===
            # Suppress the "undetected chromedriver 1337!" console spam
            # Remove navigator.webdriver flag
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    // Remove automation-related properties
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                    // Suppress console spam from undetected_chromedriver
                    const originalLog = console.log;
                    console.log = function(...args) {
                        if (args[0] && typeof args[0] === 'string' && args[0].includes('1337')) {
                            return; // Suppress chromedriver detection messages
                        }
                        originalLog.apply(console, args);
                    };
                '''
            })
            print_lg("[Stealth] Anti-detection scripts injected")
            
        except Exception as e:
            # If version detection failed, try with fresh options and explicit version
            print_lg(f"Failed with auto version, trying with fresh options: {e}")
            # Create FRESH options to avoid "cannot reuse ChromeOptions" error
            fresh_options = uc.ChromeOptions()
            fresh_options.add_argument("--disable-gpu")
            fresh_options.add_argument("--no-sandbox")
            fresh_options.add_argument("--disable-dev-shm-usage")
            fresh_options.add_argument("--disable-blink-features=AutomationControlled")
            fresh_options.add_argument("--window-size=1920,1080")
            fresh_options.add_argument(f"--user-data-dir={get_default_temp_profile()}")
            driver = uc.Chrome(options=fresh_options, use_subprocess=True)
    else: driver = webdriver.Chrome(options=options) #, service=Service(executable_path="C:\\Program Files\\Google\\Chrome\\chromedriver-win64\\chromedriver.exe"))
    
    # === IMPROVED CHROME STARTUP STABILITY ===
    # Get the configured wait time from settings (for autopilot mode)
    try:
        from config.settings import autopilot_chrome_wait_time
        chrome_wait_time = autopilot_chrome_wait_time
    except ImportError:
        chrome_wait_time = 10  # Default wait time
    
    import time as time_module
    
    # Initial wait for Chrome to fully start
    print_lg(f"[Chrome] Waiting {chrome_wait_time//2}s for Chrome to initialize...")
    time_module.sleep(chrome_wait_time // 2)
    
    # Try to maximize window with retries (undetected-chromedriver can have timing issues)
    for attempt in range(3):
        try:
            time_module.sleep(1)  # Give Chrome time to initialize
            driver.maximize_window()
            print_lg("[Chrome] Window maximized successfully")
            break
        except Exception as e:
            if attempt < 2:
                print_lg(f"[Chrome] maximize_window attempt {attempt+1} failed, retrying...")
                time_module.sleep(2)
            else:
                print_lg(f"[Chrome] Could not maximize window, using default size: {e}")
                # Try to set a reasonable window size instead
                try:
                    driver.set_window_size(1920, 1080)
                except:
                    pass
    
    # Additional stability wait after window is ready
    print_lg(f"[Chrome] Final stability wait ({chrome_wait_time//2}s)...")
    time_module.sleep(chrome_wait_time // 2)
    
    wait = WebDriverWait(driver, 5)
    actions = ActionChains(driver)
    print_lg("[Chrome] ✅ Session created and stable")
    return options, driver, actions, wait

# Lazy Chrome initialization - only create when first accessed
_chrome_session = None
_session_initialized = False  # Track if session was ever created (prevents unwanted resets)
_allow_auto_reset = True  # Flag to prevent auto-reset during bot operation

def set_auto_reset_allowed(allowed: bool):
    """Control whether auto-reset is allowed. Set to False during bot operation."""
    global _allow_auto_reset
    _allow_auto_reset = allowed

def is_session_valid():
    """Check if current Chrome session is valid and responsive."""
    global _chrome_session
    if _chrome_session is None or _chrome_session[1] is None:
        return False
    try:
        # Quick check - try to get current URL
        _ = _chrome_session[1].current_url
        # Also try to get window handles to check browser is alive
        _ = _chrome_session[1].window_handles
        return True
    except Exception as e:
        # Log specific error for debugging
        error_msg = str(e).lower()
        if 'browser window not found' in error_msg or 'invalid session' in error_msg:
            print(f"[Chrome] Browser window lost: {e}")
        return False

def get_chrome_session(max_retries: int = 3, force_new: bool = False):
    """Get or create Chrome session lazily with retry logic for connection errors.
    
    Args:
        max_retries: Number of retry attempts for session creation
        force_new: If True, create new session even if one exists (used for intentional restarts)
    """
    global _chrome_session, _session_initialized, _allow_auto_reset
    from time import sleep
    from urllib3.exceptions import MaxRetryError, NewConnectionError
    
    # If session exists and is valid, return it
    if not force_new and _chrome_session is not None and _chrome_session[1] is not None:
        return _chrome_session
    
    # If session was initialized but is now invalid, and auto-reset is not allowed,
    # raise an error instead of trying to recreate (prevents crash during operation)
    if _session_initialized and not _allow_auto_reset and not force_new:
        raise RuntimeError(
            "Chrome session became invalid during operation. "
            "This usually means the browser was closed unexpectedly. "
            "Please restart the bot."
        )
    
    # Only create new session if never initialized or force_new requested
    if _chrome_session is None or _chrome_session[1] is None or force_new:
        last_error = None
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print_lg(f"Retry attempt {attempt + 1}/{max_retries} to create Chrome session...")
                    # Clean up any stale processes before retry
                    reset_chrome_session(force=True)
                    sleep(2)  # Give OS time to release resources
                
                _chrome_session = createChromeSession()
                _session_initialized = True  # Mark that we've successfully created a session
                print_lg("Chrome session created successfully!")
                return _chrome_session
                
            except SessionNotCreatedException as e:
                critical_error_log("Failed to create Chrome Session, retrying with guest profile", e)
                try:
                    _chrome_session = createChromeSession(True)
                    _session_initialized = True
                    return _chrome_session
                except Exception as e2:
                    last_error = e2
                    
            except (MaxRetryError, NewConnectionError, ConnectionRefusedError) as e:
                # This is the "HTTPConnectionPool max retries exceeded" error
                print_lg(f"Connection error (attempt {attempt + 1}): {type(e).__name__}")
                last_error = e
                if attempt < max_retries - 1:
                    print_lg("Cleaning up stale Chrome processes and retrying...")
                    reset_chrome_session(force=True)
                    sleep(3)  # Wait longer for port release
                    
            except Exception as e:
                last_error = e
                # Check if it's a connection-related error in the message
                error_str = str(e).lower()
                if 'max retries' in error_str or 'connection' in error_str or 'refused' in error_str:
                    print_lg(f"Connection-related error (attempt {attempt + 1}): {e}")
                    if attempt < max_retries - 1:
                        reset_chrome_session(force=True)
                        sleep(3)
                    continue
                    
                msg = 'Seems like Google Chrome is outdated. Update browser and try again! \n\n\nIf issue persists, try Safe Mode. Set, safe_mode = True in config.py \n\nReach out in discord ( https://discord.gg/fFp7uUzWCY )'
                if isinstance(e, (TimeoutError, OSError)): 
                    msg = "Couldn't download Chrome-driver. Set stealth_mode = False in config!"
                print_lg(msg)
                critical_error_log("In Opening Chrome", e)
                # Skip alert in pilot mode - just log and raise
                if not pilot_mode_enabled:
                    from pyautogui import alert
                    alert(msg, "Error in opening chrome")
                else:
                    print_lg(f"[PILOT MODE] Skipping alert popup. Error: {msg}")
                raise
        
        # All retries exhausted
        if last_error:
            msg = f"Failed to create Chrome session after {max_retries} attempts. Please close all Chrome windows and try again."
            print_lg(msg)
            critical_error_log("Chrome session creation failed after retries", last_error)
            # Skip alert in pilot mode - just log and raise
            if not pilot_mode_enabled:
                from pyautogui import alert
                alert(msg, "Chrome Connection Error")
            else:
                print_lg(f"[PILOT MODE] Skipping alert popup. Error: {msg}")
            raise last_error
            
    return _chrome_session

def reset_chrome_session(force: bool = False):
    """Reset Chrome session for next run with thorough cleanup.
    
    Args:
        force: If True, reset even if auto-reset is disabled (used for intentional cleanup)
    """
    global _chrome_session, _session_initialized, _allow_auto_reset
    import subprocess
    import sys
    import gc
    from time import sleep
    
    # Prevent accidental reset during bot operation unless forced
    if not force and not _allow_auto_reset and _session_initialized:
        print_lg("Warning: reset_chrome_session called during operation but auto-reset is disabled. Skipping.")
        return
    
    print_lg("Resetting Chrome session...")
    
    # 1. First try graceful quit of the driver
    if _chrome_session and _chrome_session[1]:
        try:
            print_lg("Attempting graceful Chrome quit...")
            _chrome_session[1].quit()
            print_lg("Chrome driver quit successfully")
        except Exception as e:
            print_lg(f"Chrome quit warning (non-fatal): {e}")
    
    # 2. Clear the session reference
    _chrome_session = None
    _session_initialized = False  # Reset the initialization flag
    
    # 3. Force garbage collection to release WebDriver references
    gc.collect()
    
    # 4. Kill any lingering chromedriver processes FIRST (they hold Chrome connections)
    try:
        if sys.platform == 'win32':
            print_lg("Killing chromedriver processes...")
            result = subprocess.run(['taskkill', '/F', '/IM', 'chromedriver.exe'], 
                         capture_output=True, text=True, timeout=5)
            if "SUCCESS" in result.stdout:
                print_lg("Chromedriver processes killed")
        else:
            subprocess.run(['pkill', '-9', '-f', 'chromedriver'], capture_output=True, timeout=5)
    except Exception as e:
        print_lg(f"Chromedriver kill warning: {e}")
    
    # 5. Wait for chromedriver to fully release
    sleep(1)
    
    # 6. Kill Chrome processes with tree flag to get child processes too
    try:
        if sys.platform == 'win32':
            print_lg("Killing Chrome processes...")
            result = subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe', '/T'], 
                         capture_output=True, text=True, timeout=5)
            if "SUCCESS" in result.stdout:
                print_lg("Chrome processes killed")
        else:
            subprocess.run(['pkill', '-9', '-f', 'chrome'], capture_output=True, timeout=5)
    except Exception as e:
        print_lg(f"Chrome kill warning: {e}")
    
    # 7. Wait for ports to be released (Chrome uses debugging port)
    sleep(2)
    
    # 8. Clear lazy proxy caches so they re-initialize on next use
    # Note: _clear_all_caches is defined below, so we call the class methods directly
    try:
        _LazyDriver._cached_driver = None
        _LazyActions._cached_actions = None
        _LazyWait._cached_wait = None
    except NameError:
        pass  # Classes not yet defined during initial load
    
    print_lg("Chrome session reset complete - ready for new session")

# ============================================================================
# CONVENIENCE WRAPPER FUNCTIONS FOR PILOT MODE AND OTHER SCRIPTS
# These provide simple start/stop semantics for Chrome session management
# ============================================================================

def start_chrome(max_retries: int = 3):
    """
    Start Chrome browser and return driver, wait, and actions objects.
    
    This is a convenience wrapper around get_chrome_session() for scripts
    that need simple start/stop Chrome semantics (like pilot mode).
    
    Args:
        max_retries: Number of retry attempts if session creation fails
        
    Returns:
        tuple: (driver, wait, actions) - The Selenium driver, wait, and action chains
        
    Raises:
        RuntimeError: If Chrome session cannot be created after all retries
    """
    try:
        # Force new session to ensure clean start
        session = get_chrome_session(max_retries=max_retries, force_new=True)
        # Return driver, wait, actions (session is: options, driver, actions, wait)
        return session[1], session[3], session[2]  # driver, wait, actions
    except Exception as e:
        print_lg(f"[start_chrome] Failed to start Chrome: {e}")
        raise RuntimeError(f"Could not start Chrome browser: {e}")


def close_driver(force: bool = True):
    """
    Close the Chrome browser and clean up the session.
    
    This is a convenience wrapper around reset_chrome_session() for scripts
    that need simple start/stop Chrome semantics (like pilot mode).
    
    Args:
        force: If True (default), force close even if auto-reset is disabled
    """
    try:
        reset_chrome_session(force=force)
        print_lg("[close_driver] Chrome browser closed successfully")
    except Exception as e:
        print_lg(f"[close_driver] Warning during Chrome cleanup: {e}")
        # Don't raise - cleanup should be best-effort


# For backward compatibility - these will trigger lazy initialization when accessed
# IMPORTANT: These cache the actual objects after first access to prevent
# repeated calls to get_chrome_session() which could cause unwanted resets
class _LazyDriver:
    """Lazy proxy for driver that initializes on first use and caches the result."""
    _cached_driver = None
    
    def __getattr__(self, name):
        if _LazyDriver._cached_driver is None:
            session = get_chrome_session()
            _LazyDriver._cached_driver = session[1]
        return getattr(_LazyDriver._cached_driver, name)
    
    @classmethod
    def _clear_cache(cls):
        """Clear the cached driver reference (called on session reset)."""
        cls._cached_driver = None

class _LazyActions:
    """Lazy proxy for actions that initializes on first use and caches the result."""
    _cached_actions = None
    
    def __getattr__(self, name):
        if _LazyActions._cached_actions is None:
            session = get_chrome_session()
            _LazyActions._cached_actions = session[2]
        return getattr(_LazyActions._cached_actions, name)
    
    @classmethod
    def _clear_cache(cls):
        """Clear the cached actions reference (called on session reset)."""
        cls._cached_actions = None

class _LazyWait:
    """Lazy proxy for wait that initializes on first use and caches the result."""
    _cached_wait = None
    
    def __getattr__(self, name):
        if _LazyWait._cached_wait is None:
            session = get_chrome_session()
            _LazyWait._cached_wait = session[3]
        return getattr(_LazyWait._cached_wait, name)
    
    @classmethod
    def _clear_cache(cls):
        """Clear the cached wait reference (called on session reset)."""
        cls._cached_wait = None

def _clear_all_caches():
    """Clear all lazy proxy caches. Called internally when session is reset."""
    _LazyDriver._clear_cache()
    _LazyActions._clear_cache()
    _LazyWait._clear_cache()

# These are now lazy - Chrome won't start until they're actually used
options = None
driver = _LazyDriver()
actions = _LazyActions()
wait = _LazyWait()

# Also export the session getter for direct access
__all__ = ['driver', 'actions', 'wait', 'options', 'get_chrome_session', 'reset_chrome_session', 
           'createChromeSession', 'set_auto_reset_allowed', 'is_session_valid', '_clear_all_caches',
           'start_chrome', 'close_driver']
    
