'''
Author:     Suraj Panwar
LinkedIn:   https://www.linkedin.com/in/surajpanwar26/

Copyright (C) 2024 Suraj Panwar

License:    GNU Affero General Public License
            https://www.gnu.org/licenses/agpl-3.0.en.html
            
GitHub:     https://github.com/GodsScion/Auto_job_applier_linkedIn

version:    24.12.29.12.30
'''

import atexit
import time
from modules.helpers import make_directories
from config.settings import run_in_background, stealth_mode, disable_extensions, safe_mode, file_name, failed_file_name, logs_folder_path, generated_resume_path
from config.questions import default_resume_path, master_resume_path
if stealth_mode:
    import undetected_chromedriver as uc
else: 
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    # from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException, SessionNotCreatedException
from modules.helpers import find_default_profile_directory, critical_error_log, print_lg, chrome_setup_help_message


# Global driver reference for cleanup
_driver = None


def cleanup_driver():
    """Clean up driver on exit."""
    global _driver
    if _driver:
        try:
            _driver.quit()
        except Exception:
            pass
        _driver = None


def initialize_driver(max_retries: int = 3, retry_delay: float = 2.0):
    """
    Initialize Chrome WebDriver with retry logic.
    
    Args:
        max_retries: Maximum number of initialization attempts
        retry_delay: Delay between retries in seconds
    
    Returns:
        Tuple of (driver, wait, actions) or raises exception on failure
    """
    global _driver
    
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            make_directories([file_name, failed_file_name, logs_folder_path+"/screenshots", 
                            default_resume_path, master_resume_path, generated_resume_path+"/temp"])

            # Set up WebDriver with Chrome Profile
            options = uc.ChromeOptions() if stealth_mode else Options()
            
            # Performance optimizations
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            if run_in_background:
                options.add_argument("--headless=new")  # New headless mode
            if disable_extensions:
                options.add_argument("--disable-extensions")

            print_lg(f"Initializing Chrome (attempt {attempt + 1}/{max_retries})...")
            
            if safe_mode: 
                print_lg("SAFE MODE: Will login with a guest profile, browsing history will not be saved in the browser!")
            else:
                profile_dir = find_default_profile_directory()
                if profile_dir: 
                    options.add_argument(f"--user-data-dir={profile_dir}")
                else: 
                    print_lg("Default profile directory not found. Logging in with a guest profile, Web history will not be saved!")
            
            if stealth_mode:
                print_lg("Downloading Chrome Driver... This may take some time. Undetected mode requires download every run!")
                driver = uc.Chrome(options=options)
            else: 
                driver = webdriver.Chrome(options=options)
            
            driver.maximize_window()
            
            # Set page load timeout
            driver.set_page_load_timeout(60)
            driver.implicitly_wait(5)
            
            wait = WebDriverWait(driver, 5)
            actions = ActionChains(driver)
            
            _driver = driver
            
            # Register cleanup handler
            atexit.register(cleanup_driver)
            
            print_lg("Chrome WebDriver initialized successfully!")
            return driver, wait, actions
            
        except (WebDriverException, SessionNotCreatedException, TimeoutError) as e:
            last_exception = e
            print_lg(f"Failed to initialize Chrome (attempt {attempt + 1}): {e}")
            
            if attempt < max_retries - 1:
                print_lg(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 1.5  # Exponential backoff
            
        except Exception as e:
            last_exception = e
            print_lg(f"Unexpected error initializing Chrome: {e}")
            break
    
    # All retries failed
    msg = chrome_setup_help_message()
    if isinstance(last_exception, TimeoutError):
        msg = "Couldn't download Chrome-driver. Set stealth_mode = False in config!"
    
    print_lg(msg)
    critical_error_log("In Opening Chrome", last_exception)
    
    from pyautogui import alert
    alert(msg, "Error in opening chrome")
    raise last_exception


def close_driver():
    """Close the Chrome driver and cleanup resources."""
    global _driver, driver, wait, actions
    try:
        if _driver:
            print_lg("Closing Chrome browser...")
            _driver.quit()
            print_lg("Chrome browser closed successfully!")
    except Exception as e:
        print_lg(f"Error closing Chrome: {e}")
    finally:
        _driver = None
        driver = None
        wait = None
        actions = None


def is_driver_initialized():
    """Check if the driver is initialized and ready."""
    global _driver
    return _driver is not None


def get_driver():
    """Get the current driver instance, initializing if needed."""
    global driver, wait, actions
    if not is_driver_initialized():
        driver, wait, actions = initialize_driver()
    return driver, wait, actions


# Lazy initialization - driver will be created when start_chrome() is called
driver = None
wait = None
actions = None


def start_chrome():
    """Start Chrome browser - call this when bot starts."""
    global driver, wait, actions
    if is_driver_initialized():
        print_lg("Chrome is already running!")
        return driver, wait, actions
    
    print_lg("IF YOU HAVE MORE THAN 10 TABS OPENED, PLEASE CLOSE OR BOOKMARK THEM! Or it's highly likely that application will just open browser and not do anything!")
    print_lg("Starting Chrome browser...")
    driver, wait, actions = initialize_driver()
    print_lg("Chrome browser started and ready!")
    return driver, wait, actions
    
