'''
Author:     Suraj Panwar
LinkedIn:   https://www.linkedin.com/in/surajpanwar26/

Copyright (C) 2024 Suraj Panwar

License:    GNU Affero General Public License
            https://www.gnu.org/licenses/agpl-3.0.en.html
            
GitHub:     https://github.com/GodsScion/Auto_job_applier_linkedIn

version:    24.12.29.12.30
'''


# Imports

import os
import sys
import json
import pathlib
import threading

from time import sleep
from random import randint
from datetime import datetime, timedelta
from pprint import pprint

# Lazy import pyautogui to avoid crash in headless environments
def _alert_safe(*args, **kwargs):
    """Wrapper for pyautogui.alert that fails gracefully in headless mode."""
    try:
        from pyautogui import alert as _pyautogui_alert
        return _pyautogui_alert(*args, **kwargs)
    except Exception:
        print(f"[GUI Alert skipped - headless mode]: {args[0] if args else ''}")
        return None

from config.settings import logs_folder_path


# Thread-safe logging lock
_log_lock = threading.Lock()



#### Common functions ####

#< Directories related
def make_directories(paths: list[str]) -> None:
    '''
    Function to create missing directories
    '''
    for path in paths:
        path = os.path.expanduser(path) # Expands ~ to user's home directory
        path = path.replace("//","/")
        
        # If path looks like a file path, get the directory part
        if '.' in os.path.basename(path):
            path = os.path.dirname(path)

        if not path: # Handle cases where path is empty after dirname
            continue

        try:
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True) # exist_ok=True avoids race condition
        except Exception as e:
            print(f'Error while creating directory "{path}": ', e)


def find_default_profile_directory() -> str | None:
    '''
    Dynamically finds the default Google Chrome 'User Data' directory path
    across Windows, macOS, and Linux, regardless of OS version.

    Returns the absolute path as a string, or None if the path is not found.
    '''
    
    home = pathlib.Path.home()
    
    # Windows
    if sys.platform.startswith('win'):
        paths = [
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data"),
            os.path.expandvars(r"%USERPROFILE%\AppData\Local\Google\Chrome\User Data"),
            os.path.expandvars(r"%USERPROFILE%\Local Settings\Application Data\Google\Chrome\User Data")
        ]
    # Linux
    elif sys.platform.startswith('linux'):
        paths = [
            str(home / ".config" / "google-chrome"),
            str(home / ".var" / "app" / "com.google.Chrome" / "data" / ".config" / "google-chrome"),
        ]
    # MacOS ## For some reason, opening with profile in MacOS is not creating a session for undetected-chromedriver!
    # elif sys.platform == 'darwin':
    #     paths = [
    #         str(home / "Library" / "Application Support" / "Google" / "Chrome")
    #     ]
    else:
        return None

    # Check each potential path and return the first one that exists
    for path_str in paths:
        if os.path.exists(path_str):
            return path_str
            
    return None


def get_default_temp_profile() -> str:
    '''
    Returns a temp directory path for Chrome profile when no user profile is found.
    Creates the directory if it doesn't exist.
    '''
    if sys.platform.startswith('win'):
        temp_profile = r"C:\temp\auto-job-apply-profile"
    else:
        temp_profile = os.path.join(pathlib.Path.home(), ".auto-job-apply-profile")
    
    # Create directory if it doesn't exist
    if not os.path.exists(temp_profile):
        try:
            os.makedirs(temp_profile, exist_ok=True)
        except Exception as e:
            print(f"Warning: Could not create temp profile directory: {e}")
    
    return temp_profile
#>


#< Logging related
def critical_error_log(possible_reason: str, stack_trace: Exception) -> None:
    '''
    Function to log and print critical errors along with datetime stamp
    '''
    print_lg(possible_reason, stack_trace, datetime.now(), from_critical=True)


def get_log_path():
    '''
    Function to replace '//' with '/' for logs path
    '''
    try:
        path = logs_folder_path+"/log.txt"
        return path.replace("//","/")
    except Exception as e:
        critical_error_log("Failed getting log path! So assigning default logs path: './logs/log.txt'", e)
        return "logs/log.txt"


__logs_file_path = get_log_path()


def chrome_setup_help_message() -> str:
    return (
        'Seems like either... '\
        '\n\n1. Chrome is already running. '\
        '\nA. Close all Chrome windows and try again. '\
        '\n\n2. Google Chrome or Chromedriver is out dated. '\
        '\nA. Update browser and Chromedriver (You can run "windows-setup.bat" in /setup folder for Windows PC to update Chromedriver)! '\
        '\n\n3. If error occurred when using "stealth_mode", try reinstalling undetected-chromedriver. '\
        '\nA. Open a terminal and use commands "pip uninstall undetected-chromedriver" and "pip install undetected-chromedriver". '\
        '\n\n\nIf issue persists, try Safe Mode. Set, safe_mode = True in config.py '\
        '\n\nPlease check GitHub discussions/support for solutions https://github.com/GodsScion/Auto_job_applier_linkedIn '\
        '\n                                   OR '\
        '\nReach out in discord ( https://discord.gg/fFp7uUzWCY )'
    )


def print_lg(*msgs: str | dict, end: str = "\n", pretty: bool = False, flush: bool = False, from_critical: bool = False) -> None:
    '''
    Function to log and print. **Note that, `end` and `flush` parameters are ignored if `pretty = True`**
    Thread-safe implementation.
    '''
    with _log_lock:
        try:
            for message in msgs:
                pprint(message) if pretty else print(message, end=end, flush=flush)
                try:
                    with open(__logs_file_path, 'a+', encoding="utf-8") as file:
                        file.write(str(message) + end)
                except (IOError, PermissionError) as file_error:
                    if not from_critical:
                        print(f"Warning: Could not write to log file: {file_error}")
                
                # Publish to dashboard if available (non-blocking)
                try:
                    from modules.dashboard import log_handler
                    try:
                        log_handler.publish(str(message))
                    except Exception:
                        pass
                except Exception:
                    pass
        except Exception as e:
            trail = f'Skipped saving this message: "{msgs}" to log.txt!' if from_critical else "We'll try one more time to log..."
            # Check if pilot mode is enabled - skip alerts in pilot mode
            try:
                from config.settings import pilot_mode_enabled
                if pilot_mode_enabled:
                    print(f"[PILOT MODE] Log file issue (skipping alert): {e}")
                    return
            except ImportError:
                pass
            try:
                _alert_safe(f"log.txt in {logs_folder_path} is open or is occupied by another program! Please close it! {trail}", "Failed Logging")
            except Exception:
                print(f"Logging error: {e}")
            if not from_critical:
                critical_error_log("Log.txt is open or is occupied by another program!", e)
#>


# Bot speed control - load from settings
try:
    from config.settings import form_fill_fast_mode, form_fill_delay_multiplier
    BOT_SLOW_MODE = not form_fill_fast_mode  # Invert: fast_mode=True means slow_mode=False
    BASE_DELAY_MULTIPLIER = form_fill_delay_multiplier
except ImportError:
    BOT_SLOW_MODE = False  # Default to fast mode
    BASE_DELAY_MULTIPLIER = 0.5  # Default to 50% delays for speed


def buffer(speed: int=0) -> None:
    '''
    Function to wait within a period of selected random range.
    * Will not wait if input `speed <= 0`
    * Will wait within a random range of 
      - `0.3 to 0.8 secs` if `1 <= speed < 2`
      - `0.6 to 1.2 secs` if `2 <= speed < 3`
      - `1.0 to speed secs` if `3 <= speed`
    * When BOT_SLOW_MODE is True, delays are multiplied by BASE_DELAY_MULTIPLIER
    '''
    if speed<=0:
        return
    
    multiplier = BASE_DELAY_MULTIPLIER if BOT_SLOW_MODE else 1.0
    
    if speed >= 1 and speed < 2:
        return sleep(randint(3, 8) * 0.1 * multiplier)
    elif speed >= 2 and speed < 3:
        return sleep(randint(6, 12) * 0.1 * multiplier)
    else:
        return sleep(randint(10, max(12, round(speed) * 5)) * 0.1 * multiplier)


def human_delay(min_sec: float = 0.3, max_sec: float = 1.0) -> None:
    '''
    Add a random human-like delay between actions.
    Useful to make bot behavior less predictable.
    '''
    multiplier = BASE_DELAY_MULTIPLIER if BOT_SLOW_MODE else 1.0
    delay = randint(int(min_sec * 100), int(max_sec * 100)) / 100.0 * multiplier
    sleep(delay)
    

def manual_login_retry(is_logged_in: callable, limit: int = 2) -> None:
    '''
    Function to ask and validate manual login
    '''
    count = 0
    while not is_logged_in():
        print_lg("Seems like you're not logged in!")
        button = "Confirm Login"
        message = 'After you successfully Log In, please click "{}" button below.'.format(button)
        if count > limit:
            button = "Skip Confirmation"
            message = 'If you\'re seeing this message even after you logged in, Click "{}". Seems like auto login confirmation failed!'.format(button)
        count += 1
        if _alert_safe(message, "Login Required", button) and count > limit: return



def calculate_date_posted(time_string: str) -> datetime | None | ValueError:
    '''
    Function to calculate date posted from string.
    Returns datetime object | None if unable to calculate | ValueError if time_string is invalid
    Valid time string examples:
    * 10 seconds ago
    * 15 minutes ago
    * 2 hours ago
    * 1 hour ago
    * 1 day ago
    * 10 days ago
    * 1 week ago
    * 1 month ago
    * 1 year ago
    '''
    import re
    time_string = time_string.strip()
    now = datetime.now()

    match = re.search(r'(\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago', time_string, re.IGNORECASE)

    if match:
        try:
            value = int(match.group(1))
            unit = match.group(2).lower()

            if 'second' in unit:
                return now - timedelta(seconds=value)
            elif 'minute' in unit:
                return now - timedelta(minutes=value)
            elif 'hour' in unit:
                return now - timedelta(hours=value)
            elif 'day' in unit:
                return now - timedelta(days=value)
            elif 'week' in unit:
                return now - timedelta(weeks=value)
            elif 'month' in unit:
                return now - timedelta(days=value * 30)  # Approximation
            elif 'year' in unit:
                return now - timedelta(days=value * 365)  # Approximation
        except (ValueError, IndexError):
            # Fallback for cases where parsing fails
            pass
    
    # If regex doesn't match, or parsing failed, return None.
    # This will skip jobs where the date can't be determined, preventing crashes.
    return None


def convert_to_lakhs(value: str) -> str:
    '''
    Converts str value to lakhs, no validations are done except for length and stripping.
    Examples:
    * "100000" -> "1.00"
    * "101,000" -> "10.1," Notice ',' is not removed 
    * "50" -> "0.00"
    * "5000" -> "0.05" 
    '''
    value = value.strip()
    l = len(value)
    if l > 0:
        if l > 5:
            value = value[:l-5] + "." + value[l-5:l-3]
        else:
            value = "0." + "0"*(5-l) + value[:2]
    return value


def convert_to_json(data) -> dict:
    '''
    Function to convert data to JSON, if unsuccessful, returns `{"error": "Unable to parse the response as JSON", "data": data}`
    '''
    try:
        result_json = json.loads(data)
        return result_json
    except json.JSONDecodeError:
        return {"error": "Unable to parse the response as JSON", "data": data}


def truncate_for_csv(data, max_length: int = 131000, suffix: str = "...[TRUNCATED]") -> str:
    '''
    Function to truncate data for CSV writing to avoid field size limit errors.
    * Takes in `data` of any type and converts to string
    * Takes in `max_length` of type `int` - maximum allowed length (default: 131000, leaving room for suffix)
    * Takes in `suffix` of type `str` - text to append when truncated
    * Returns truncated string if data exceeds max_length
    '''
    try:
        # Convert data to string
        str_data = str(data) if data is not None else ""
        
        # If within limit, return as-is
        if len(str_data) <= max_length:
            return str_data
        
        # Truncate and add suffix
        truncated = str_data[:max_length - len(suffix)] + suffix
        return truncated
    except Exception as e:
        return f"[ERROR CONVERTING DATA: {e}]"