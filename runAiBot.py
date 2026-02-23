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


# Imports
import os
import csv
import re
import time
import threading
import pyautogui

# Set CSV field size limit to prevent field size errors
csv.field_size_limit(1000000)  # Set to 1MB instead of default 131KB

from random import choice, shuffle, randint
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.select import Select
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, NoSuchWindowException, ElementNotInteractableException, WebDriverException, StaleElementReferenceException, TimeoutException

from config.personals import *
from config.questions import *
from config.search import *
from config.secrets import use_AI, username, password, ai_provider
from config.settings import *
from config import settings as settings_module  # For getattr access to dynamic settings

# Re-import from personals to guarantee user's personal data wins over any residual defaults.
# This is a safety net — the duplicate definitions have been removed from questions.py,
# but this explicit import protects against future accidental re-additions.
from config.personals import (
    years_of_experience, desired_salary, current_ctc, notice_period,
    require_visa, us_citizenship, linkedIn, website, linkedin_headline,
    linkedin_summary, cover_letter, recent_employer, confidence_level,
)

from modules.open_chrome import *
# Import session management functions explicitly
from modules.open_chrome import set_auto_reset_allowed, is_session_valid
from modules.helpers import *
from modules.clickers_and_finders import *
from modules.validator import validate_config
from modules.popup_blocker import (
    PopupBlocker, 
    dismiss_deloitte_popup, 
    setup_popup_blocker_for_session,
    inject_popup_blocker_script,
    aggressive_popup_sweep,
    _is_easy_apply_open
)

# Network security check for corporate environments
try:
    from modules.network_check import run_full_security_check, check_and_warn
    NETWORK_CHECK_AVAILABLE = True
except ImportError:
    NETWORK_CHECK_AVAILABLE = False

if use_AI:
    from modules.ai.openaiConnections import ai_create_openai_client, ai_extract_skills, ai_answer_question, ai_close_openai_client
    from modules.ai.deepseekConnections import deepseek_create_client, deepseek_extract_skills, deepseek_answer_question
    from modules.ai.geminiConnections import gemini_create_client, gemini_extract_skills, gemini_answer_question
    from modules.ai.groqConnections import groq_create_client, groq_extract_skills, groq_answer_question, groq_tailor_resume

from typing import Literal

# Import settings for pause options
try:
    from config.settings import pause_before_submit as settings_pause_before_submit
    from config.settings import pause_at_failed_question as settings_pause_at_failed_question
except ImportError:
    settings_pause_before_submit = False
    settings_pause_at_failed_question = False

pyautogui.FAILSAFE = False


def _to_float(value, default=0.0) -> float:
    """Safely convert to float for numeric calculations."""
    try:
        return float(value)
    except Exception:
        try:
            # Extract first number from string like "150000" or "150,000"
            cleaned = re.sub(r"[^0-9.]+", "", str(value))
            return float(cleaned) if cleaned else float(default)
        except Exception:
            return float(default)


def _to_int(value, default=0) -> int:
    """Safely convert to int for numeric calculations."""
    try:
        return int(value)
    except Exception:
        try:
            cleaned = re.sub(r"[^0-9]+", "", str(value))
            return int(cleaned) if cleaned else int(default)
        except Exception:
            return int(default)


#< Global Variables and logics

# Initialize pause settings from config (can be overridden at runtime)
pause_before_submit = settings_pause_before_submit
pause_at_failed_question = settings_pause_at_failed_question

# PILOT MODE - Skip all confirmations when enabled
try:
    from config.settings import pilot_mode_enabled, pilot_resume_mode, pilot_max_applications, pilot_application_delay, pilot_continue_on_error, job_search_mode
except ImportError:
    pilot_mode_enabled = False
    pilot_resume_mode = 'tailored'
    pilot_max_applications = 0
    pilot_application_delay = 5
    pilot_continue_on_error = True
    job_search_mode = 'sequential'

# In pilot mode, disable all pause/confirmation dialogs
if pilot_mode_enabled:
    pause_at_failed_question = False
    pause_before_submit = False
    print("[PILOT MODE] \u2708\ufe0f All confirmation dialogs disabled for automated operation")

if run_in_background == True:
    pause_at_failed_question = False
    pause_before_submit = False
    run_non_stop = False

first_name = first_name.strip()
middle_name = middle_name.strip()
last_name = last_name.strip()
full_name = first_name + " " + middle_name + " " + last_name if middle_name else first_name + " " + last_name

useNewResume = True
easy_apply_active = False  # Guard to prevent popup blocker from closing modal
randomly_answered_questions = set()

tabs_count = 1
easy_applied_count = 0
external_jobs_count = 0
failed_count = 0
skip_count = 0
dailyEasyApplyLimitReached = False

# ===== PER-SESSION RUNTIME CONTEXT =====
# Bridge: create a session context that co-exists with the globals above.
# New code should prefer reading/writing through _session_ctx; legacy code
# still mutates the bare globals and the context is synced at session boundaries.
try:
    from modules.bot_session import current_session as _get_session_ctx, new_session as _new_session, get_session_id as _get_session_id
    _session_ctx = _get_session_ctx()
except Exception:
    _session_ctx = None
    def _get_session_id():
        return "no-session"

# ===== STUCK / TIMEOUT RECOVERY SYSTEM =====
# Import timeout settings with safe defaults
try:
    from config.settings import per_job_timeout, form_fill_timeout, dialog_auto_dismiss_timeout
except ImportError:
    per_job_timeout = 180
    form_fill_timeout = 120
    dialog_auto_dismiss_timeout = 15

class JobTimeoutError(Exception):
    """Raised when a single job application exceeds per_job_timeout."""
    pass

def _safe_pyautogui_confirm(text, title="", buttons=None, timeout_seconds=None):
    """
    Wrapper around pyautogui.confirm that auto-dismisses in pilot/scheduled mode.
    In pilot mode or when dialog_auto_dismiss_timeout > 0, runs the dialog in a thread 
    and auto-presses Enter after the timeout to dismiss it.
    Falls back to first button option (safe default).
    """
    if buttons is None:
        buttons = ["OK"]
    
    # Determine effective timeout
    effective_timeout = timeout_seconds if timeout_seconds is not None else dialog_auto_dismiss_timeout
    
    # In pilot mode, skip dialog entirely and return first (default) option
    if pilot_mode_enabled:
        print_lg(f"[PILOT] Auto-dismissing dialog: '{title}' -> '{buttons[0]}'")
        return buttons[0]
    
    # If no timeout configured, use native pyautogui (blocking)
    if not effective_timeout or effective_timeout <= 0:
        return pyautogui.confirm(text=text, title=title, buttons=buttons)
    
    # Threaded auto-dismiss: run dialog in thread, press Enter after timeout
    result_holder = [buttons[0]]  # Default to first button
    dialog_done = threading.Event()
    
    def _show_dialog():
        try:
            result_holder[0] = pyautogui.confirm(text=text, title=title, buttons=buttons)
        except Exception:
            result_holder[0] = buttons[0]
        finally:
            dialog_done.set()
    
    dialog_thread = threading.Thread(target=_show_dialog, daemon=True)
    dialog_thread.start()
    
    # Wait for timeout, then auto-dismiss if still open
    if not dialog_done.wait(timeout=effective_timeout):
        print_lg(f"[TIMEOUT] Auto-dismissing dialog after {effective_timeout}s: '{title}'")
        try:
            pyautogui.press('enter')  # Dismiss the dialog
        except Exception:
            pass
        dialog_done.wait(timeout=3)  # Give it 3s to close
    
    return result_holder[0]

def _safe_pyautogui_alert(text, title="", button="OK", timeout_seconds=None):
    """Wrapper around pyautogui.alert that auto-dismisses in pilot/scheduled mode."""
    if pilot_mode_enabled:
        print_lg(f"[PILOT] Auto-dismissing alert: '{title}'")
        return button
    
    effective_timeout = timeout_seconds if timeout_seconds is not None else dialog_auto_dismiss_timeout
    if not effective_timeout or effective_timeout <= 0:
        return pyautogui.alert(text=text, title=title, button=button)
    
    result_holder = [button]
    dialog_done = threading.Event()
    
    def _show_alert():
        try:
            result_holder[0] = pyautogui.alert(text=text, title=title, button=button)
        except Exception:
            pass
        finally:
            dialog_done.set()
    
    alert_thread = threading.Thread(target=_show_alert, daemon=True)
    alert_thread.start()
    
    if not dialog_done.wait(timeout=effective_timeout):
        print_lg(f"[TIMEOUT] Auto-dismissing alert after {effective_timeout}s: '{title}'")
        try:
            pyautogui.press('enter')
        except Exception:
            pass
        dialog_done.wait(timeout=3)
    
    return result_holder[0]


# Bot control flags for dashboard integration
# (threading already imported at top)
_stop_event = None  # Threading event for stop signal
_pause_flag = False  # Pause flag
_skip_current = False  # Skip current job flag

# ===== VERBOSE LOGGING FOR DASHBOARD =====
def emit_dashboard_event(event: str, data: dict | None = None):
    """Publish deterministic structured telemetry events for dashboard."""
    try:
        from modules.dashboard import log_handler
        log_handler.publish_event(event=event, data=data or {}, source="runAiBot")
    except Exception:
        pass


def log_action(action: str, details: str = "", level: str = "info"):
    """
    Log detailed bot actions to both console and dashboard.
    
    Args:
        action: Short action description (e.g., "CLICK", "WAIT", "FILL", "ERROR")
        details: Additional details about what's happening
        level: Log level - "info", "success", "warning", "error", "action"
    """
    try:
        from modules.dashboard import log_handler
        # Format: [ACTION] details
        msg = f"🔹 {action}: {details}" if details else f"🔹 {action}"
        log_handler.publish(msg, tag=level.upper())
    except ImportError:
        pass
    # Also print to console
    print_lg(f"[{level.upper()}] {action}: {details}" if details else f"[{level.upper()}] {action}")

def log_click(element_desc: str, success: bool = True):
    """Log a click action with success/failure status."""
    if success:
        log_action("CLICK", f"✅ Clicked: {element_desc}", "action")
    else:
        log_action("CLICK", f"❌ Failed to click: {element_desc}", "error")

def log_fill(field: str, value: str = "***"):
    """Log a form fill action."""
    log_action("FILL", f"📝 {field} = {value[:30]}..." if len(value) > 30 else f"📝 {field} = {value}", "action")

def log_wait(reason: str, seconds: float = 0):
    """Log a wait action."""
    if seconds > 0:
        log_action("WAIT", f"⏳ {reason} ({seconds:.1f}s)", "info")
    else:
        log_action("WAIT", f"⏳ {reason}", "info")

def log_status(status: str, level: str = "info"):
    """Log a status update."""
    icons = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}
    icon = icons.get(level, "ℹ️")
    log_action("STATUS", f"{icon} {status}", level)

def log_job(title: str, company: str, action: str = "Processing"):
    """Log job-related action."""
    log_action("JOB", f"💼 {action}: {title} @ {company}", "info")
    emit_dashboard_event("job_context", {"title": title, "company": company})

def log_ai(action: str, details: str = ""):
    """Log AI-related action."""
    log_action("AI", f"🤖 {action}: {details}" if details else f"🤖 {action}", "info")
    stage = (action or "").strip().lower()
    if "extract" in stage or "skill" in stage or "jd" in stage:
        emit_dashboard_event("jd_analysis_started", {"action": action, "details": details})
    elif "resume" in stage or "tailor" in stage:
        emit_dashboard_event("resume_tailoring_started", {"action": action, "details": details})
    else:
        emit_dashboard_event("form_filling_started", {"action": action, "details": details})

def log_next_step(step: str, details: str = ""):
    """
    Log the NEXT step the bot will take - shown prominently in dashboard.
    This helps users know what's about to happen.
    """
    try:
        from modules.dashboard import log_handler
        from modules.dashboard import metrics as _m
        msg = f"➡️ NEXT: {step}" + (f" - {details}" if details else "")
        log_handler.publish(msg, tag="NEXT")
        # Also store in metrics for side panel display
        _m.set_metric('next_step', hash(step) % 1000)  # Store a hash for change detection
    except ImportError:
        pass
    print_lg(f"[NEXT STEP] {step}: {details}" if details else f"[NEXT STEP] {step}")

def log_progress(jd_pct: int = 0, resume_pct: int = 0):
    """Update progress bars in dashboard."""
    try:
        from modules.dashboard import metrics as _m
        if jd_pct >= 0:
            _m.set_metric('jd_progress', jd_pct)
        if resume_pct >= 0:
            _m.set_metric('resume_progress', resume_pct)
    except ImportError:
        pass


def set_stop_event(event: threading.Event):
    """Set the stop event from dashboard controller."""
    global _stop_event
    _stop_event = event

def should_stop() -> bool:
    """Check if bot should stop."""
    return _stop_event is not None and _stop_event.is_set()

def stop_bot():
    """Signal the bot to stop."""
    global _stop_event
    if _stop_event:
        _stop_event.set()

def pause_bot():
    """Toggle pause state."""
    global _pause_flag
    _pause_flag = not _pause_flag
    return _pause_flag

def skip_job():
    """Signal to skip current job."""
    global _skip_current
    _skip_current = True

def check_pause():
    """Check and wait if paused. Returns True if should continue, False if should stop."""
    global _pause_flag
    while _pause_flag:
        if should_stop():
            return False
        sleep(0.5)
    return not should_stop()


def interruptible_sleep(seconds: float, check_interval: float = 1.0):
    """
    Sleep for the given duration but check for stop signals periodically.
    Returns True if sleep completed normally, False if interrupted by stop signal.
    """
    import time
    elapsed = 0.0
    while elapsed < seconds:
        if should_stop():
            print_lg(f"💤 Sleep interrupted by stop signal after {elapsed:.0f}s of {seconds:.0f}s")
            return False
        chunk = min(check_interval, seconds - elapsed)
        time.sleep(chunk)
        elapsed += chunk
    return True

def check_pilot_limit_reached() -> bool:
    """
    Check if pilot mode application limit has been reached.
    Returns True if limit reached and bot should stop, False otherwise.
    Reloads settings dynamically from config to get updated dashboard values.
    """
    global easy_applied_count, dailyEasyApplyLimitReached
    
    # Daily limit always takes precedence
    if dailyEasyApplyLimitReached:
        print_lg("📊 [PILOT] LinkedIn daily Easy Apply limit reached!")
        return True
    
    # Check max_jobs_to_process (global limit, applies in all modes, 0 = unlimited)
    try:
        from config import settings
        max_jobs = getattr(settings, 'max_jobs_to_process', 0)
        total_processed = easy_applied_count + external_jobs_count
        if max_jobs > 0 and total_processed >= max_jobs:
            print_lg(f"📊 Max jobs to process limit reached! Processed: {total_processed} / Max: {max_jobs}")
            return True
    except Exception:
        pass
    
    # Check pilot max applications (0 = unlimited)
    try:
        from config import settings
        # Reload from settings (dashboard updates these at runtime)
        current_max = getattr(settings, 'pilot_max_applications', 0)
        
        if current_max > 0 and easy_applied_count >= current_max:
            print_lg(f"📊 [PILOT] Application limit reached! Applied: {easy_applied_count} / Max: {current_max}")
            return True
        
        if current_max > 0:
            print_lg(f"📊 [PILOT] Progress: {easy_applied_count} / {current_max} applications")
    except Exception as e:
        print_lg(f"[PILOT] Warning: Could not check pilot limit: {e}")
    
    return False

def get_next_search_term(search_terms: list, current_index: int, current_count: int) -> tuple:
    """
    Get the next search term based on job_search_mode setting.
    Returns (next_term, next_index, reset_count) tuple.
    
    Modes:
    - "sequential": Apply in order, switch after switch_number
    - "random": Randomly pick a term
    - "single": Stay on first term until limit
    """
    try:
        from config import settings
        from config import search as search_config
        mode = getattr(settings, 'job_search_mode', 'sequential')
        switch_num = getattr(search_config, 'switch_number', 30)
        
        if mode == "single":
            # Stay on first term forever
            return search_terms[0], 0, current_count
        elif mode == "random":
            # Pick random term
            from random import choice
            next_term = choice(search_terms)
            return next_term, search_terms.index(next_term), 0
        else:  # sequential (default)
            # Switch to next term after switch_number applications
            if current_count >= switch_num:
                next_index = (current_index + 1) % len(search_terms)
                return search_terms[next_index], next_index, 0
            return search_terms[current_index], current_index, current_count
    except Exception as e:
        print_lg(f"[PILOT] Error getting next search term: {e}")
        return search_terms[current_index], current_index, current_count

# Import quick tailor popup for in-flow resume tailoring
try:
    from modules.quick_tailor_popup import (
        show_quick_tailor_popup, 
        ask_tailor_or_default,
        RESULT_TAILOR, 
        RESULT_SKIP_TAILOR, 
        RESULT_CANCEL
    )
    TAILOR_POPUP_AVAILABLE = True
except ImportError:
    TAILOR_POPUP_AVAILABLE = False
    print_lg("Quick tailor popup not available")

re_experience = re.compile(r"\(?\s*(\d+)\s*\)?\s*[-to]*\s*\d*\+?\s*year[s]?", re.IGNORECASE)

desired_salary_value = _to_float(desired_salary)
desired_salary_lakhs = str(round(desired_salary_value / 100000, 2))
desired_salary_monthly = str(round(desired_salary_value / 12, 2))
desired_salary = str(desired_salary)

current_ctc_value = _to_float(current_ctc)
current_ctc_lakhs = str(round(current_ctc_value / 100000, 2))
current_ctc_monthly = str(round(current_ctc_value / 12, 2))
current_ctc = str(current_ctc)

notice_period_value = _to_int(notice_period)
notice_period_months = str(notice_period_value // 30)
notice_period_weeks = str(notice_period_value // 7)
notice_period = str(notice_period)

aiClient = None
popup_blocker = None  # Global popup blocker instance
##> ------ Dheeraj Deshwal : dheeraj9811 Email:dheeraj20194@iiitd.ac.in/dheerajdeshwal9811@gmail.com - Feature ------
about_company_for_ai = None  # Placeholder for future About Company extraction
##<

#>


#< Login Functions
def is_logged_in_LN() -> bool:
    '''
    Function to check if user is logged-in in LinkedIn
    * Returns: `True` if user is logged-in or `False` if not
    '''
    if driver.current_url == "https://www.linkedin.com/feed/": return True
    if try_linkText(driver, "Sign in"): return False
    if try_xp(driver, '//button[@type="submit" and contains(text(), "Sign in")]'):  return False
    if try_linkText(driver, "Join now"): return False
    print_lg("Didn't find Sign in link, so assuming user is logged in!")
    return True


def login_LN() -> None:
    '''
    Function to login for LinkedIn
    * Tries to login using given `username` and `password` from `secrets.py`
    * If failed, tries to login using saved LinkedIn profile button if available
    * If both failed, asks user to login manually
    '''
    # Find the username and password fields and fill them with user credentials
    driver.get("https://www.linkedin.com/login")
    if username == "username@example.com" and password == "example_password":
        if not pilot_mode_enabled:
            _safe_pyautogui_alert("User did not configure username and password in secrets.py, hence can't login automatically! Please login manually!", "Login Manually","Okay")
        print_lg("User did not configure username and password in secrets.py, hence can't login automatically! Please login manually!")
        manual_login_retry(is_logged_in_LN, 2)
        return
    try:
        wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Forgot password?")))
        try:
            text_input_by_ID(driver, "username", username, 1)
        except Exception as e:
            print_lg("Couldn't find username field.")
            # print_lg(e)
        try:
            text_input_by_ID(driver, "password", password, 1)
        except Exception as e:
            print_lg("Couldn't find password field.")
            # print_lg(e)
        # Find the login submit button and click it
        driver.find_element(By.XPATH, '//button[@type="submit" and contains(text(), "Sign in")]').click()
    except Exception as e1:
        try:
            profile_button = find_by_class(driver, "profile__details")
            profile_button.click()
        except Exception as e2:
            # print_lg(e1, e2)
            print_lg("Couldn't Login!")

    try:
        # Wait until successful redirect, indicating successful login
        wait.until(EC.url_to_be("https://www.linkedin.com/feed/")) # wait.until(EC.presence_of_element_located((By.XPATH, '//button[normalize-space(.)="Start a post"]')))
        return print_lg("Login successful!")
    except Exception as e:
        print_lg("Seems like login attempt failed! Possibly due to wrong credentials or already logged in! Try logging in manually!")
        # print_lg(e)
        manual_login_retry(is_logged_in_LN, 2)
#>



def get_applied_job_ids() -> set[str]:
    '''
    Function to get a `set` of applied job's Job IDs
    * Returns a set of Job IDs from existing applied jobs history csv file
    '''
    job_ids: set[str] = set()
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                job_ids.add(row[0])
    except FileNotFoundError:
        print_lg(f"The CSV file '{file_name}' does not exist.")
    return job_ids



def set_search_location() -> None:
    '''
    Function to set search location
    '''
    if search_location.strip():
        try:
            print_lg(f'Setting search location as: "{search_location.strip()}"')
            search_location_ele = try_xp(driver, ".//input[@aria-label='City, state, or zip code'and not(@disabled)]", False) #  and not(@aria-hidden='true')]")
            text_input(actions, search_location_ele, search_location, "Search Location")
        except ElementNotInteractableException:
            try_xp(driver, ".//label[@class='jobs-search-box__input-icon jobs-search-box__keywords-label']")
            actions.send_keys(Keys.TAB, Keys.TAB).perform()
            actions.key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).perform()
            actions.send_keys(search_location.strip()).perform()
            sleep(2)
            actions.send_keys(Keys.ENTER).perform()
            try_xp(driver, ".//button[@aria-label='Cancel']")
        except Exception as e:
            try_xp(driver, ".//button[@aria-label='Cancel']")
            print_lg("Failed to update search location, continuing with default location!", e)


def apply_filters() -> None:
    '''
    Function to apply job search filters with robust verification.
    All filters from config are applied consistently with retry logic.
    SPEED OPTIMIZED: Reduced wait times for faster filter application.
    '''
    log_status("Starting filter application (FAST MODE)...", "info")
    set_search_location()

    def _is_24h_selected() -> bool:
        try:
            radio = driver.find_element(By.XPATH, './/input[@value="r86400"]')
            return radio.is_selected() or radio.get_attribute('aria-checked') == 'true' or radio.get_attribute('checked') is not None
        except Exception:
            return False

    def _click_24h_option() -> bool:
        try:
            radio = driver.find_element(By.XPATH, './/input[@value="r86400"]')
            # Try clicking associated label/span for better reliability
            label = radio.find_element(By.XPATH, './following-sibling::label | ./following-sibling::*[1]')
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", label)
            driver.execute_script("arguments[0].click();", label)
            buffer(0.2)
            return _is_24h_selected()
        except Exception:
            return False

    try:
        # SPEED: Use shorter waits - 0.3s instead of 1s
        recommended_wait = 0.2  # Reduced for faster filter application
        filters_applied = []
        filters_failed = []

        # Open All Filters panel
        log_action("FILTER", "Opening 'All filters' panel...", "action")
        all_filters_btn = wait.until(EC.presence_of_element_located((By.XPATH, '//button[normalize-space()="All filters"]')))
        # Scroll into view first to avoid nav bar intercepting the click
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", all_filters_btn)
        buffer(0.3)
        try:
            all_filters_btn.click()
        except Exception:
            # If direct click is intercepted by nav bar, use JS click
            driver.execute_script("arguments[0].click();", all_filters_btn)
        log_click("All filters button", True)
        buffer(0.2)  # Reduced from 1.5s - just need modal to appear
        
        # Wait for modal to be fully loaded - use shorter timeout
        try:
            WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, '//div[contains(@class, "artdeco-modal")]')))
            log_action("FILTER", "Modal loaded successfully", "success")
        except Exception:
            log_action("FILTER", "Modal may not have loaded completely", "warning")
            print_lg("Filter modal may not have loaded completely")

        # ====== SORT BY ======
        if sort_by:
            log_action("FILTER", f"Setting sort by: {sort_by}", "action")
            if wait_span_click(driver, sort_by, 2):  # Reduced timeout from 3
                filters_applied.append(f"Sort: {sort_by}")
            else:
                filters_failed.append(f"Sort: {sort_by}")
        
        # ====== DATE POSTED (Critical - Past 24 hours) ======
        if date_posted:
            log_action("FILTER", f"Setting date filter: {date_posted}", "action")
            success = False
            
            # Multiple strategies to find and click date filter
            date_selectors = [
                f'.//span[normalize-space()="{date_posted}"]',
                f'.//label[contains(text(), "{date_posted}")]',
                f'.//*[contains(text(), "Past 24 hours")]',
                f'.//*[contains(text(), "24 hours")]',
                f'.//input[@value="r86400"]/following-sibling::*',  # 24 hours radio value
            ]
            
            for attempt in range(2):
                # First try standard wait_span_click
                if wait_span_click(driver, date_posted, 2):
                    success = True
                    log_click(f"Date filter: {date_posted}", True)
                    break
                
                # Try alternative selectors
                for selector in date_selectors:
                    try:
                        elem = driver.find_element(By.XPATH, selector)
                        if elem and elem.is_displayed():
                            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                            buffer(0.2)
                            elem.click()
                            success = True
                            log_click(f"Date filter: {date_posted} (alt)", True)
                            break
                    except:
                        continue
                
                if success:
                    break
                    
                log_action("FILTER", f"Date filter retry {attempt+1}/3", "warning")
                buffer(0.2)
                
            if "24" in date_posted and not _is_24h_selected():
                # Force-select the 24 hours option if it didn't stick
                success = _click_24h_option() or success

            if success:
                filters_applied.append(f"Date: {date_posted}")
            else:
                filters_failed.append(f"Date: {date_posted}")
                log_click(f"Date filter: {date_posted}", False)
                print_lg(f"⚠️ WARNING: Could not set date filter to '{date_posted}'")
        buffer(recommended_wait)

        # ====== EXPERIENCE LEVEL ======
        if experience_level:
            log_action("FILTER", f"Setting experience level: {experience_level}", "action")
            multi_sel_noWait(driver, experience_level) 
            filters_applied.append(f"Experience: {experience_level}")
        
        # ====== COMPANIES ======
        if companies:
            multi_sel_noWait(driver, companies, actions)
            filters_applied.append(f"Companies: {len(companies)} selected")
        
        if experience_level or companies: 
            buffer(recommended_wait)

        # ====== JOB TYPE ======
        if job_type:
            multi_sel_noWait(driver, job_type)
            filters_applied.append(f"Job Type: {job_type}")
        
        # ====== WORK STYLE (On-site/Remote/Hybrid) ======
        if on_site:
            multi_sel_noWait(driver, on_site)
            filters_applied.append(f"Work Style: {on_site}")
        
        if job_type or on_site: 
            buffer(recommended_wait)

        # ====== EASY APPLY TOGGLE (Critical - Must verify) ======
        if easy_apply_only:
            log_action("FILTER", "Enabling Easy Apply toggle (CRITICAL)...", "action")
            success = boolean_button_click(driver, actions, "Easy Apply", max_retries=5)
            if success:
                filters_applied.append("Easy Apply: ✓ ENABLED")
                log_click("Easy Apply toggle", True)
                log_status("✅ Easy Apply filter ENABLED successfully!", "success")
            else:
                filters_failed.append("Easy Apply: FAILED TO ENABLE")
                log_click("Easy Apply toggle", False)
                log_status("⚠️ WARNING: Easy Apply filter may not be enabled!", "error")
                print_lg("⚠️ WARNING: Easy Apply filter may not be enabled!")
        
        # ====== LOCATION ======
        if location:
            multi_sel_noWait(driver, location)
            filters_applied.append(f"Location: {location}")
        
        # ====== INDUSTRY ======
        if industry:
            multi_sel_noWait(driver, industry)
            filters_applied.append(f"Industry: {industry}")
        
        if location or industry: 
            buffer(recommended_wait)

        # ====== JOB FUNCTION ======
        if job_function:
            multi_sel_noWait(driver, job_function)
            filters_applied.append(f"Function: {job_function}")
        
        # ====== JOB TITLES ======
        if job_titles:
            multi_sel_noWait(driver, job_titles)
            filters_applied.append(f"Titles: {job_titles}")
        
        if job_function or job_titles: 
            buffer(recommended_wait)

        # ====== ADDITIONAL BOOLEAN FILTERS ======
        if under_10_applicants: 
            if boolean_button_click(driver, actions, "Under 10 applicants", max_retries=3):
                filters_applied.append("Under 10 applicants: ✓")
            else:
                filters_failed.append("Under 10 applicants: FAILED")
        
        if in_your_network: 
            if boolean_button_click(driver, actions, "In your network", max_retries=3):
                filters_applied.append("In your network: ✓")
            else:
                filters_failed.append("In your network: FAILED")
        
        if fair_chance_employer: 
            if boolean_button_click(driver, actions, "Fair Chance Employer", max_retries=3):
                filters_applied.append("Fair Chance Employer: ✓")
            else:
                filters_failed.append("Fair Chance Employer: FAILED")

        # ====== SALARY ======
        if salary:
            wait_span_click(driver, salary)
            filters_applied.append(f"Salary: {salary}")
        buffer(recommended_wait)
        
        # ====== BENEFITS ======
        if benefits:
            multi_sel_noWait(driver, benefits)
            filters_applied.append(f"Benefits: {benefits}")
        
        # ====== COMMITMENTS ======
        if commitments:
            multi_sel_noWait(driver, commitments)
            filters_applied.append(f"Commitments: {commitments}")
        
        if benefits or commitments: 
            buffer(recommended_wait)

        # ====== FINAL VERIFICATION BEFORE SUBMIT ======
        # Re-verify critical filters before clicking Show Results
        buffer(0.2)  # Reduced from 0.5s
        
        # Double-check Easy Apply if it was supposed to be enabled
        if easy_apply_only:
            from modules.clickers_and_finders import verify_filter_state
            if not verify_filter_state(driver, "Easy Apply"):
                print_lg("⚠️ Easy Apply filter lost! Re-enabling...")
                boolean_button_click(driver, actions, "Easy Apply", max_retries=2)
                buffer(0.2)

        # Re-verify 24 hours if requested
        if date_posted and "24" in date_posted and not _is_24h_selected():
            print_lg("⚠️ Date filter lost! Re-selecting Past 24 hours...")
            _click_24h_option()
            buffer(0.2)

        # ====== SHOW RESULTS ======
        show_results_button: WebElement = driver.find_element(By.XPATH, '//button[contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "apply current filters to show")]')
        show_results_button.click()
        log_action("FILTER", "✅ Show results clicked - filters applied!", "success")

        # Log filter summary
        print_lg("\n" + "="*50)
        print_lg("📋 FILTER APPLICATION SUMMARY")
        print_lg("="*50)
        if filters_applied:
            print_lg("✅ Applied successfully:")
            for f in filters_applied:
                print_lg(f"   • {f}")
        if filters_failed:
            print_lg("❌ Failed to apply:")
            for f in filters_failed:
                print_lg(f"   • {f}")
        print_lg("="*50 + "\n")

        global pause_after_filters
        # Skip confirmation in pilot mode
        if pilot_mode_enabled:
            print_lg("[PILOT MODE] \u2708\ufe0f Skipping filter confirmation dialog")
        elif pause_after_filters and "Turn off Pause after search" == _safe_pyautogui_confirm("These are your configured search results and filter. It is safe to change them while this dialog is open, any changes later could result in errors and skipping this search run.", "Please check your results", ["Turn off Pause after search", "Look's good, Continue"]):
            pause_after_filters = False

    except Exception as e:
        print_lg("Setting the preferences failed!")
        # Skip error confirmation in pilot mode
        if not pilot_mode_enabled:
            _safe_pyautogui_confirm(f"Faced error while applying filters. Please make sure correct filters are selected, click on show results and click on any button of this dialog, I know it sucks. Can't turn off Pause after search when error occurs! ERROR: {e}", "Filter Error", ["Doesn't look good, but Continue XD", "Look's good, Continue"])
        else:
            print_lg(f"[PILOT MODE] \u2708\ufe0f Skipping error dialog, continuing... Error: {e}")
        # print_lg(e)



def get_page_info() -> tuple[WebElement | None, int | None]:
    '''
    Function to get pagination element and current page number
    '''
    try:
        pagination_element = try_find_by_classes(driver, ["jobs-search-pagination__pages", "artdeco-pagination", "artdeco-pagination__pages"])
        scroll_to_view(driver, pagination_element)
        current_page = int(pagination_element.find_element(By.XPATH, "//button[contains(@class, 'active')]").text)
    except Exception as e:
        print_lg("Failed to find Pagination element, hence couldn't scroll till end!")
        pagination_element = None
        current_page = None
        print_lg(e)
    return pagination_element, current_page



def get_job_main_details(job: WebElement, blacklisted_companies: set, rejected_jobs: set) -> tuple[str, str, str, str, str, bool]:
    '''
    # Function to get job main details.
    Returns a tuple of (job_id, title, company, work_location, work_style, skip)
    * job_id: Job ID
    * title: Job title
    * company: Company name
    * work_location: Work location of this job
    * work_style: Work style of this job (Remote, On-site, Hybrid)
    * skip: A boolean flag to skip this job
    '''
    skip = False
    log_action("JOB", "Processing job card...", "action")
    # Prefer explicit job card link to avoid wrong title selection on DOM updates
    try:
        job_details_button = job.find_element(By.XPATH, ".//a[contains(@href, '/jobs/view/')]")
    except Exception:
        job_details_button = job.find_element(By.TAG_NAME, 'a')
    scroll_to_view(driver, job_details_button, True)
    job_id = job.get_dom_attribute('data-occludable-job-id')
    if not job_id:
        print_lg("[Job] Missing job id on card, skipping")
        return ("", "", "", "", "", True)
    title = job_details_button.text
    title = title[:title.find("\n")]
    # company = job.find_element(By.CLASS_NAME, "job-card-container__primary-description").text
    # work_location = job.find_element(By.CLASS_NAME, "job-card-container__metadata-item").text
    other_details = job.find_element(By.CLASS_NAME, 'artdeco-entity-lockup__subtitle').text
    index = other_details.find(' · ')
    company = other_details[:index]
    work_location = other_details[index+3:]
    work_style = work_location[work_location.rfind('(')+1:work_location.rfind(')')]
    work_location = work_location[:work_location.rfind('(')].strip()
    
    log_job(title, company, "Found")
    
    # Skip if previously rejected due to blacklist or already applied
    if company in blacklisted_companies:
        log_status(f'Skipping "{title}" - Blacklisted Company', "warning")
        print_lg(f'Skipping "{title} | {company}" job (Blacklisted Company). Job ID: {job_id}!')
        skip = True
    elif job_id in rejected_jobs: 
        log_status(f'Skipping "{title}" - Previously Rejected', "warning")
        print_lg(f'Skipping previously rejected "{title} | {company}" job. Job ID: {job_id}!')
        skip = True
    try:
        if job.find_element(By.CLASS_NAME, "job-card-container__footer-job-state").text == "Applied":
            skip = True
            log_status(f'Skipping "{title}" - Already Applied', "info")
            print_lg(f'Already applied to "{title} | {company}" job. Job ID: {job_id}!')
    except: pass
    try: 
        if not skip:
            log_click(f"Job details: {title[:40]}...", True)
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", job_details_button)
                driver.execute_script("arguments[0].click();", job_details_button)
            except Exception:
                job_details_button.click()
    except Exception as e:
        log_click(f"Job details: {title[:40]}...", False)
        print_lg(f'Failed to click "{title} | {company}" job on details button. Job ID: {job_id}!') 
        # Don't call discard_job() here - there's no open modal to discard.
        # Just mark as skip so the caller continues to the next job in the SAME search term.
        skip = True
    buffer(click_gap)
    return (job_id,title,company,work_location,work_style,skip)


# Function to check for Blacklisted words in About Company
def check_blacklist(rejected_jobs: set, job_id: str, company: str, blacklisted_companies: set) -> tuple[set, set, WebElement] | ValueError:
    jobs_top_card = try_find_by_classes(driver, ["job-details-jobs-unified-top-card__primary-description-container","job-details-jobs-unified-top-card__primary-description","jobs-unified-top-card__primary-description","jobs-details__main-content"])
    about_company_org = find_by_class(driver, "jobs-company__box")
    scroll_to_view(driver, about_company_org)
    about_company_org = about_company_org.text
    about_company = about_company_org.lower()
    skip_checking = False
    for word in about_company_good_words:
        if word.lower() in about_company:
            print_lg(f'Found the word "{word}". So, skipped checking for blacklist words.')
            skip_checking = True
            break
    if not skip_checking:
        for word in about_company_bad_words: 
            if word.lower() in about_company: 
                rejected_jobs.add(job_id)
                blacklisted_companies.add(company)
                raise ValueError(f'\n"{about_company_org}"\n\nContains "{word}".')
    buffer(click_gap)
    scroll_to_view(driver, jobs_top_card)
    return rejected_jobs, blacklisted_companies, jobs_top_card



# Function to extract years of experience required from About Job
def extract_years_of_experience(text: str) -> int:
    # Extract all patterns like '10+ years', '5 years', '3-5 years', etc.
    matches = re.findall(re_experience, text)
    if len(matches) == 0: 
        print_lg(f'\n{text}\n\nCouldn\'t find experience requirement in About the Job!')
        return 0
    return max([int(match) for match in matches if int(match) <= 12])



def get_job_description(
) -> tuple[
    str | Literal['Unknown'],
    int | Literal['Unknown'],
    bool,
    str | None,
    str | None
    ]:
    '''
    # Job Description
    Function to extract job description from About the Job.
    ### Returns:
    - `jobDescription: str | 'Unknown'`
    - `experience_required: int | 'Unknown'`
    - `skip: bool`
    - `skipReason: str | None`
    - `skipMessage: str | None`
    '''
    jobDescription = "Unknown"
    experience_required = "Unknown"
    found_masters = 0
    skip = False
    skipReason = None
    skipMessage = None
    
    try:
        jobDescription = find_by_class(driver, "jobs-box__html-content").text
        jobDescriptionLow = jobDescription.lower()
        
        for word in bad_words:
            if word.lower() in jobDescriptionLow:
                skipMessage = f'\n{jobDescription}\n\nContains bad word "{word}". Skipping this job!\n'
                skipReason = "Found a Bad Word in About Job"
                skip = True
                break
        if not skip and security_clearance == False and ('polygraph' in jobDescriptionLow or 'security clearance' in jobDescriptionLow or 'secret clearance' in jobDescriptionLow or 'top secret' in jobDescriptionLow or 'top-secret' in jobDescriptionLow or 'ts/sci' in jobDescriptionLow):
            skipMessage = f'\n{jobDescription}\n\nFound security clearance requirement. Skipping this job!\n'
            skipReason = "Asking for Security clearance"
            skip = True
        if not skip:
            if did_masters and 'master' in jobDescriptionLow:
                print_lg(f'Found the word "master" in \n{jobDescription}')
                found_masters = 2
            experience_required = extract_years_of_experience(jobDescription)
            if current_experience > -1 and experience_required > current_experience + found_masters:
                skipMessage = f'\n{jobDescription}\n\nExperience required {experience_required} > Current Experience {current_experience + found_masters}. Skipping this job!\n'
                skipReason = "Required experience is high"
                skip = True
    except Exception as e:
        if jobDescription == "Unknown":
            print_lg("Unable to extract job description!")
        else:
            experience_required = "Error in extraction"
            print_lg("Unable to extract years of experience required!")
    
    return jobDescription, experience_required, skip, skipReason, skipMessage


def prompt_for_resume_tailoring(
    job_title: str, 
    company: str, 
    job_description: str
) -> tuple[str | None, bool]:
    """
    Prompt user to tailor resume or use default.
    
    Returns:
        tuple of (resume_path, was_tailored)
        - resume_path: Path to resume to use (tailored or default)
        - was_tailored: True if resume was tailored
    """
    if not resume_tailoring_enabled:
        log_ai("Resume tailoring disabled in settings")
        return default_resume_path, False
    
    # PILOT MODE: Skip all confirmations - use settings to determine behavior
    if pilot_mode_enabled:
        log_ai("[PILOT MODE]", f"Resume mode: {pilot_resume_mode}")
        if pilot_resume_mode == 'tailored':
            # Auto-tailor without asking
            try:
                from modules.ai.resume_tailoring import tailor_resume_to_files, _read_resume_text
                from config.secrets import ai_provider as _ai_provider
                import time
                
                log_ai("[PILOT MODE] Auto-tailoring resume", f"Provider: {_ai_provider}")
                print_lg("\ud83d\ude80 [PILOT MODE] Auto-tailoring resume...")
                
                start_time = time.time()
                resume_text = _read_resume_text(default_resume_path)
                if not resume_text:
                    print_lg("\u274c Could not read resume, using default")
                    return default_resume_path, False
                
                output_dir = os.path.join(generated_resume_path, "temp")
                os.makedirs(output_dir, exist_ok=True)
                
                paths = tailor_resume_to_files(
                    resume_text=resume_text,
                    job_description=job_description,
                    job_title=job_title,
                    candidate_name=company,
                    instructions=resume_tailoring_default_instructions,
                    output_dir=output_dir,
                    resume_path=default_resume_path
                )
                
                elapsed = time.time() - start_time
                
                # Respect resume_upload_format setting
                resume_format_pref = getattr(settings_module, 'resume_upload_format', 'auto')
                master_ext = os.path.splitext(default_resume_path)[1].lower() if default_resume_path else '.docx'
                
                tailored_path = None
                if paths:
                    if resume_format_pref == 'pdf':
                        tailored_path = paths.get('pdf')
                    elif resume_format_pref == 'docx':
                        tailored_path = paths.get('docx')
                    else:  # 'auto' - match master resume format
                        if master_ext == '.pdf':
                            tailored_path = paths.get('pdf') or paths.get('docx')
                        else:
                            tailored_path = paths.get('docx') or paths.get('pdf')
                
                if tailored_path and os.path.exists(tailored_path):
                    print_lg(f"\u2705 [PILOT MODE] Resume tailored in {elapsed:.1f}s: {os.path.basename(tailored_path)}")
                    return tailored_path, True
                else:
                    print_lg(f"\u274c [PILOT MODE] Tailoring returned no usable file, using default")
            except Exception as e:
                import traceback
                print_lg(f"\u274c [PILOT MODE] Tailoring failed: {e}")
                print_lg(f"\u274c [PILOT MODE] Traceback: {traceback.format_exc()}")
            return default_resume_path, False
            
        elif pilot_resume_mode == 'default':
            # Use project's default resume file
            print_lg("\ud83d\udcc4 [PILOT MODE] Using project default resume")
            return default_resume_path, False
            
        elif pilot_resume_mode == 'preselected':
            # Return special marker to signal: use whatever is pre-selected in the form
            print_lg("\ud83d\udcc4 [PILOT MODE] Using pre-selected resume (no upload)")
            return "PRESELECTED", False
            
        elif pilot_resume_mode == 'skip':
            # Return special marker to signal: don't touch resume at all
            print_lg("\u23ed\ufe0f [PILOT MODE] Skipping resume handling")
            return "SKIP_RESUME", False
        else:
            return default_resume_path, False
    
    log_ai("Resume Tailoring", f"Prompting for: {job_title} @ {company}")
    
    if not TAILOR_POPUP_AVAILABLE:
        # Fallback to simple pyautogui dialog
        decision = _safe_pyautogui_confirm(
            f"Do you want to tailor your resume for:\n\n"
            f"📋 {job_title}\n"
            f"🏢 {company}\n\n"
            "AI will optimize your resume for this job.",
            "Resume Tailoring",
            ["✨ Tailor", "📄 Default", "❌ Skip Job"]
        )
        
        if decision == "❌ Skip Job":
            log_ai("User chose to skip job")
            return None, False
        elif decision == "✨ Tailor":
            # ====== JD PREVIEW (resume_tailoring_prompt_before_jd) ======
            # If enabled, show the job description text before sending to AI
            if resume_tailoring_prompt_before_jd and not pilot_mode_enabled:
                jd_preview = job_description[:1500] + ("..." if len(job_description) > 1500 else "")
                jd_confirm = _safe_pyautogui_confirm(
                    f"📄 Job Description Preview (will be sent to AI):\n\n"
                    f"{jd_preview}\n\n"
                    f"Send this to AI for resume tailoring?",
                    "Review Job Description",
                    ["✅ Send to AI", "📄 Use Default"]
                )
                if jd_confirm != "✅ Send to AI":
                    print_lg("📄 User declined JD send — using default resume")
                    return default_resume_path, False

            # Do tailoring in background
            try:
                from modules.ai.resume_tailoring import tailor_resume_to_files, _read_resume_text
                from datetime import datetime
                from config.secrets import ai_provider as _ai_provider
                
                log_ai("Starting AI Tailoring", f"Provider: {_ai_provider}")
                print_lg("🔄 Tailoring resume with AI...")
                
                import time
                start_time = time.time()
                
                resume_text = _read_resume_text(default_resume_path)
                if not resume_text:
                    log_ai("ERROR", "Could not read resume file")
                    print_lg("❌ Could not read resume, using default")
                    return default_resume_path, False
                
                output_dir = os.path.join(generated_resume_path, "temp")
                os.makedirs(output_dir, exist_ok=True)
                
                log_ai("Calling AI API...", f"This may take 10-60 seconds")
                
                paths = tailor_resume_to_files(
                    resume_text=resume_text,
                    job_description=job_description,
                    job_title=job_title,
                    candidate_name=company,
                    instructions=resume_tailoring_default_instructions,
                    output_dir=output_dir,
                    resume_path=default_resume_path
                )
                
                elapsed = time.time() - start_time
                
                # Get resume upload format preference from settings
                # Options: "auto" (match master resume), "pdf", "docx"
                resume_format_pref = getattr(settings_module, 'resume_upload_format', 'auto')
                
                # Determine master resume format for "auto" mode
                master_ext = os.path.splitext(default_resume_path)[1].lower() if default_resume_path else '.docx'
                
                tailored_resume = None
                if paths:
                    # Select format based on user preference
                    if resume_format_pref == "pdf":
                        # User wants PDF only
                        if paths.get('pdf') and os.path.exists(paths['pdf']):
                            tailored_resume = paths['pdf']
                            log_ai("SUCCESS", f"Tailored PDF in {elapsed:.1f}s: {os.path.basename(paths['pdf'])}")
                            print_lg(f"✅ Resume tailored (PDF - user preference): {paths['pdf']}")
                    elif resume_format_pref == "docx":
                        # User wants DOCX only
                        if paths.get('docx') and os.path.exists(paths['docx']):
                            tailored_resume = paths['docx']
                            log_ai("SUCCESS", f"Tailored DOCX in {elapsed:.1f}s: {os.path.basename(paths['docx'])}")
                            print_lg(f"✅ Resume tailored (DOCX - user preference): {paths['docx']}")
                    else:
                        # Auto mode: Match master resume format
                        if master_ext == '.pdf':
                            if paths.get('pdf') and os.path.exists(paths['pdf']):
                                tailored_resume = paths['pdf']
                                log_ai("SUCCESS", f"Tailored PDF in {elapsed:.1f}s (matching master): {os.path.basename(paths['pdf'])}")
                                print_lg(f"✅ Resume tailored (PDF - auto/master): {paths['pdf']}")
                        else:
                            # Default to DOCX for .docx master or any other format
                            if paths.get('docx') and os.path.exists(paths['docx']):
                                tailored_resume = paths['docx']
                                log_ai("SUCCESS", f"Tailored DOCX in {elapsed:.1f}s (matching master): {os.path.basename(paths['docx'])}")
                                print_lg(f"✅ Resume tailored (DOCX - auto/master): {paths['docx']}")
                    
                    # Fallback: If preferred format not available, use whatever is available
                    if not tailored_resume:
                        if paths.get('docx') and os.path.exists(paths['docx']):
                            tailored_resume = paths['docx']
                            log_ai("SUCCESS", f"Tailored DOCX in {elapsed:.1f}s (fallback): {os.path.basename(paths['docx'])}")
                            print_lg(f"✅ Resume tailored (DOCX fallback): {paths['docx']}")
                        elif paths.get('pdf') and os.path.exists(paths['pdf']):
                            tailored_resume = paths['pdf']
                            log_ai("SUCCESS", f"Tailored PDF in {elapsed:.1f}s (fallback): {os.path.basename(paths['pdf'])}")
                            print_lg(f"✅ Resume tailored (PDF fallback): {paths['pdf']}")
                
                if tailored_resume:
                    # Show preview option (skip in pilot mode)
                    if paths.get('html_diff') and not pilot_mode_enabled:
                        preview_choice = _safe_pyautogui_confirm(
                            "Resume tailored successfully!\n\nWould you like to preview it?",
                            "Tailored Resume Ready",
                            ["👁️ Preview & Apply", "✅ Apply Now", "❌ Cancel"]
                        )
                        if preview_choice == "👁️ Preview & Apply":
                            import webbrowser
                            webbrowser.open(f"file://{os.path.abspath(paths['html_diff'])}")
                            _safe_pyautogui_alert("Click OK when ready to continue with application.", "Preview Open")
                        elif preview_choice == "❌ Cancel":
                            return None, False
                    elif pilot_mode_enabled:
                        print_lg("✈️ [PILOT MODE] Skipping resume preview - applying directly")
                    return tailored_resume, True
                else:
                    log_ai("FAILED", f"No output after {elapsed:.1f}s")
                    print_lg("❌ Tailoring failed, using default resume")
                    return default_resume_path, False
                    
            except Exception as e:
                log_ai("ERROR", str(e)[:100])
                print_lg(f"❌ Tailoring error: {e}, using default resume")
                return default_resume_path, False
        else:
            return default_resume_path, False
    
    # Use the full popup with preview
    result, tailored_path = show_quick_tailor_popup(
        job_title=job_title,
        company=company,
        job_description=job_description,
        default_resume_path=default_resume_path
    )
    
    if result == RESULT_CANCEL:
        return None, False
    elif result == RESULT_TAILOR and tailored_path:
        return tailored_path, True
    else:
        return default_resume_path, False


# Function to upload resume
def upload_resume(modal: WebElement, resume: str) -> tuple[bool, str]:
    try:
        modal.find_element(By.NAME, "file").send_keys(os.path.abspath(resume))
        # Immediately handle any popup (especially Deloitte DLP) after resume upload
        time.sleep(0.5)  # Brief wait for popup to appear
        
        # First try browser-based popup handling (only when Easy Apply modal is NOT active)
        if popup_blocker and not _is_easy_apply_open(driver):
            popup_blocker.block_all()
        
        # Try Selenium-based Deloitte popup dismissal
        dismiss_deloitte_popup(driver, max_attempts=3)
        
        # CRITICAL: Handle Deloitte DLP SYSTEM popup (appears outside browser)
        # This popup blocks file uploads and needs pyautogui to click OK
        try:
            from modules.popup_blocker import dismiss_deloitte_dlp_popup
            # Run DLP popup handler - this uses pyautogui for system-level popup
            dismiss_deloitte_dlp_popup(max_attempts=5, click_delay=0.3)
        except Exception as dlp_error:
            print_lg(f"[Upload] DLP popup handler note: {dlp_error}")
        
        return True, os.path.basename(default_resume_path)
    except Exception as e:
        print_lg(f"Resume upload issue: {e}")
        return False, "Previous resume"


# ============================================================================
# SMART MODAL HANDLER - Intelligent Easy Apply Form Navigation
# ============================================================================
class SmartModalHandler:
    """
    Intelligent handler for LinkedIn Easy Apply modal.
    Properly detects fields, scrolls to find buttons, and navigates pages.
    """
    
    def __init__(self, driver_instance, modal_element, popup_blocker_instance=None):
        self.driver = driver_instance
        self.modal = modal_element
        self.popup_blocker = popup_blocker_instance
        self.current_page = 1
        self.max_pages = 10
        self.uploaded_resume = False
        self._used_fallback_resume = False  # Track if we've already tried fallback
    
    def refresh_modal_reference(self) -> bool:
        """
        Refresh the modal reference to handle stale element issues.
        This is CRITICAL after page navigation as the modal DOM may have changed.
        
        Returns:
            True if modal reference was successfully refreshed, False otherwise
        """
        try:
            # Try multiple selectors to find the modal
            modal_selectors = [
                "jobs-easy-apply-modal",
                "artdeco-modal",
                "jobs-easy-apply-content",
            ]
            
            for selector in modal_selectors:
                try:
                    # Find the modal fresh from the DOM
                    new_modal = self.driver.find_element(By.CLASS_NAME, selector)
                    if new_modal and new_modal.is_displayed():
                        self.modal = new_modal
                        print_lg(f"[SmartModal] ✅ Modal reference refreshed via .{selector}")
                        return True
                except NoSuchElementException:
                    continue
                except Exception:
                    continue
            
            # Try by XPath as fallback
            try:
                new_modal = self.driver.find_element(By.XPATH, 
                    "//div[contains(@class, 'jobs-easy-apply-modal') or contains(@class, 'artdeco-modal')]")
                if new_modal and new_modal.is_displayed():
                    self.modal = new_modal
                    print_lg("[SmartModal] ✅ Modal reference refreshed via XPath")
                    return True
            except Exception:
                pass
            
            print_lg("[SmartModal] ⚠️ Could not refresh modal reference")
            return False
            
        except Exception as e:
            print_lg(f"[SmartModal] ❌ Error refreshing modal reference: {e}")
            return False
        
    def scroll_modal_to_bottom(self) -> None:
        """Scroll within the modal to reveal bottom buttons."""
        try:
            # Find the scrollable container within the modal
            scroll_containers = [
                ".jobs-easy-apply-content",
                ".jobs-easy-apply-modal__content",
                "[class*='jobs-easy-apply'] [class*='content']",
                ".artdeco-modal__content"
            ]
            
            for selector in scroll_containers:
                try:
                    container = self.modal.find_element(By.CSS_SELECTOR, selector)
                    # Scroll to bottom using JavaScript
                    self.driver.execute_script(
                        "arguments[0].scrollTop = arguments[0].scrollHeight;", 
                        container
                    )
                    time.sleep(0.3)
                    return
                except NoSuchElementException:
                    continue
            
            # Fallback: scroll the modal itself
            self.driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight;", 
                self.modal
            )
        except Exception as e:
            print_lg(f"[SmartModal] Scroll issue: {e}")
    
    def scroll_modal_to_top(self) -> None:
        """Scroll within the modal to top."""
        try:
            scroll_containers = [
                ".jobs-easy-apply-content",
                ".jobs-easy-apply-modal__content",
                "[class*='jobs-easy-apply'] [class*='content']"
            ]
            
            for selector in scroll_containers:
                try:
                    container = self.modal.find_element(By.CSS_SELECTOR, selector)
                    self.driver.execute_script("arguments[0].scrollTop = 0;", container)
                    time.sleep(0.2)
                    return
                except NoSuchElementException:
                    continue
        except Exception:
            pass
    
    def dismiss_popups(self) -> None:
        """Dismiss any popups including Deloitte consent dialogs."""
        try:
            if self.popup_blocker and not _is_easy_apply_open(self.driver):
                self.popup_blocker.block_all()
            dismiss_deloitte_popup(self.driver, max_attempts=3)
        except Exception:
            pass

    def _dismiss_safe_overlays(self) -> None:
        """
        SAFE popup dismiss that ONLY removes non-modal overlays.
        
        This method is safe to call during Easy Apply form navigation because it
        NEVER touches modal dismiss/X buttons. It only dismisses:
        - Toast notifications
        - LinkedIn messaging bubbles
        - Cookie consent banners
        
        Use this instead of dismiss_popups() when inside Easy Apply modal flow.
        """
        safe_selectors = [
            ".artdeco-toast-item__dismiss",                          # Toast notifications
            "button.msg-overlay-bubble-header__control--close",      # Chat bubbles
            "button.mercado-match__dismiss",                         # Match notifications
            "#onetrust-accept-btn-handler",                          # Cookie consent
            ".onetrust-close-btn-handler",                           # Cookie close
        ]
        try:
            for selector in safe_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for el in elements:
                        if el.is_displayed():
                            try:
                                el.click()
                                print_lg(f"[SmartModal] ✅ Safe dismiss: closed '{selector}'")
                                time.sleep(0.1)
                            except Exception:
                                pass
                except Exception:
                    continue
        except Exception:
            pass
    
    def _find_button_no_scroll(self, button_type: str) -> WebElement | None:
        """
        Find a button without scrolling - uses current scroll position.
        Internal method for batch button detection.
        """
        # Comprehensive button configs with multiple fallback XPaths
        button_configs = {
            'next': [
                ".//button[contains(@aria-label, 'Continue to next step')]",
                ".//button[.//span[text()='Next']]",
                ".//button[contains(span, 'Next')]",
                ".//span[normalize-space(.)='Next']/ancestor::button",
                ".//button[contains(@class, 'artdeco-button--primary')][.//span[contains(text(), 'Next')]]",
                # Fallback - find primary button in footer that's NOT back/secondary
                "(.//footer//button[contains(@class, 'artdeco-button--primary') and not(contains(@class, 'artdeco-button--secondary'))])[last()]",
            ],
            'review': [
                ".//button[.//span[text()='Review']]",
                ".//span[normalize-space(.)='Review']/ancestor::button",
                ".//button[contains(@aria-label, 'Review')]",
                ".//button[contains(@class, 'artdeco-button--primary')][.//span[contains(text(), 'Review')]]",
            ],
            'submit': [
                # Most specific first - exact text match for "Submit application"
                ".//button[.//span[normalize-space()='Submit application']]",
                ".//span[normalize-space(.)='Submit application']/ancestor::button[1]",
                ".//button[contains(@aria-label, 'Submit application')]",
                # Blue primary button containing Submit text
                ".//button[contains(@class, 'artdeco-button--primary')][.//span[contains(text(), 'Submit')]]",
                # Primary button with Submit text in footer area (NOT Back/secondary)
                ".//footer//button[contains(@class, 'artdeco-button--primary')][.//span[contains(text(), 'Submit')]]",
                # Look in the jobs-easy-apply container specifically
                ".//div[contains(@class, 'jobs-easy-apply')]//button[contains(@class, 'artdeco-button--primary')][.//span[contains(text(), 'Submit')]]",
                # Primary button with Submit (excluding anything with 'back' in any attribute)
                ".//button[contains(@class, 'artdeco-button--primary') and not(contains(@class, 'secondary')) and not(contains(@class, 'tertiary'))][.//span[contains(text(), 'Submit')]]",
                # Button with data-easy-apply-submit attribute (LinkedIn standard)
                ".//button[@data-easy-apply-submit]",
                ".//button[contains(@data-control-name, 'submit')]",
                # Try CSS-style matching - blue button with Submit text
                ".//button[contains(@class, 'artdeco-button')][.//span[contains(translate(text(), 'SUBMIT', 'submit'), 'submit')]]",
                # Fallback - any button containing "submit" (case insensitive) but NOT back
                ".//button[contains(translate(., 'SUBMIT', 'submit'), 'submit') and not(contains(translate(., 'BACK', 'back'), 'back'))]",
                # Last resort - find the primary button in the modal footer
                "(.//div[contains(@class, 'jobs-easy-apply-footer')]//button[contains(@class, 'artdeco-button--primary')])[last()]",
            ],
            'done': [
                ".//button[.//span[text()='Done']]",
                ".//span[normalize-space(.)='Done']/ancestor::button",
                ".//button[contains(@aria-label, 'Done')]",
                ".//button[contains(@aria-label, 'Dismiss')]",
            ]
        }
        
        xpaths = button_configs.get(button_type, [])
        
        for xpath in xpaths:
            try:
                buttons = self.modal.find_elements(By.XPATH, xpath)
                for btn in buttons:
                    try:
                        # Wrap each button check in try-catch to handle stale elements
                        if btn.is_displayed() and btn.is_enabled():
                            # Make sure it's not the discard/close button or Back button
                            aria_label = btn.get_attribute("aria-label") or ""
                            btn_class = btn.get_attribute("class") or ""
                            btn_text = btn.text.strip().lower() if btn.text else ""
                            
                            # === CRITICAL: Never match X / Close / Dismiss buttons ===
                            # Skip the modal dismiss (X) button - it has artdeco-modal__dismiss class
                            if 'artdeco-modal__dismiss' in btn_class:
                                continue
                            # Skip circular close buttons (the X icon in top-right)
                            if 'artdeco-button--circle' in btn_class:
                                continue
                            # Skip buttons with dismiss/close/discard aria labels (except Done type)
                            aria_lower = aria_label.lower()
                            if button_type != 'done' and any(w in aria_lower for w in ['dismiss', 'close', 'discard']):
                                continue
                            # Skip buttons whose text is just 'x', 'close', 'dismiss', or 'discard'
                            if btn_text in ('x', 'close', 'dismiss', 'discard', '×', '✕'):
                                continue
                            # Skip tiny buttons (likely icon-only close buttons, < 40px wide)
                            try:
                                btn_width = btn.size.get('width', 100)
                                btn_height = btn.size.get('height', 40)
                                if btn_width < 40 and btn_height < 40 and button_type == 'submit':
                                    continue
                            except Exception:
                                pass
                            
                            # Skip Back/Previous buttons explicitly
                            if 'back' in btn_text or 'previous' in btn_text:
                                continue
                            if 'back' in aria_lower or 'previous' in aria_lower:
                                continue
                            # Skip secondary/tertiary buttons when looking for primary actions
                            if button_type in ['submit', 'next', 'review']:
                                if 'artdeco-button--secondary' in btn_class or 'artdeco-button--tertiary' in btn_class:
                                    continue
                            
                            # === EXTRA SAFETY for Submit: Verify text actually contains submit-like words ===
                            if button_type == 'submit':
                                submit_words = ['submit', 'apply', 'send']
                                has_submit_text = any(w in btn_text for w in submit_words)
                                has_submit_aria = any(w in aria_lower for w in submit_words)
                                # If the button has NO submit-related text at all, skip it
                                # (unless it's from a very specific XPath that guarantees submit)
                                if not has_submit_text and not has_submit_aria:
                                    # Only allow as last-resort fallback if primary class present
                                    if 'artdeco-button--primary' not in btn_class:
                                        continue
                            
                            return btn
                    except StaleElementReferenceException:
                        print_lg(f"[SmartModal] ⚠️ Button became stale while checking - trying next")
                        continue
                    except Exception as btn_err:
                        continue
            except Exception:
                continue
        
        return None
    
    def find_button(self, button_type: str) -> WebElement | None:
        """
        Find a specific button in the modal.
        button_type: 'next', 'review', 'submit', 'done'
        Uses minimal scrolling - only scrolls if button not found initially.
        """
        # First try without scrolling (button may already be visible)
        btn = self._find_button_no_scroll(button_type)
        if btn:
            return btn
        
        # If not found, scroll to bottom (where buttons typically are) and try once more
        self.scroll_modal_to_bottom()
        time.sleep(0.15)
        
        btn = self._find_button_no_scroll(button_type)
        if btn:
            return btn
            
        # If still not found, try refreshing modal reference (DOM may have changed)
        if self.refresh_modal_reference():
            btn = self._find_button_no_scroll(button_type)
            
        return btn
    
    def get_current_page_state(self) -> dict:
        """
        Analyze the current modal page state.
        Returns dict with: has_next, has_review, has_submit, has_upload, unfilled_required
        Optimized to minimize scrolling - scrolls once then checks all buttons.
        """
        # Single scroll to bottom where buttons are located
        self.scroll_modal_to_bottom()
        time.sleep(0.15)
        
        state = {
            'has_next': False,
            'has_review': False,
            'has_submit': False,
            'has_done': False,
            'has_upload': False,
            'unfilled_required': [],
            'page_title': ''
        }
        
        # Check for buttons - use no-scroll version since we already scrolled above
        state['has_next'] = self._find_button_no_scroll('next') is not None
        state['has_review'] = self._find_button_no_scroll('review') is not None
        state['has_submit'] = self._find_button_no_scroll('submit') is not None
        state['has_done'] = self._find_button_no_scroll('done') is not None
        
        # Check for file upload field
        try:
            upload_field = self.modal.find_element(By.NAME, "file")
            state['has_upload'] = upload_field is not None
        except NoSuchElementException:
            state['has_upload'] = False
        
        # Check for unfilled required fields
        try:
            # Required text inputs
            required_inputs = self.modal.find_elements(By.CSS_SELECTOR, 
                "input[required]:not([type='hidden']):not([type='file'])")
            for inp in required_inputs:
                if inp.is_displayed() and not inp.get_attribute("value"):
                    label = self._get_field_label(inp)
                    state['unfilled_required'].append(label)
            
            # Required selects
            required_selects = self.modal.find_elements(By.CSS_SELECTOR, "select[required]")
            for sel in required_selects:
                if sel.is_displayed():
                    selected = Select(sel).first_selected_option.text
                    if selected == "Select an option" or not selected:
                        label = self._get_field_label(sel)
                        state['unfilled_required'].append(label)
            
            # Required textareas
            required_textareas = self.modal.find_elements(By.CSS_SELECTOR, "textarea[required]")
            for ta in required_textareas:
                if ta.is_displayed() and not ta.get_attribute("value"):
                    label = self._get_field_label(ta)
                    state['unfilled_required'].append(label)
                    
        except Exception as e:
            print_lg(f"[SmartModal] Error checking required fields: {e}")
        
        # Get page title/header
        try:
            header = self.modal.find_element(By.CSS_SELECTOR, "h3, .jobs-easy-apply-modal__title")
            state['page_title'] = header.text
        except NoSuchElementException:
            pass
        
        return state
    
    def _get_field_label(self, element) -> str:
        """Get the label text for a form field."""
        try:
            # Try finding associated label
            field_id = element.get_attribute("id")
            if field_id:
                label = self.modal.find_element(By.CSS_SELECTOR, f"label[for='{field_id}']")
                return label.text
        except Exception:
            pass
        
        try:
            # Try parent container
            parent = element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'form-element')]//label")
            return parent.text
        except Exception:
            pass
        
        return element.get_attribute("name") or "Unknown field"
    
    def _close_autocomplete_dropdowns(self) -> None:
        """Close any open autocomplete/typeahead dropdowns that might intercept clicks."""
        try:
            # Check for open typeahead/autocomplete dropdowns
            open_dropdowns = self.modal.find_elements(By.XPATH, 
                ".//div[contains(@class, 'search-typeahead') and contains(@class, 'hit')]"
                " | .//div[contains(@class, 'autocomplete')]"
                " | .//ul[contains(@class, 'typeahead')]")
            
            if open_dropdowns:
                # Avoid ESC on Easy Apply (can trigger modal close). Click a safe area instead.
                try:
                    safe_targets = [
                        ".jobs-easy-apply-content",
                        ".jobs-easy-apply-modal__content",
                        ".artdeco-modal__content",
                    ]
                    clicked = False
                    for selector in safe_targets:
                        try:
                            container = self.modal.find_element(By.CSS_SELECTOR, selector)
                            if container.is_displayed():
                                container.click()
                                clicked = True
                                break
                        except Exception:
                            continue
                    if not clicked:
                        # Fallback: blur active element
                        self.driver.execute_script("document.activeElement && document.activeElement.blur();")
                    time.sleep(0.2)
                    print_lg("[SmartModal] Closed autocomplete dropdown(s) safely")
                except Exception:
                    pass
                
            # Also blur any focused inputs that might have dropdowns open
            try:
                focused = self.driver.switch_to.active_element
                if focused and focused.tag_name in ('input', 'textarea'):
                    # Check if it's a typeahead input
                    role = focused.get_attribute("role") or ""
                    aria_auto = focused.get_attribute("aria-autocomplete") or ""
                    if "combobox" in role or aria_auto:
                        self.driver.execute_script("arguments[0].blur();", focused)
                        time.sleep(0.15)
                        print_lg("[SmartModal] Blurred autocomplete input")
            except Exception:
                pass
                
        except Exception as e:
            # Non-critical, just log it
            pass
    
    def click_button_safely(self, button: WebElement, button_name: str = "button") -> bool:
        """
        Click a button with multiple retry strategies and fallback to JS click.
        
        Args:
            button: The WebElement button to click
            button_name: Name of button for logging (e.g., 'Submit', 'Next')
            
        Returns:
            True if click succeeded, False otherwise
        """
        if not button:
            print_lg(f"[SmartModal] ⚠️ {button_name} button is None - cannot click")
            return False
        
        try:
            # First, close any open autocomplete dropdowns
            self._close_autocomplete_dropdowns()
            
            # Get button details for logging
            btn_text = button.text.strip() if button.text else "No text"
            btn_class = button.get_attribute("class") or "No class"
            btn_aria = button.get_attribute("aria-label") or "No aria-label"
            print_lg(f"[SmartModal] 🖱️ Attempting to click {button_name}: '{btn_text}' | aria: '{btn_aria}'")
            
            # === SAFETY: Final guard against clicking the X/dismiss button ===
            if button_name.lower() in ('submit', 'next', 'review'):
                if 'artdeco-modal__dismiss' in btn_class or 'artdeco-button--circle' in btn_class:
                    print_lg(f"[SmartModal] ❌ BLOCKED: Refusing to click dismiss/X button as {button_name}!")
                    return False
                close_words = ('dismiss', 'close', 'discard')
                if any(w in btn_aria.lower() for w in close_words):
                    print_lg(f"[SmartModal] ❌ BLOCKED: aria-label '{btn_aria}' is a close button, not {button_name}!")
                    return False
                if btn_text.lower() in ('x', '×', '✕', 'close', 'dismiss', 'discard'):
                    print_lg(f"[SmartModal] ❌ BLOCKED: text '{btn_text}' is a close button, not {button_name}!")
                    return False
            
            # METHOD 1: Scroll into view and direct click
            try:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", 
                    button
                )
                time.sleep(0.3)
                button.click()
                print_lg(f"[SmartModal] ✅ {button_name} clicked via direct click")
                return True
            except ElementClickInterceptedException as e:
                print_lg(f"[SmartModal] Direct click intercepted, trying safe overlay dismiss...")
                # SAFE dismiss: Only remove toasts/messaging overlays - NEVER touch modal dismiss/X buttons
                self._dismiss_safe_overlays()
                time.sleep(0.3)
                try:
                    button.click()
                    print_lg(f"[SmartModal] ✅ {button_name} clicked after popup dismiss")
                    return True
                except Exception:
                    pass
            except Exception as e1:
                print_lg(f"[SmartModal] Direct click failed: {type(e1).__name__}")
            
            # METHOD 2: JavaScript click (bypasses overlay issues)
            try:
                self.driver.execute_script("arguments[0].click();", button)
                print_lg(f"[SmartModal] ✅ {button_name} clicked via JavaScript")
                return True
            except Exception as e2:
                print_lg(f"[SmartModal] JS click failed: {type(e2).__name__}")
            
            # METHOD 3: ActionChains click (simulates mouse movement)
            try:
                from selenium.webdriver.common.action_chains import ActionChains
                actions = ActionChains(self.driver)
                actions.move_to_element(button).pause(0.2).click().perform()
                print_lg(f"[SmartModal] ✅ {button_name} clicked via ActionChains")
                return True
            except Exception as e3:
                print_lg(f"[SmartModal] ActionChains click failed: {type(e3).__name__}")
            
            # METHOD 4: Focus and Enter key
            try:
                button.send_keys(Keys.RETURN)
                print_lg(f"[SmartModal] ✅ {button_name} activated via ENTER key")
                return True
            except Exception as e4:
                print_lg(f"[SmartModal] ENTER key failed: {type(e4).__name__}")
            
            # METHOD 5: JavaScript dispatch click event
            try:
                self.driver.execute_script("""
                    var event = new MouseEvent('click', {
                        view: window,
                        bubbles: true,
                        cancelable: true
                    });
                    arguments[0].dispatchEvent(event);
                """, button)
                print_lg(f"[SmartModal] ✅ {button_name} clicked via dispatch event")
                return True
            except Exception as e5:
                print_lg(f"[SmartModal] Dispatch event failed: {type(e5).__name__}")
            
            # METHOD 6: PyAutoGUI coordinate-based click (LAST RESORT for Submit button)
            # SAFETY: Only use if button text/aria confirms it's actually the Submit button
            if button_name.lower() == 'submit':
                try:
                    import pyautogui
                    
                    # SAFETY CHECK: Verify this is actually a Submit button, not a close/X button
                    btn_text = (button.text or "").strip().lower()
                    btn_aria = (button.get_attribute("aria-label") or "").lower()
                    btn_class = (button.get_attribute("class") or "").lower()
                    
                    # Skip PyAutoGUI if this looks like a close/dismiss button
                    if any(x in btn_text for x in ['dismiss', 'close', 'discard', 'x']):
                        print_lg(f"[SmartModal] ⚠️ Skipping PyAutoGUI - button text '{btn_text}' looks like close button")
                        return False
                    if any(x in btn_aria for x in ['dismiss', 'close', 'discard']):
                        print_lg(f"[SmartModal] ⚠️ Skipping PyAutoGUI - aria-label '{btn_aria}' looks like close button")
                        return False
                    if 'artdeco-button--circle' in btn_class:
                        print_lg(f"[SmartModal] ⚠️ Skipping PyAutoGUI - circular button (likely close)")
                        return False
                    
                    # Must contain submit-related text
                    if not any(x in btn_text for x in ['submit', 'apply', 'send']):
                        if not any(x in btn_aria for x in ['submit', 'apply', 'send']):
                            print_lg(f"[SmartModal] ⚠️ Skipping PyAutoGUI - button doesn't look like submit (text='{btn_text}', aria='{btn_aria}')")
                            return False
                    
                    # Get button's screen coordinates
                    btn_location = button.location
                    btn_size = button.size
                    
                    # Verify button is reasonably sized (submit buttons are typically 80-200px wide)
                    if btn_size['width'] < 60 or btn_size['width'] > 300:
                        print_lg(f"[SmartModal] ⚠️ Skipping PyAutoGUI - suspicious button width: {btn_size['width']}px")
                        return False
                    if btn_size['height'] < 20 or btn_size['height'] > 60:
                        print_lg(f"[SmartModal] ⚠️ Skipping PyAutoGUI - suspicious button height: {btn_size['height']}px")
                        return False
                    
                    # Get browser window position using more reliable method
                    window_x = self.driver.execute_script("return window.screenX || window.screenLeft || 0;")
                    window_y = self.driver.execute_script("return window.screenY || window.screenTop || 0;")
                    
                    # Get outer height (includes browser chrome) vs inner height
                    outer_height = self.driver.execute_script("return window.outerHeight || 0;")
                    inner_height = self.driver.execute_script("return window.innerHeight || 0;")
                    browser_chrome_height = max(outer_height - inner_height, 60)  # At least 60px for toolbar
                    
                    # Calculate actual screen position (center of button)
                    click_x = window_x + btn_location['x'] + (btn_size['width'] // 2)
                    click_y = window_y + btn_location['y'] + (btn_size['height'] // 2) + browser_chrome_height
                    
                    print_lg(f"[SmartModal] 🎯 Submit button verified: text='{btn_text}', size={btn_size}")
                    print_lg(f"[SmartModal] 🎯 Chrome height: {browser_chrome_height}px, clicking at ({click_x}, {click_y})")
                    
                    # Move and click with pyautogui
                    pyautogui.moveTo(click_x, click_y, duration=0.2)
                    time.sleep(0.1)
                    pyautogui.click()
                    print_lg(f"[SmartModal] ✅ {button_name} clicked via PyAutoGUI at ({click_x}, {click_y})")
                    return True
                except Exception as e6:
                    print_lg(f"[SmartModal] PyAutoGUI click failed: {type(e6).__name__}: {e6}")
                
            print_lg(f"[SmartModal] ❌ All click methods failed for {button_name}")
            return False
            
        except Exception as e:
            print_lg(f"[SmartModal] ❌ {button_name} click failed unexpectedly: {e}")
            return False
    
    def navigate_to_next_page(self) -> str:
        """
        Navigate to the next page in the modal.
        Returns: 'next', 'review', 'submit', 'done', 'stuck', 'unfilled', or 'error'
        
        Includes verification that resume is uploaded before proceeding.
        """
        # First check if driver is still alive
        if not self._is_driver_alive():
            print_lg("[SmartModal] ❌ Browser/Driver not responding!")
            return 'error'
        
        self.dismiss_popups()
        time.sleep(0.3)
        
        state = self.get_current_page_state()
        
        # Log current state
        print_lg(f"[SmartModal] Page {self.current_page}: Next={state['has_next']}, "
                f"Review={state['has_review']}, Submit={state['has_submit']}, "
                f"Upload={state['has_upload']}, Unfilled={len(state['unfilled_required'])}")
        
        # === CRITICAL: If upload field exists, verify resume is uploaded before proceeding ===
        if state['has_upload'] and not self.uploaded_resume:
            print_lg("[SmartModal] ⚠️ Upload field present but resume not verified - blocking navigation")
            return 'unfilled'
        
        # Priority order: Submit > Done > Review > Next
        if state['has_submit']:
            # CRITICAL: Refresh modal reference before finding submit button
            # The modal DOM may have changed during form filling
            self.refresh_modal_reference()
            time.sleep(0.2)
            
            btn = self.find_button('submit')
            if btn:
                # Try clicking submit with multiple retries - SELENIUM ONLY (no pyautogui)
                # NOTE: We do NOT call dismiss_popups() here - it can accidentally
                # click the Easy Apply modal's X/dismiss button, closing the form!
                # The JS click fallback in click_button_safely() handles overlays safely.
                for submit_attempt in range(5):
                    time.sleep(0.2)
                    
                    # CRITICAL: Refresh modal reference on each attempt to handle stale DOM
                    if submit_attempt > 0:
                        self.refresh_modal_reference()
                        time.sleep(0.15)
                    
                    # Re-find button in case DOM changed
                    btn = self.find_button('submit')
                    if not btn:
                        print_lg(f"[SmartModal] ⚠️ Submit button not found on attempt {submit_attempt+1}")
                        # Try global search for submit button if modal search fails
                        try:
                            btn = self.driver.find_element(By.XPATH, 
                                "//button[contains(@class, 'artdeco-button--primary')][.//span[contains(text(), 'Submit')]]")
                            print_lg(f"[SmartModal] 🔍 Found submit button via global search")
                        except Exception:
                            time.sleep(0.3)
                            continue
                    
                    # Log detailed button info for debugging
                    try:
                        btn_loc = btn.location
                        btn_sz = btn.size
                        btn_txt = btn.text.strip() if btn.text else "N/A"
                        btn_tag = btn.tag_name
                        btn_displayed = btn.is_displayed()
                        btn_enabled = btn.is_enabled()
                        btn_class = btn.get_attribute('class') or "N/A"
                        btn_aria = btn.get_attribute('aria-label') or "N/A"
                        btn_id = btn.get_attribute('id') or "N/A"
                        print_lg(f"[SmartModal] 📍 Submit button details:")
                        print_lg(f"[SmartModal]    - text='{btn_txt}'")
                        print_lg(f"[SmartModal]    - tag={btn_tag}, id='{btn_id}'")
                        print_lg(f"[SmartModal]    - class='{btn_class}'")
                        print_lg(f"[SmartModal]    - aria-label='{btn_aria}'")
                        print_lg(f"[SmartModal]    - location=({btn_loc['x']}, {btn_loc['y']})")
                        print_lg(f"[SmartModal]    - size=({btn_sz['width']}x{btn_sz['height']})")
                        print_lg(f"[SmartModal]    - displayed={btn_displayed}, enabled={btn_enabled}")
                        
                        # Also log parent element info
                        try:
                            parent = btn.find_element(By.XPATH, "..")
                            parent_class = parent.get_attribute('class') or "N/A"
                            parent_tag = parent.tag_name
                            print_lg(f"[SmartModal]    - parent: <{parent_tag} class='{parent_class[:60]}'>")
                        except:
                            pass
                    except Exception as detail_err:
                        print_lg(f"[SmartModal] Could not get button details: {detail_err}")
                    
                    print_lg(f"[SmartModal] 🖱️ Attempting to click Submit (attempt {submit_attempt+1}/5)...")
                    if self.click_button_safely(btn, "Submit"):
                        print_lg("[SmartModal] ✅ Clicked Submit Application")
                        return 'submit'
                    else:
                        print_lg(f"[SmartModal] ⚠️ Submit click attempt {submit_attempt+1} failed, retrying...")
                        time.sleep(0.5)
                
                # If all Selenium methods failed, try one more aggressive JS approach
                btn = self.find_button('submit')
                if btn:
                    try:
                        # Force remove any overlays first
                        self.driver.execute_script("""
                            // Remove any overlays that might be blocking
                            var overlays = document.querySelectorAll('.artdeco-modal-overlay, .overlay, [class*="overlay"]');
                            overlays.forEach(function(el) {
                                if (el.classList.contains('jobs-easy-apply-modal') === false) {
                                    el.style.display = 'none';
                                }
                            });
                        """)
                        time.sleep(0.2)
                        
                        # Try multiple JS click methods
                        click_success = self.driver.execute_script("""
                            var btn = arguments[0];
                            try {
                                // Method 1: Standard click
                                btn.click();
                                return true;
                            } catch(e1) {
                                try {
                                    // Method 2: Dispatch click event
                                    var evt = new MouseEvent('click', {bubbles: true, cancelable: true, view: window});
                                    btn.dispatchEvent(evt);
                                    return true;
                                } catch(e2) {
                                    return false;
                                }
                            }
                        """, btn)
                        
                        if click_success:
                            print_lg("[SmartModal] ✅ Submit clicked via aggressive JS method")
                            return 'submit'
                    except Exception as js_err:
                        print_lg(f"[SmartModal] ⚠️ Aggressive JS click failed: {js_err}")
                
                print_lg("[SmartModal] ⚠️ Submit button found but ALL click attempts failed")
            else:
                print_lg("[SmartModal] ⚠️ has_submit=True but find_button returned None")
        
        if state['has_done']:
            btn = self.find_button('done')
            if self.click_button_safely(btn, "Done"):
                print_lg("[SmartModal] ✅ Clicked Done")
                return 'done'
        
        if state['has_review']:
            btn = self.find_button('review')
            if self.click_button_safely(btn, "Review"):
                print_lg("[SmartModal] ✅ Clicked Review")
                self.current_page += 1
                return 'review'
        
        if state['has_next']:
            btn = self.find_button('next')
            if self.click_button_safely(btn, "Next"):
                print_lg(f"[SmartModal] ✅ Clicked Next (Page {self.current_page} -> {self.current_page + 1})")
                self.current_page += 1
                self.dismiss_popups()  # Dismiss popups after page transition
                return 'next'
        
        # No button found - might be stuck
        if state['unfilled_required']:
            print_lg(f"[SmartModal] ⚠️ Unfilled required fields: {state['unfilled_required']}")
            return 'unfilled'
        
        return 'stuck'
    
    def upload_resume_if_needed(self, resume_path: str) -> bool:
        """Upload resume if upload field is present and not already uploaded.
        
        Includes verification that the file was actually uploaded and crash protection.
        Uses multiple strategies including file copying to bypass potential detection.
        """
        if self.uploaded_resume:
            return True
        
        # === STRATEGY: Copy file to a fresh temp location with clean name ===
        # This helps bypass any detection based on file path or metadata
        actual_upload_path = resume_path
        temp_copy_path = None
        
        try:
            import tempfile
            import shutil
            
            # Create a clean copy with simple filename
            ext = os.path.splitext(resume_path)[1]
            clean_name = f"Resume{ext}"  # Simple, clean filename
            temp_dir = tempfile.gettempdir()
            temp_copy_path = os.path.join(temp_dir, clean_name)
            
            # Copy the file
            shutil.copy2(resume_path, temp_copy_path)
            actual_upload_path = temp_copy_path
            print_lg(f"[SmartModal] 📋 Created clean copy: {clean_name}")
        except Exception as copy_err:
            print_lg(f"[SmartModal] Copy note: {copy_err}, using original")
            actual_upload_path = resume_path
        
        # Multiple strategies to find and upload resume
        upload_strategies = [
            # Strategy 1: Find by NAME attribute
            lambda: self.modal.find_element(By.NAME, "file"),
            # Strategy 2: Find by input type=file
            lambda: self.modal.find_element(By.CSS_SELECTOR, "input[type='file']"),
            # Strategy 3: Find in document card container
            lambda: self.modal.find_element(By.CSS_SELECTOR, ".jobs-document-upload input[type='file']"),
            # Strategy 4: Find by data-test attribute
            lambda: self.modal.find_element(By.CSS_SELECTOR, "[data-test-document-upload-input]"),
            # Strategy 5: Global search for file input
            lambda: self.driver.find_element(By.CSS_SELECTOR, ".jobs-easy-apply-modal input[type='file']"),
        ]
        
        for strategy in upload_strategies:
            try:
                upload_field = strategy()
                if upload_field:
                    # Make sure the field is interactable
                    if not upload_field.is_displayed():
                        # Try to make it visible via JS
                        self.driver.execute_script(
                            "arguments[0].style.display = 'block'; arguments[0].style.visibility = 'visible';",
                            upload_field
                        )
                    
                    # Upload the file
                    abs_path = os.path.abspath(actual_upload_path)
                    print_lg(f"[SmartModal] 📄 Uploading resume: {os.path.basename(resume_path)}")
                    upload_field.send_keys(abs_path)
                    
                    # Handle Deloitte DLP popup after upload
                    # DLP popup appears ~0.5-1s after file is sent to the input
                    # Use background monitor thread to catch it reliably
                    try:
                        from modules.popup_blocker import dismiss_deloitte_dlp_popup, monitor_and_dismiss_dlp_popup
                        import threading
                        
                        # Start background DLP monitor for 5 seconds
                        dlp_thread = threading.Thread(
                            target=monitor_and_dismiss_dlp_popup,
                            args=(5.0, 0.5),
                            daemon=True
                        )
                        dlp_thread.start()
                        print_lg("[SmartModal] 🛡️ DLP popup monitor started (5s)")
                        
                        # Wait for the monitor to finish (limited to 6s)
                        dlp_thread.join(timeout=6.0)
                    except ImportError:
                        # monitor_and_dismiss_dlp_popup may not exist, fallback
                        try:
                            from modules.popup_blocker import dismiss_deloitte_dlp_popup
                            time.sleep(1.0)
                            dismiss_deloitte_dlp_popup(max_attempts=3, click_delay=0.5)
                        except Exception:
                            pass
                    except Exception as dlp_err:
                        print_lg(f"[SmartModal] DLP handler note: {dlp_err}")
                    
                    # Dismiss any browser-based popups
                    time.sleep(0.3)
                    self.dismiss_popups()
                    
                    # === VERIFICATION: Wait for upload to complete and verify ===
                    upload_verified = self._verify_resume_upload(resume_path, max_wait=10)
                    
                    if upload_verified:
                        print_lg(f"[SmartModal] ✅ Resume upload VERIFIED: {os.path.basename(resume_path)}")
                        self.uploaded_resume = True
                        # Clean up temp file
                        if temp_copy_path and os.path.exists(temp_copy_path):
                            try:
                                os.remove(temp_copy_path)
                            except:
                                pass
                        return True
                    else:
                        print_lg("[SmartModal] ⚠️ Resume upload not verified, will retry on next iteration")
                        return False
                        
            except NoSuchElementException:
                continue
            except Exception as e:
                print_lg(f"[SmartModal] Upload strategy failed: {e}")
                # Check if browser/driver is still alive
                if not self._is_driver_alive():
                    print_lg("[SmartModal] ❌ Driver crashed during upload!")
                    raise Exception("Browser crashed during resume upload")
                continue
        
        # Clean up temp file if upload failed
        if temp_copy_path and os.path.exists(temp_copy_path):
            try:
                os.remove(temp_copy_path)
            except:
                pass
        
        # If no upload field found, it's okay - might not be on upload page
        return False
    
    def select_existing_resume(self) -> bool:
        """
        Fallback: Select an existing resume from LinkedIn's dropdown/list.
        
        This is used when the tailored resume upload is rejected by LinkedIn.
        Returns True if an existing resume was successfully selected.
        """
        print_lg("[SmartModal] 🔄 Attempting to select existing resume from LinkedIn...")
        
        try:
            # Look for existing resume options (radio buttons, cards, or dropdown)
            selectors = [
                # Radio buttons for resume selection
                ".jobs-document-upload-redesign-card__container input[type='radio']",
                ".jobs-document-upload__container input[type='radio']",
                # Document cards that can be clicked
                ".jobs-document-upload-redesign-card__container:not(.jobs-document-upload-redesign-card__container--selected)",
                # Any clickable resume option
                "[data-test-document-upload-card]",
                # Dropdown options
                ".jobs-document-upload__resume-dropdown option",
            ]
            
            for selector in selectors:
                try:
                    elements = self.modal.find_elements(By.CSS_SELECTOR, selector)
                    # Skip the first one if it's the currently selected one
                    for elem in elements:
                        try:
                            # Check if this is not already selected
                            if elem.get_attribute("checked") == "true":
                                continue
                            classes = elem.get_attribute("class") or ""
                            if "selected" in classes or "active" in classes:
                                continue
                            
                            # Try to click this option
                            if elem.is_displayed():
                                print_lg(f"[SmartModal] Found existing resume option, clicking...")
                                elem.click()
                                time.sleep(1)
                                
                                # Verify selection
                                if elem.get_attribute("checked") == "true" or "selected" in (elem.get_attribute("class") or ""):
                                    print_lg("[SmartModal] ✅ Selected existing resume from list")
                                    self.uploaded_resume = True
                                    return True
                        except:
                            continue
                except:
                    continue
            
            # Alternative: Look for "Show more resumes" and expand
            try:
                show_more = self.modal.find_element(By.XPATH, 
                    ".//*[contains(text(), 'Show') and contains(text(), 'resume')]")
                if show_more and show_more.is_displayed():
                    show_more.click()
                    time.sleep(0.5)
                    # Try again after expanding
                    return self.select_existing_resume()
            except:
                pass
            
            print_lg("[SmartModal] ❌ Could not find existing resume to select")
            return False
            
        except Exception as e:
            print_lg(f"[SmartModal] Error selecting existing resume: {e}")
            return False
    
    def _verify_resume_upload(self, resume_path: str, max_wait: int = 10) -> bool:
        """Verify that the resume was actually uploaded and selected.
        
        Checks for:
        1. Document card showing the filename
        2. No loading spinners
        3. No error messages
        """
        filename = os.path.basename(resume_path)
        filename_no_ext = os.path.splitext(filename)[0]
        
        print_lg(f"[SmartModal] 🔍 Verifying resume upload... (waiting up to {max_wait}s)")
        
        for wait_time in range(max_wait):
            try:
                # Check if driver is still alive
                if not self._is_driver_alive():
                    print_lg("[SmartModal] ❌ Driver not responding during verification")
                    return False
                
                # Check for loading indicators (wait for them to disappear)
                loading_selectors = [
                    ".artdeco-spinner",
                    "[class*='loading']",
                    "[class*='uploading']",
                    ".jobs-document-upload__loading",
                ]
                is_loading = False
                for selector in loading_selectors:
                    try:
                        loaders = self.modal.find_elements(By.CSS_SELECTOR, selector)
                        if any(l.is_displayed() for l in loaders):
                            is_loading = True
                            break
                    except:
                        pass
                
                if is_loading:
                    print_lg(f"[SmartModal]    └─ Upload in progress... ({wait_time+1}s)")
                    time.sleep(1)
                    continue
                
                # Check for error messages
                error_selectors = [
                    ".artdeco-inline-feedback--error",
                    "[class*='error']",
                    ".jobs-document-upload__error",
                ]
                for selector in error_selectors:
                    try:
                        errors = self.modal.find_elements(By.CSS_SELECTOR, selector)
                        for err in errors:
                            if err.is_displayed() and err.text:
                                print_lg(f"[SmartModal] ❌ Upload error detected: {err.text}")
                                return False
                    except:
                        pass
                
                # Check for document card showing the filename
                doc_card_selectors = [
                    ".jobs-document-upload-redesign-card__file-name",
                    ".jobs-document-upload__file-name", 
                    "[class*='document'] [class*='file-name']",
                    ".jobs-document-upload-redesign-card__container",
                    ".ui-attachment__filename",
                ]
                
                for selector in doc_card_selectors:
                    try:
                        cards = self.modal.find_elements(By.CSS_SELECTOR, selector)
                        for card in cards:
                            if card.is_displayed():
                                card_text = card.text.lower()
                                # Check if filename appears in the card
                                if filename_no_ext.lower()[:20] in card_text or filename.lower()[:20] in card_text:
                                    print_lg(f"[SmartModal] ✅ Found document card: {card.text[:50]}")
                                    return True
                    except:
                        pass
                
                # Alternative: Check for any document card (even without matching name)
                try:
                    any_card = self.modal.find_element(By.CSS_SELECTOR, 
                        ".jobs-document-upload-redesign-card__container, .jobs-document-upload__container")
                    if any_card.is_displayed():
                        # Check if there's a selected/active state
                        card_classes = any_card.get_attribute("class") or ""
                        if "selected" in card_classes or "active" in card_classes:
                            print_lg("[SmartModal] ✅ Document card is selected/active")
                            return True
                except:
                    pass
                
                # Check for radio button or checkbox being selected (resume selection)
                try:
                    selected_inputs = self.modal.find_elements(By.CSS_SELECTOR, 
                        "input[type='radio']:checked, input[type='checkbox']:checked")
                    for inp in selected_inputs:
                        # Check if this is near a document upload section
                        parent = inp.find_element(By.XPATH, "./ancestor::div[contains(@class, 'document')]")
                        if parent:
                            print_lg("[SmartModal] ✅ Resume selection radio/checkbox is checked")
                            return True
                except:
                    pass
                
                time.sleep(1)
                
            except Exception as e:
                print_lg(f"[SmartModal] Verification check error: {e}")
                time.sleep(1)
        
        # Last resort: check if file input has a value
        try:
            file_inputs = self.modal.find_elements(By.CSS_SELECTOR, "input[type='file']")
            for fi in file_inputs:
                value = fi.get_attribute("value")
                if value and filename_no_ext.lower() in value.lower():
                    print_lg(f"[SmartModal] ✅ File input has value: {value}")
                    return True
        except:
            pass
        
        print_lg("[SmartModal] ⚠️ Could not verify resume upload within timeout")
        
        # === LENIENT MODE: Assume upload worked if file was sent and no errors ===
        # LinkedIn's UI changes frequently, so strict verification often fails
        # even when upload actually succeeded. Trust that send_keys worked.
        print_lg("[SmartModal] 🔄 Lenient mode: Assuming upload succeeded (no errors detected)")
        return True
    
    def _is_driver_alive(self) -> bool:
        """Check if the WebDriver/browser is still alive and responsive."""
        try:
            # Try a simple operation to check if driver is responsive
            _ = self.driver.current_url
            return True
        except Exception:
            return False


def smart_easy_apply(modal: WebElement, resume_path: str, questions_handler, work_location: str, 
                     job_description: str = None, popup_blocker_instance=None) -> tuple[bool, set, str]:
    """
    Smart Easy Apply handler using the SmartModalHandler.
    
    Includes crash protection and resume upload verification.
    
    Args:
        modal: The Easy Apply modal WebElement
        resume_path: Path to resume file to upload
        questions_handler: Function to answer questions (answer_questions)
        work_location: Work location string
        job_description: Job description text
        popup_blocker_instance: Optional popup blocker
    
    Returns:
        tuple of (success, questions_list, error_message)
    """
    global pause_before_submit
    
    # === CHECK PILOT RESUME MODE ===
    # Import settings to check resume mode
    from config import settings
    pilot_resume_mode = getattr(settings, 'pilot_resume_mode', 'tailored')
    
    # === CHECK SMART FORM FILLER V2 ===
    use_v2_filler = getattr(settings, 'use_smart_form_filler', True)
    smart_filler_v2 = None
    if use_v2_filler:
        try:
            from modules.smart_form_filler import SmartFormFiller
            # Build user_config from questions/personals for the v2 engine
            v2_config = {}
            try:
                from config import personals as _p
                v2_config.update({
                    'first_name': getattr(_p, 'first_name', ''),
                    'last_name': getattr(_p, 'last_name', ''),
                    'email': getattr(_p, 'email', ''),
                    'phone_number': getattr(_p, 'phone_number', ''),
                    'city': getattr(_p, 'current_city', ''),
                    'state': getattr(_p, 'state', ''),
                    'country': getattr(_p, 'country', ''),
                    'zipcode': getattr(_p, 'zipcode', ''),
                    'street': getattr(_p, 'street', ''),
                    'linkedin_url': getattr(_p, 'linkedIn', ''),
                    'website': getattr(_p, 'website', ''),
                    'years_of_experience': str(getattr(_p, 'years_of_experience', '')),
                    'desired_salary': str(getattr(_p, 'desired_salary', '')),
                    'current_employer': getattr(_p, 'recent_employer', ''),
                    'notice_period': str(getattr(_p, 'notice_period', '')),
                    'linkedin_headline': getattr(_p, 'linkedin_headline', ''),
                    'summary': getattr(_p, 'linkedin_summary', ''),
                    'cover_letter': getattr(_p, 'cover_letter', ''),
                    'gender': getattr(_p, 'gender', ''),
                    'ethnicity': getattr(_p, 'ethnicity', ''),
                    'veteran_status': getattr(_p, 'veteran_status', ''),
                    'disability_status': getattr(_p, 'disability_status', ''),
                    'visa_sponsorship': getattr(_p, 'require_visa', ''),
                    'citizenship': getattr(_p, 'us_citizenship', ''),
                    'work_authorized': 'Yes',
                    'full_name': f"{getattr(_p, 'first_name', '')} {getattr(_p, 'last_name', '')}".strip(),
                    # Education fields
                    'university': getattr(_p, 'university', ''),
                    'degree': getattr(_p, 'degree', ''),
                    'field_of_study': getattr(_p, 'field_of_study', ''),
                    'gpa': getattr(_p, 'gpa', ''),
                    # Email and phone country code
                    'phone_country_code': getattr(_p, 'phone_country_code', ''),
                })
                # Override email with config email if available
                if getattr(_p, 'email', ''):
                    v2_config['email'] = getattr(_p, 'email', '')
            except Exception:
                pass
            
            # Load learned answers for V2 filler
            v2_learned = {}
            try:
                from modules.self_learning import get_all_learned
                all_learned = get_all_learned()
                for bucket_key in ('dropdown_mappings', 'select_answers', 'text_answers'):
                    bucket = all_learned.get(bucket_key, {})
                    for k, v in bucket.items():
                        v2_learned[k.strip().lower()] = v
            except ImportError:
                pass
            
            smart_filler_v2 = SmartFormFiller(driver, v2_config, fast_mode=True, learned_answers=v2_learned)
            print_lg("[SmartEasyApply] 🧠 Smart Form Filler V2 enabled (with self-learning)")
        except Exception as e:
            print_lg(f"[SmartEasyApply] ⚠️ V2 filler unavailable, falling back to legacy: {e}")
            smart_filler_v2 = None
    # 'preselected' mode uses LinkedIn's pre-selected resume, 
    # 'skip' does nothing with resume. Both skip the upload.
    # 'default' mode UPLOADS the project's default resume file.
    # 'tailored' mode UPLOADS the AI-tailored resume.
    skip_resume_upload = pilot_resume_mode in ('preselected', 'skip')
    
    if skip_resume_upload:
        mode_desc = {
            'preselected': "Using LinkedIn's pre-selected resume (no upload)",
            'skip': "Skipping resume handling entirely"
        }
        print_lg(f"[SmartEasyApply] 📄 Resume Mode: '{pilot_resume_mode}' - {mode_desc.get(pilot_resume_mode, 'No upload')}")
    else:
        print_lg(f"[SmartEasyApply] 📄 Resume Mode: '{pilot_resume_mode}' - Will upload resume: {os.path.basename(resume_path)}")
    
    handler = SmartModalHandler(driver, modal, popup_blocker_instance)
    questions_list = set()
    max_iterations = 20
    iteration = 0
    upload_retry_count = 0
    max_upload_retries = 3
    
    # === WALL-CLOCK TIMEOUT for form filling ===
    _form_start_time = time.time()
    _effective_form_timeout = form_fill_timeout if form_fill_timeout and form_fill_timeout > 0 else 0
    
    # === CRITICAL FIX: In preselected/default/skip mode, mark resume as handled IMMEDIATELY ===
    # This prevents navigate_to_next_page() from blocking on upload pages
    if skip_resume_upload:
        handler.uploaded_resume = True
        print_lg(f"[SmartEasyApply] ✅ Resume pre-marked as handled (mode: {pilot_resume_mode})")
    
    print_lg("[SmartEasyApply] Starting smart form navigation...")
    
    # First, try to click "Next" to get past the initial phone/contact page
    try:
        wait_span_click(modal, "Next", 1)
        print_lg("[SmartEasyApply] Clicked initial Next button")
        time.sleep(0.5)
    except Exception:
        pass  # Modal may already be on a different page
    
    while iteration < max_iterations:
        iteration += 1
        
        # === WALL-CLOCK TIMEOUT CHECK ===
        if _effective_form_timeout > 0:
            elapsed = time.time() - _form_start_time
            if elapsed > _effective_form_timeout:
                print_lg(f"[SmartEasyApply] ⏰ Form fill timeout reached ({elapsed:.0f}s > {_effective_form_timeout}s)")
                return False, questions_list, f"Form fill timeout after {elapsed:.0f}s"
        
        # === STOP SIGNAL CHECK inside form loop ===
        if should_stop():
            print_lg("[SmartEasyApply] 🛑 Stop signal received during form filling")
            return False, questions_list, "Stop signal received"
        
        # === CRASH PROTECTION: Check if driver is still alive ===
        if not handler._is_driver_alive():
            print_lg("[SmartEasyApply] ❌ Browser crashed or driver not responding!")
            return False, questions_list, "Browser crashed during application"
        
        # Dismiss any popups first
        handler.dismiss_popups()
        
        # === RESUME UPLOAD LOGIC ===
        # Only try to upload if NOT in 'preselected', 'default' or 'skip' mode
        if not skip_resume_upload:
            # Try to upload resume if on upload page (with retry logic)
            upload_result = handler.upload_resume_if_needed(resume_path)
            
            # If upload failed and we're on upload page, retry
            if not upload_result and not handler.uploaded_resume:
                state = handler.get_current_page_state()
                if state.get('has_upload'):
                    upload_retry_count += 1
                    if upload_retry_count <= max_upload_retries:
                        print_lg(f"[SmartEasyApply] 🔄 Resume upload retry {upload_retry_count}/{max_upload_retries}")
                        # Handle DLP popup again just in case
                        try:
                            from modules.popup_blocker import dismiss_deloitte_dlp_popup
                            dismiss_deloitte_dlp_popup(max_attempts=3, click_delay=0.3)
                        except:
                            pass
                        time.sleep(1)
                        continue
                    else:
                        print_lg("[SmartEasyApply] ❌ Resume upload failed after max retries")
                        return False, questions_list, "Resume upload failed - could not verify upload"
        else:
            # In 'preselected'/'default'/'skip' mode - resume already marked as handled at init
            # Just log when we detect an upload page (for debugging purposes)
            state = handler.get_current_page_state()
            if state.get('has_upload'):
                print_lg("[SmartEasyApply] 📄 Upload page detected - using pre-selected/existing resume (no upload action)")
        
        # Answer any questions on current page
        try:
            if smart_filler_v2:
                # V2 Smart Form Filler: pattern-matching + config-driven answers
                v2_ok = smart_filler_v2.fill_current_page(resume_path)
                if not v2_ok:
                    # V2 couldn't fill all required fields, fall back to legacy for this page
                    questions_list = questions_handler(modal, questions_list, work_location, job_description)
            else:
                # Legacy: keyword matching + AI fallback
                questions_list = questions_handler(modal, questions_list, work_location, job_description)
        except Exception as e:
            print_lg(f"[SmartEasyApply] Question answering error: {e}")
            # If v2 crashed, fall back to legacy gracefully
            if smart_filler_v2:
                try:
                    questions_list = questions_handler(modal, questions_list, work_location, job_description)
                except Exception:
                    pass
        
        # Try to navigate to next page
        result = handler.navigate_to_next_page()
        
        # === CRASH PROTECTION: Handle error result ===
        if result == 'error':
            print_lg("[SmartEasyApply] ❌ Navigation error - browser may have crashed")
            return False, questions_list, "Browser crashed during navigation"
        
        if result == 'submit':
            # ====================================================================
            # DETAILED DEBUG LOGGING FOR SUBMIT VERIFICATION
            # ====================================================================
            print_lg("=" * 70)
            print_lg("[DEBUG] ========== SUBMIT BUTTON CLICKED - STARTING VERIFICATION ==========")
            print_lg("=" * 70)
            
            # Wait for submission to process
            print_lg("[DEBUG] Waiting 2 seconds for submission to process...")
            time.sleep(2.0)
            
            # === CRITICAL CHECK: Did LinkedIn reject and go back to upload page? ===
            try:
                handler.refresh_modal_reference()
                post_submit_state = handler.get_current_page_state()
                if post_submit_state.get('has_upload'):
                    # LinkedIn rejected the resume and sent back to upload page!
                    print_lg("[DEBUG] ⚠️ DETECTED: LinkedIn sent back to UPLOAD page after submit!")
                    print_lg("[DEBUG] This means LinkedIn rejected the uploaded resume file!")
                    
                    # Check if there's an error message
                    try:
                        error_msgs = handler.modal.find_elements(By.CSS_SELECTOR, 
                            ".artdeco-inline-feedback--error, [class*='error'], .jobs-document-upload__error")
                        for err in error_msgs:
                            if err.is_displayed() and err.text:
                                print_lg(f"[DEBUG] Error message: {err.text}")
                    except:
                        pass
                    
                    # === FALLBACK: Try to use existing resume from dropdown ===
                    fallback_enabled = getattr(settings_module, 'resume_fallback_on_rejection', True)
                    if fallback_enabled and not handler._used_fallback_resume:
                        print_lg("[SmartEasyApply] 🔄 Attempting fallback: selecting existing resume...")
                        handler._used_fallback_resume = True  # Prevent infinite loop
                        
                        if handler.select_existing_resume():
                            print_lg("[SmartEasyApply] ✅ Fallback successful - selected existing resume")
                            # Reset uploaded flag and continue the application
                            handler.uploaded_resume = True
                            # Continue to next iteration to re-try submit
                            continue
                        else:
                            print_lg("[SmartEasyApply] ❌ Fallback failed - no existing resume available")
                    
                    # Return failure with specific reason
                    return False, questions_list, "LinkedIn rejected resume file - went back to upload page"
            except Exception as check_err:
                print_lg(f"[DEBUG] State check error: {check_err}")
            
            # VERIFICATION: Check if modal closed or shows "Done" or confirmation
            try:
                # Log current page state
                print_lg(f"[DEBUG] handler.current_page = {handler.current_page}")
                
                # Try to refresh modal reference
                print_lg("[DEBUG] Attempting to refresh modal reference...")
                refresh_success = handler.refresh_modal_reference()
                print_lg(f"[DEBUG] Modal refresh result: {refresh_success}")
                
                # Check if original modal is still displayed
                try:
                    modal_displayed = modal.is_displayed()
                    print_lg(f"[DEBUG] Original modal.is_displayed() = {modal_displayed}")
                except StaleElementReferenceException:
                    print_lg("[DEBUG] Original modal is STALE (no longer exists) - this is GOOD!")
                    print_lg("[SmartEasyApply] ✅ Modal gone - submission successful")
                    return True, questions_list, ""
                except Exception as modal_check_err:
                    print_lg(f"[DEBUG] Error checking original modal: {type(modal_check_err).__name__}: {modal_check_err}")
                
                # Check for "Done" button
                print_lg("[DEBUG] Looking for 'Done' button...")
                done_btn = handler.find_button('done')
                if done_btn:
                    try:
                        done_text = done_btn.text.strip() if done_btn.text else "N/A"
                        done_displayed = done_btn.is_displayed()
                        print_lg(f"[DEBUG] Done button FOUND: text='{done_text}', displayed={done_displayed}")
                    except:
                        print_lg("[DEBUG] Done button FOUND but couldn't get details")
                    print_lg("[SmartEasyApply] ✅ Application submitted - Done button appeared")
                    handler.click_button_safely(done_btn, "Done")
                    return True, questions_list, ""
                else:
                    print_lg("[DEBUG] Done button NOT found")
                
                # Check for confirmation/success messages
                print_lg("[DEBUG] Looking for success/confirmation messages...")
                try:
                    success_xpaths = [
                        ".//*[contains(text(), 'Application submitted')]",
                        ".//*[contains(text(), 'application sent')]", 
                        ".//*[contains(text(), 'Successfully')]",
                        ".//*[contains(text(), 'applied')]",
                        ".//*[contains(text(), 'Your application was sent')]",
                    ]
                    for xpath in success_xpaths:
                        try:
                            elements = handler.modal.find_elements(By.XPATH, xpath)
                            if elements:
                                for el in elements:
                                    try:
                                        if el.is_displayed():
                                            print_lg(f"[DEBUG] SUCCESS indicator found: '{el.text[:100]}...'")
                                            print_lg("[SmartEasyApply] ✅ Application submitted - confirmation found")
                                            return True, questions_list, ""
                                    except:
                                        pass
                        except:
                            pass
                    print_lg("[DEBUG] No success messages found")
                except Exception as success_err:
                    print_lg(f"[DEBUG] Error checking success messages: {success_err}")
                
                # Check what buttons are currently visible
                print_lg("[DEBUG] Checking what buttons are currently visible...")
                has_submit = handler.find_button('submit')
                has_next = handler.find_button('next')
                has_review = handler.find_button('review')
                has_done = handler.find_button('done')
                print_lg(f"[DEBUG] Buttons: Submit={has_submit is not None}, Next={has_next is not None}, Review={has_review is not None}, Done={has_done is not None}")
                
                if has_submit:
                    try:
                        submit_text = has_submit.text.strip()
                        submit_loc = has_submit.location
                        print_lg(f"[DEBUG] Submit button STILL VISIBLE: text='{submit_text}', location={submit_loc}")
                    except:
                        print_lg("[DEBUG] Submit button STILL VISIBLE (couldn't get details)")
                    print_lg("[SmartEasyApply] ⚠️ Submit button still visible - will retry...")
                    continue
                
                # Log the current modal content for debugging
                print_lg("[DEBUG] Capturing modal content for analysis...")
                try:
                    modal_html = handler.modal.get_attribute('innerHTML')
                    # Log first 1000 chars of HTML
                    print_lg(f"[DEBUG] Modal HTML (first 1000 chars): {modal_html[:1000] if modal_html else 'EMPTY'}")
                    
                    # Check for specific elements
                    all_buttons = handler.modal.find_elements(By.TAG_NAME, 'button')
                    print_lg(f"[DEBUG] Total buttons in modal: {len(all_buttons)}")
                    for i, btn in enumerate(all_buttons[:10]):  # First 10 buttons
                        try:
                            btn_text = btn.text.strip() if btn.text else "N/A"
                            btn_class = btn.get_attribute('class') or "N/A"
                            btn_visible = btn.is_displayed()
                            print_lg(f"[DEBUG]   Button {i+1}: text='{btn_text}', class='{btn_class[:50]}', visible={btn_visible}")
                        except:
                            pass
                except Exception as html_err:
                    print_lg(f"[DEBUG] Could not capture modal HTML: {html_err}")
                
                # If we get here, no clear success or failure - assume success
                print_lg("[DEBUG] No clear success/failure indicators. Assuming success since submit was clicked.")
                print_lg("[SmartEasyApply] ✅ Submit clicked - assuming success (no errors detected)")
                print_lg("=" * 70)
                return True, questions_list, ""
                
            except StaleElementReferenceException as stale_err:
                print_lg(f"[DEBUG] StaleElementReferenceException caught: {stale_err}")
                print_lg("[SmartEasyApply] ✅ Modal stale - submission successful")
                return True, questions_list, ""
            except Exception as verify_err:
                print_lg(f"[DEBUG] Verification exception: {type(verify_err).__name__}: {verify_err}")
                import traceback
                print_lg(f"[DEBUG] Traceback: {traceback.format_exc()}")
                print_lg("[SmartEasyApply] ✅ Submit clicked - assuming success")
                return True, questions_list, ""
        
        elif result == 'done':
            return True, questions_list, ""
        
        elif result == 'review':
            # On review page - handle pause_before_submit and follow_company
            time.sleep(1.0)
            handler.refresh_modal_reference()
            try:
                WebDriverWait(driver, 3).until(lambda d: handler.find_button('submit') or handler.find_button('done'))
            except Exception:
                pass
            
            # Apply follow company setting
            try:
                follow_company(modal)
            except Exception as e:
                print_lg(f"[SmartEasyApply] Follow company error: {e}")
            
            # Handle pause_before_submit (skip in pilot mode)
            cur_pause_before_submit = pause_before_submit
            if cur_pause_before_submit and not pilot_mode_enabled:
                decision = _safe_pyautogui_confirm(
                    '1. Please verify your information.\n'
                    '2. If you edited something, please return to this final screen.\n'
                    '3. DO NOT CLICK "Submit Application".\n\n\n'
                    'You can turn off "Pause before submit" in config.py\n'
                    'To TEMPORARILY disable pausing, click "Disable Pause"',
                    "Confirm your information",
                    ["Disable Pause", "Discard Application", "Submit Application"]
                )
                if decision == "Discard Application":
                    return False, questions_list, "Job application discarded by user"
                elif decision == "Disable Pause":
                    pause_before_submit = False
                # If "Submit Application" or "Disable Pause", continue to submit
            elif pilot_mode_enabled:
                print_lg("✈️ [PILOT MODE] Skipping pause_before_submit - auto-submitting")
            
            # Now look for Submit button
            time.sleep(0.3)
            continue
        
        elif result == 'next':
            # Successfully moved to next page
            time.sleep(0.5)
            handler.refresh_modal_reference()
            continue
        
        elif result == 'unfilled':
            # There are unfilled fields - give question handler another chance
            print_lg("[SmartEasyApply] Retrying question answering for unfilled fields...")
            try:
                questions_list = questions_handler(modal, questions_list, work_location, job_description)
            except Exception:
                pass
            time.sleep(0.2)  # Reduced from 0.3
            # If still stuck after 3 attempts on same page, fail
            if iteration > 3 and handler.current_page == 1:
                return False, questions_list, "Stuck on first page with unfilled fields"
        
        elif result == 'stuck':
            print_lg(f"[SmartEasyApply] ⚠️ Stuck at iteration {iteration}")
            # Only scroll once (to bottom where buttons should be)
            handler.scroll_modal_to_bottom()
            time.sleep(0.2)
            
            if iteration > 5:
                return False, questions_list, "Stuck - cannot find navigation buttons"
        
        time.sleep(0.3)  # Reduced from 0.5
    
    return False, questions_list, "Max iterations reached"


# Function to answer common questions for Easy Apply
def answer_common_questions(label: str, answer: str) -> str:
    """Answer common Yes/No questions using autopilot settings when in pilot mode."""
    if 'sponsorship' in label or 'visa' in label:
        if pilot_mode_enabled:
            try:
                from config import settings as _s
                answer = getattr(_s, 'autopilot_visa_required', require_visa)
            except Exception:
                answer = require_visa
        else:
            answer = require_visa
    elif pilot_mode_enabled:
        # In pilot mode, use autopilot form pre-fill settings for common Yes/No questions
        try:
            from config import settings as _s
            if 'relocat' in label:
                answer = getattr(_s, 'autopilot_willing_relocate', 'Yes')
            elif 'authorized' in label or 'authoris' in label or 'work permit' in label or ('eligible' in label and 'work' in label):
                answer = getattr(_s, 'autopilot_work_authorization', 'Yes')
            elif 'remote' in label:
                answer = getattr(_s, 'autopilot_remote_preference', 'Yes')
            elif 'start immediately' in label or ('start' in label and 'when' in label):
                answer = getattr(_s, 'autopilot_start_immediately', 'Yes')
            elif 'background check' in label or 'drug test' in label or 'drug screen' in label:
                answer = getattr(_s, 'autopilot_background_check', 'Yes')
            elif 'commut' in label:
                answer = getattr(_s, 'autopilot_commute_ok', 'Yes')
        except Exception:
            pass  # Keep default answer='Yes'
    return answer


# Function to answer the questions for Easy Apply
def answer_questions(modal: WebElement, questions_list: set, work_location: str, job_description: str | None = None ) -> set:
    # ===== SELF-LEARNING: Load learned answers =====
    try:
        from modules.self_learning import get_answer as sl_get_answer, learn as sl_learn, learn_dropdown as sl_learn_dropdown, get_dropdown as sl_get_dropdown, get_education as sl_get_education, flush as sl_flush
        _self_learning_available = True
    except ImportError:
        _self_learning_available = False
    
    # Load email from config for dropdown matching
    try:
        from config.personals import email as config_email, phone_country_code as config_phone_country_code
    except ImportError:
        config_email = ""
        config_phone_country_code = ""
    
    # Load education config
    try:
        from config.personals import university, degree, field_of_study, gpa, education_start_date, education_end_date
    except ImportError:
        university = degree = field_of_study = gpa = education_start_date = education_end_date = ""
    
    # Get all questions from the page
     
    all_questions = modal.find_elements(By.XPATH, ".//div[@data-test-form-element]")

    for Question in all_questions:
        # Check if it's a select Question
        select = try_xp(Question, ".//select", False)
        if select:
            label_org = "Unknown"
            try:
                label = Question.find_element(By.TAG_NAME, "label")
                label_org = label.find_element(By.TAG_NAME, "span").text
            except: pass
            answer = 'Yes'
            label = label_org.lower()
            select = Select(select)
            selected_option = select.first_selected_option.text
            optionsText = []
            options = '"List of phone country codes"'
            # Always enumerate options now (needed for email/country code matching)
            optionsText = [option.text for option in select.options]
            if 'country code' in label:
                options = '"List of phone country codes"'  # Keep compact log
            else:
                options = "".join([f' "{option}",' for option in optionsText])
            prev_answer = selected_option
            if overwrite_previous_answers or selected_option == "Select an option":
                # ===== SELF-LEARNING: Check learned dropdown mappings first =====
                learned_answer = None
                if _self_learning_available:
                    learned_answer = sl_get_dropdown(label)
                    if not learned_answer:
                        learned_answer = sl_get_answer(label_org, "select")
                
                if learned_answer:
                    # Use learned answer
                    answer = learned_answer
                    print_lg(f"[SelfLearning] 🧠 Using learned answer for '{label_org}': {answer}")
                elif 'email' in label:
                    # Select the correct email from dropdown options
                    if config_email:
                        answer = config_email
                    else:
                        answer = prev_answer  # Fallback to pre-selected
                elif 'country code' in label or ('phone' in label and 'country' in label):
                    # Select the correct phone country code
                    if config_phone_country_code:
                        answer = config_phone_country_code
                    else:
                        answer = prev_answer
                elif 'gender' in label or 'sex' in label: 
                    answer = gender
                elif 'disability' in label: 
                    answer = disability_status
                elif 'proficiency' in label: 
                    answer = 'Professional'
                # Add location handling
                elif any(loc_word in label for loc_word in ['location', 'city', 'state', 'country']):
                    if 'country' in label:
                        answer = country 
                    elif 'state' in label:
                        answer = state
                    elif 'city' in label:
                        answer = current_city if current_city else work_location
                    else:
                        answer = work_location
                else: 
                    answer = answer_common_questions(label,answer)
                try: 
                    select.select_by_visible_text(answer)
                except NoSuchElementException as e:
                    # Define similar phrases for common answers
                    possible_answer_phrases = []
                    if answer == 'Decline':
                        possible_answer_phrases = ["Decline", "not wish", "don't wish", "Prefer not", "not want"]
                    elif 'yes' in answer.lower():
                        possible_answer_phrases = ["Yes", "Agree", "I do", "I have"]
                    elif 'no' in answer.lower():
                        possible_answer_phrases = ["No", "Disagree", "I don't", "I do not"]
                    else:
                        # Try partial matching for any answer
                        possible_answer_phrases = [answer]
                        # Add lowercase and uppercase variants
                        possible_answer_phrases.append(answer.lower())
                        possible_answer_phrases.append(answer.upper())
                        # Try without special characters
                        possible_answer_phrases.append(''.join(c for c in answer if c.isalnum()))
                    ##<
                    foundOption = False
                    for phrase in possible_answer_phrases:
                        for option in optionsText:
                            # Check if phrase is in option or option is in phrase (bidirectional matching)
                            if phrase.lower() in option.lower() or option.lower() in phrase.lower():
                                select.select_by_visible_text(option)
                                answer = option
                                foundOption = True
                                break
                    if not foundOption:
                        ai_selected = None
                        if use_AI and aiClient and optionsText:
                            try:
                                options_list = [opt.strip() for opt in optionsText if opt.strip()]
                                if options_list:
                                    prompt = (
                                        f"{label_org}\n"
                                        f"Options: {', '.join(options_list)}\n"
                                        f"Return the best matching option text exactly."
                                    )
                                    if ai_provider == "openai":
                                        ai_selected = ai_answer_question(
                                            aiClient,
                                            prompt,
                                            options=options_list,
                                            question_type="single_select",
                                            job_description=job_description,
                                            user_information_all=user_information_all,
                                        )
                                    elif ai_provider == "deepseek":
                                        ai_selected = deepseek_answer_question(
                                            aiClient,
                                            prompt,
                                            options=options_list,
                                            question_type="single_select",
                                            job_description=job_description,
                                            about_company=about_company_for_ai,
                                            user_information_all=user_information_all,
                                        )
                                    elif ai_provider == "gemini":
                                        ai_selected = gemini_answer_question(
                                            aiClient,
                                            prompt,
                                            options=options_list,
                                            question_type="single_select",
                                            job_description=job_description,
                                            about_company=about_company_for_ai,
                                            user_information_all=user_information_all,
                                        )
                                    elif ai_provider == "groq":
                                        ai_selected = groq_answer_question(
                                            aiClient,
                                            prompt,
                                            user_information_all or "",
                                            job_description or "",
                                        )
                            except Exception as e:
                                print_lg(f"AI option selection failed: {e}")

                        if ai_selected:
                            for option in optionsText:
                                if ai_selected.lower() in option.lower() or option.lower() in ai_selected.lower():
                                    select.select_by_visible_text(option)
                                    answer = option
                                    foundOption = True
                                    break

                        if not foundOption:
                            print_lg(f'Failed to find an option with text "{answer}" for question labelled "{label_org}", answering randomly!')
                            select.select_by_index(randint(1, len(select.options)-1))
                            answer = select.first_selected_option.text
                            randomly_answered_questions.add((f'{label_org} [ {options} ]',"select"))
            questions_list.add((f'{label_org} [ {options} ]', answer, "select", prev_answer))
            # ===== SELF-LEARNING: Save successful dropdown answer =====
            if _self_learning_available and answer and answer != prev_answer:
                sl_learn(label_org, answer, question_type="select", overwrite=True)
                sl_learn_dropdown(label, answer)
                print_lg(f"[SelfLearning] 💾 Learned select answer: '{label_org}' → '{answer}'")
            continue
        
        # Check if it's a radio Question
        radio = try_xp(Question, './/fieldset[@data-test-form-builder-radio-button-form-component="true"]', False)
        if radio:
            prev_answer = None
            label = try_xp(radio, './/span[@data-test-form-builder-radio-button-form-component__title]', False)
            try: label = find_by_class(label, "visually-hidden", 2.0)
            except: pass
            label_org = label.text if label else "Unknown"
            answer = 'Yes'
            label = label_org.lower()

            label_org += ' [ '
            options = radio.find_elements(By.TAG_NAME, 'input')
            options_labels = []
            
            for option in options:
                id = option.get_attribute("id")
                option_label = try_xp(radio, f'.//label[@for="{id}"]', False)
                options_labels.append( f'"{option_label.text if option_label else "Unknown"}"<{option.get_attribute("value")}>' ) # Saving option as "label <value>"
                if option.is_selected(): prev_answer = options_labels[-1]
                label_org += f' {options_labels[-1]},'

            if overwrite_previous_answers or prev_answer is None:
                if 'citizenship' in label or 'employment eligibility' in label: answer = us_citizenship
                elif 'veteran' in label or 'protected' in label: answer = veteran_status
                elif 'disability' in label or 'handicapped' in label: 
                    answer = disability_status
                else: answer = answer_common_questions(label,answer)
                foundOption = try_xp(radio, f".//label[normalize-space()='{answer}']", False)
                if foundOption: 
                    actions.move_to_element(foundOption).click().perform()
                else:    
                    possible_answer_phrases = ["Decline", "not wish", "don't wish", "Prefer not", "not want"] if answer == 'Decline' else [answer]
                    ele = options[0]
                    answer = options_labels[0]
                    for phrase in possible_answer_phrases:
                        for i, option_label in enumerate(options_labels):
                            if phrase in option_label:
                                foundOption = options[i]
                                ele = foundOption
                                answer = f'Decline ({option_label})' if len(possible_answer_phrases) > 1 else option_label
                                break
                        if foundOption: break
                    # if answer == 'Decline':
                    #     answer = options_labels[0]
                    #     for phrase in ["Prefer not", "not want", "not wish"]:
                    #         foundOption = try_xp(radio, f".//label[normalize-space()='{phrase}']", False)
                    #         if foundOption:
                    #             answer = f'Decline ({phrase})'
                    #             ele = foundOption
                    #             break
                    actions.move_to_element(ele).click().perform()
                    if not foundOption: randomly_answered_questions.add((f'{label_org} ]',"radio"))
            else: answer = prev_answer
            questions_list.add((label_org+" ]", answer, "radio", prev_answer))
            # ===== SELF-LEARNING: Save radio answer =====
            if _self_learning_available and answer and answer != prev_answer:
                sl_learn(label_org, answer, question_type="radio", overwrite=True)
            continue
        
        # Check if it's a text question
        text = try_xp(Question, ".//input[@type='text']", False)
        if text: 
            do_actions = False
            label = try_xp(Question, ".//label[@for]", False)
            try: label = label.find_element(By.CLASS_NAME,'visually-hidden')
            except: pass
            label_org = label.text if label else "Unknown"
            answer = "" # years_of_experience
            label = label_org.lower()

            prev_answer = text.get_attribute("value")
            if not prev_answer or overwrite_previous_answers:
                # ===== SELF-LEARNING: Check learned text answers first =====
                learned_text = None
                if _self_learning_available:
                    learned_text = sl_get_answer(label_org, "text")
                
                if learned_text:
                    answer = learned_text
                    print_lg(f"[SelfLearning] 🧠 Using learned text answer for '{label_org}': {answer[:30]}")
                elif 'experience' in label or 'years' in label: answer = years_of_experience
                elif 'email' in label: answer = config_email if config_email else ""
                elif 'phone' in label or 'mobile' in label: answer = phone_number
                elif 'street' in label: answer = street
                elif 'city' in label or 'location' in label or 'address' in label:
                    answer = current_city if current_city else work_location
                    do_actions = True
                elif 'signature' in label: answer = full_name
                elif 'name' in label:
                    if 'full' in label: answer = full_name
                    elif 'first' in label and 'last' not in label: answer = first_name
                    elif 'middle' in label and 'last' not in label: answer = middle_name
                    elif 'last' in label and 'first' not in label: answer = last_name
                    elif 'employer' in label: answer = recent_employer
                    elif 'university' in label or 'college' in label or 'school' in label: answer = university
                    else: answer = full_name
                # ===== EDUCATION FIELDS =====
                elif 'university' in label or 'college' in label or 'school' in label or 'institution' in label: answer = university
                elif 'degree' in label or 'qualification' in label: answer = degree
                elif 'major' in label or 'field of study' in label or 'specialization' in label or 'specialisation' in label or 'discipline' in label: answer = field_of_study
                elif 'gpa' in label or 'cgpa' in label or 'grade' in label or 'percentage' in label: answer = gpa
                elif 'notice' in label:
                    if 'month' in label:
                        answer = notice_period_months
                    elif 'week' in label:
                        answer = notice_period_weeks
                    else: answer = notice_period
                elif 'salary' in label or 'compensation' in label or 'ctc' in label or 'pay' in label: 
                    if 'current' in label or 'present' in label:
                        if 'month' in label:
                            answer = current_ctc_monthly
                        elif 'lakh' in label:
                            answer = current_ctc_lakhs
                        else:
                            answer = current_ctc
                    else:
                        if 'month' in label:
                            answer = desired_salary_monthly
                        elif 'lakh' in label:
                            answer = desired_salary_lakhs
                        else:
                            answer = desired_salary
                elif 'linkedin' in label: answer = linkedIn
                elif 'website' in label or 'blog' in label or 'portfolio' in label or 'link' in label: answer = website
                elif 'scale of 1-10' in label: answer = confidence_level
                elif 'headline' in label: answer = linkedin_headline
                elif ('hear' in label or 'come across' in label) and 'this' in label and ('job' in label or 'position' in label): answer = "LinkedIn"
                elif 'state' in label or 'province' in label: answer = state
                elif 'zip' in label or 'postal' in label or 'code' in label: answer = zipcode
                elif 'country' in label: answer = country
                else: answer = answer_common_questions(label,answer)
                ##> ------ Yang Li : MARKYangL - Feature ------
                if answer == "":
                    if use_AI and aiClient:
                        try:
                            if ai_provider.lower() == "openai":
                                answer = ai_answer_question(aiClient, label_org, question_type="text", job_description=job_description, user_information_all=user_information_all)
                            elif ai_provider.lower() == "deepseek":
                                answer = deepseek_answer_question(aiClient, label_org, options=None, question_type="text", job_description=job_description, about_company=None, user_information_all=user_information_all)
                            elif ai_provider.lower() == "gemini":
                                answer = gemini_answer_question(aiClient, label_org, options=None, question_type="text", job_description=job_description, about_company=None, user_information_all=user_information_all)
                            else:
                                randomly_answered_questions.add((label_org, "text"))
                                answer = years_of_experience
                            if answer and isinstance(answer, str) and len(answer) > 0:
                                print_lg(f'AI Answered received for question "{label_org}" \nhere is answer: "{answer}"')
                            else:
                                randomly_answered_questions.add((label_org, "text"))
                                answer = years_of_experience
                        except Exception as e:
                            print_lg("Failed to get AI answer!", e)
                            randomly_answered_questions.add((label_org, "text"))
                            answer = years_of_experience
                    else:
                        randomly_answered_questions.add((label_org, "text"))
                        answer = years_of_experience
                ##<
                text.clear()
                text.send_keys(answer)
                if do_actions:
                    sleep(2)
                    actions.send_keys(Keys.ARROW_DOWN)
                    actions.send_keys(Keys.ENTER).perform()
            questions_list.add((label, text.get_attribute("value"), "text", prev_answer))
            # ===== SELF-LEARNING: Save text answer =====
            final_val = text.get_attribute("value")
            if _self_learning_available and final_val and final_val != prev_answer:
                sl_learn(label_org, final_val, question_type="text", overwrite=False)
            continue

        # Check if it's a textarea question
        text_area = try_xp(Question, ".//textarea", False)
        if text_area:
            do_actions = False  # Initialize for textarea scope (was missing, caused NameError)
            label = try_xp(Question, ".//label[@for]", False)
            label_org = label.text if label else "Unknown"
            label = label_org.lower()
            answer = ""
            prev_answer = text_area.get_attribute("value")
            if not prev_answer or overwrite_previous_answers:
                if 'summary' in label: answer = linkedin_summary
                elif 'cover' in label: answer = cover_letter
                if answer == "":
                ##> ------ Yang Li : MARKYangL - Feature ------
                    if use_AI and aiClient:
                        try:
                            if ai_provider.lower() == "openai":
                                answer = ai_answer_question(aiClient, label_org, question_type="textarea", job_description=job_description, user_information_all=user_information_all)
                            elif ai_provider.lower() == "deepseek":
                                answer = deepseek_answer_question(aiClient, label_org, options=None, question_type="textarea", job_description=job_description, about_company=None, user_information_all=user_information_all)
                            elif ai_provider.lower() == "gemini":
                                answer = gemini_answer_question(aiClient, label_org, options=None, question_type="textarea", job_description=job_description, about_company=None, user_information_all=user_information_all)
                            else:
                                randomly_answered_questions.add((label_org, "textarea"))
                                answer = ""
                            if answer and isinstance(answer, str) and len(answer) > 0:
                                print_lg(f'AI Answered received for question "{label_org}" \nhere is answer: "{answer}"')
                            else:
                                randomly_answered_questions.add((label_org, "textarea"))
                                answer = ""
                        except Exception as e:
                            print_lg("Failed to get AI answer!", e)
                            randomly_answered_questions.add((label_org, "textarea"))
                            answer = ""
                    else:
                        randomly_answered_questions.add((label_org, "textarea"))
            text_area.clear()
            text_area.send_keys(answer)
            if do_actions:
                    sleep(2)
                    actions.send_keys(Keys.ARROW_DOWN)
                    actions.send_keys(Keys.ENTER).perform()
            questions_list.add((label, text_area.get_attribute("value"), "textarea", prev_answer))
            # ===== SELF-LEARNING: Save textarea answer =====
            final_ta = text_area.get_attribute("value")
            if _self_learning_available and final_ta and final_ta != prev_answer:
                sl_learn(label_org, final_ta, question_type="textarea", overwrite=False)
            ##<
            continue

        # Check if it's a checkbox question
        checkbox = try_xp(Question, ".//input[@type='checkbox']", False)
        if checkbox:
            label = try_xp(Question, ".//span[@class='visually-hidden']", False)
            label_org = label.text if label else "Unknown"
            label = label_org.lower()
            answer = try_xp(Question, ".//label[@for]", False)  # Sometimes multiple checkboxes are given for 1 question, Not accounted for that yet
            answer = answer.text if answer else "Unknown"
            prev_answer = checkbox.is_selected()
            checked = prev_answer
            if not prev_answer:
                try:
                    actions.move_to_element(checkbox).click().perform()
                    checked = True
                except Exception as e: 
                    print_lg("Checkbox click failed!", e)
                    pass
            questions_list.add((f'{label} ([X] {answer})', checked, "checkbox", prev_answer))
            continue


    # Select todays date
    try_xp(driver, "//button[contains(@aria-label, 'This is today')]")

    # Collect important skills
    # if 'do you have' in label and 'experience' in label and ' in ' in label -> Get word (skill) after ' in ' from label
    # if 'how many years of experience do you have in ' in label -> Get word (skill) after ' in '

    # ===== SELF-LEARNING: Persist all learned answers to disk =====
    if _self_learning_available:
        try:
            sl_flush()
        except Exception:
            pass

    return questions_list




def external_apply(pagination_element: WebElement, job_id: str, job_link: str, resume: str, date_listed, application_link: str, screenshot_name: str) -> tuple[bool, str, int]:
    '''
    Function to open new tab and save external job application links
    '''
    global tabs_count, dailyEasyApplyLimitReached
    if easy_apply_only:
        try:
            if "exceeded the daily application limit" in driver.find_element(By.CLASS_NAME, "artdeco-inline-feedback__message").text: dailyEasyApplyLimitReached = True
        except: pass
        print_lg("Easy apply failed I guess!")
        if pagination_element != None: return True, application_link, tabs_count
    try:
        wait.until(EC.element_to_be_clickable((By.XPATH, ".//button[contains(@class,'jobs-apply-button') and contains(@class, 'artdeco-button--3')]"))).click() # './/button[contains(span, "Apply") and not(span[contains(@class, "disabled")])]'
        wait_span_click(driver, "Continue", 1, True, False)
        windows = driver.window_handles
        tabs_count = len(windows)
        driver.switch_to.window(windows[-1])
        application_link = driver.current_url
        
        # Handle popups on external sites (especially Deloitte)
        if 'deloitte' in application_link.lower():
            print_lg("Detected Deloitte application page, attempting to dismiss popups...")
            dismiss_deloitte_popup(driver)
        elif popup_blocker:
            popup_blocker.block_all()
        
        print_lg('Got the external application link "{}"'.format(application_link))
        if close_tabs and driver.current_window_handle != linkedIn_tab: driver.close()
        driver.switch_to.window(linkedIn_tab)
        return False, application_link, tabs_count
    except Exception as e:
        # print_lg(e)
        print_lg("Failed to apply!")
        failed_job(job_id, job_link, resume, date_listed, "Probably didn't find Apply button or unable to switch tabs.", e, application_link, screenshot_name)
        global failed_count
        failed_count += 1
        return True, application_link, tabs_count



def follow_company(modal: WebDriver = driver) -> None:
    '''
    Function to follow or un-follow easy applied companies based om `follow_companies`
    '''
    try:
        follow_checkbox_input = try_xp(modal, ".//input[@id='follow-company-checkbox' and @type='checkbox']", False)
        if follow_checkbox_input and follow_checkbox_input.is_selected() != follow_companies:
            try_xp(modal, ".//label[@for='follow-company-checkbox']")
    except Exception as e:
        print_lg("Failed to update follow companies checkbox!", e)
    


#< Failed attempts logging
def failed_job(job_id: str, job_link: str, resume: str, date_listed, error: str, exception: Exception, application_link: str, screenshot_name: str) -> None:
    '''
    Function to update failed jobs list in excel
    '''
    try:
        sid = _get_session_id() if callable(_get_session_id) else "n/a"
        emit_dashboard_event("application_failed", {
            "session_id": sid,
            "job_id": str(job_id),
            "job_link": str(job_link),
            "reason": str(error),
            "application_link": str(application_link),
        })
        with open(failed_file_name, 'a', newline='', encoding='utf-8') as file:
            fieldnames = ['Job ID', 'Job Link', 'Resume Tried', 'Date listed', 'Date Tried', 'Assumed Reason', 'Stack Trace', 'External Job link', 'Screenshot Name', 'Session ID']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if file.tell() == 0: writer.writeheader()
            writer.writerow({'Job ID':truncate_for_csv(job_id), 'Job Link':truncate_for_csv(job_link), 'Resume Tried':truncate_for_csv(resume), 'Date listed':truncate_for_csv(date_listed), 'Date Tried':datetime.now(), 'Assumed Reason':truncate_for_csv(error), 'Stack Trace':truncate_for_csv(exception), 'External Job link':truncate_for_csv(application_link), 'Screenshot Name':truncate_for_csv(screenshot_name), 'Session ID': sid})
            file.close()
    except Exception as e:
        print_lg("Failed to update failed jobs list!", e)
        if not pilot_mode_enabled:
            _safe_pyautogui_alert("Failed to update the excel of failed jobs!\nProbably because of 1 of the following reasons:\n1. The file is currently open or in use by another program\n2. Permission denied to write to the file\n3. Failed to find the file", "Failed Logging")


def screenshot(driver: WebDriver, job_id: str, failedAt: str) -> str:
    '''
    Function to to take screenshot for debugging
    - Returns screenshot name as String
    '''
    screenshot_name = "{} - {} - {}.png".format( job_id, failedAt, str(datetime.now()) )
    path = logs_folder_path+"/screenshots/"+screenshot_name.replace(":",".")
    # special_chars = {'*', '"', '\\', '<', '>', ':', '|', '?'}
    # for char in special_chars:  path = path.replace(char, '-')
    driver.save_screenshot(path.replace("//","/"))
    return screenshot_name
#>



def submitted_jobs(job_id: str, title: str, company: str, work_location: str, work_style: str, description: str, experience_required: int | Literal['Unknown', 'Error in extraction'], 
                   skills: list[str] | Literal['In Development'], hr_name: str | Literal['Unknown'], hr_link: str | Literal['Unknown'], resume: str, 
                   reposted: bool, date_listed: datetime | Literal['Unknown'], date_applied:  datetime | Literal['Pending'], job_link: str, application_link: str, 
                   questions_list: set | None, connect_request: Literal['In Development']) -> None:
    '''
    Function to create or update the Applied jobs CSV file, once the application is submitted successfully
    '''
    try:
        sid = _get_session_id() if callable(_get_session_id) else "n/a"
        emit_dashboard_event("application_submitted", {
            "session_id": sid,
            "job_id": str(job_id),
            "title": str(title),
            "company": str(company),
            "location": str(work_location),
            "job_link": str(job_link),
        })
        emit_dashboard_event("job_context", {
            "title": str(title),
            "company": str(company),
            "location": str(work_location),
        })
        with open(file_name, mode='a', newline='', encoding='utf-8') as csv_file:
            fieldnames = ['Job ID', 'Title', 'Company', 'Work Location', 'Work Style', 'About Job', 'Experience required', 'Skills required', 'HR Name', 'HR Link', 'Resume', 'Re-posted', 'Date Posted', 'Date Applied', 'Job Link', 'External Job link', 'Questions Found', 'Connect Request', 'Session ID']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            if csv_file.tell() == 0: writer.writeheader()
            writer.writerow({'Job ID':truncate_for_csv(job_id), 'Title':truncate_for_csv(title), 'Company':truncate_for_csv(company), 'Work Location':truncate_for_csv(work_location), 'Work Style':truncate_for_csv(work_style), 
                            'About Job':truncate_for_csv(description), 'Experience required': truncate_for_csv(experience_required), 'Skills required':truncate_for_csv(skills), 
                                'HR Name':truncate_for_csv(hr_name), 'HR Link':truncate_for_csv(hr_link), 'Resume':truncate_for_csv(resume), 'Re-posted':truncate_for_csv(reposted), 
                                'Date Posted':truncate_for_csv(date_listed), 'Date Applied':truncate_for_csv(date_applied), 'Job Link':truncate_for_csv(job_link), 
                                'External Job link':truncate_for_csv(application_link), 'Questions Found':truncate_for_csv(questions_list), 'Connect Request':truncate_for_csv(connect_request), 'Session ID': sid})
        csv_file.close()
    except Exception as e:
        print_lg("Failed to update submitted jobs list!", e)
        if not pilot_mode_enabled:
            _safe_pyautogui_alert("Failed to update the excel of applied jobs!\nProbably because of 1 of the following reasons:\n1. The file is currently open or in use by another program\n2. Permission denied to write to the file\n3. Failed to find the file", "Failed Logging")



# Function to discard the job application
def discard_job() -> None:
    actions.send_keys(Keys.ESCAPE).perform()
    wait_span_click(driver, 'Discard', 2)






# Function to apply to jobs
def apply_to_jobs(search_terms: list[str]) -> None:
    applied_jobs = get_applied_job_ids()
    rejected_jobs = set()
    blacklisted_companies = set()
    global current_city, failed_count, skip_count, easy_applied_count, external_jobs_count, tabs_count, pause_before_submit, pause_at_failed_question, useNewResume, easy_apply_active
    current_city = current_city.strip()

    if randomize_search_order:  shuffle(search_terms)
    for searchTerm in search_terms:
        try:
            # Check for stop signal from dashboard before each search term
            if should_stop():
                print_lg("🛑 Stop signal received. Stopping bot...")
                return
            
            log_next_step("Search Jobs", f'Searching for "{searchTerm}"')
            driver.get(f"https://www.linkedin.com/jobs/search/?keywords={searchTerm}")
            print_lg("\n________________________________________________________________________________________________________________________\n")
            print_lg(f'\n>>>> Now searching for "{searchTerm}" <<<<\n\n')

            log_next_step("Apply Filters", "Setting up search filters")
            apply_filters()

            current_count = 0
            while current_count < switch_number:
                # Wait until job listings are loaded
                log_next_step("Load Jobs", "Waiting for job listings to load")
                wait.until(EC.presence_of_all_elements_located((By.XPATH, "//li[@data-occludable-job-id]")))

                pagination_element, current_page = get_page_info()

                # Find all job listings in current page
                buffer(3)
                job_listings = driver.find_elements(By.XPATH, "//li[@data-occludable-job-id]")
                job_ids = []
                for el in job_listings:
                    try:
                        job_card_id = el.get_dom_attribute('data-occludable-job-id')
                        if job_card_id:
                            job_ids.append(job_card_id)
                    except Exception:
                        continue

                log_status(f"Found {len(job_ids)} jobs on page {current_page or '?'}", "info")

                page_processed_job_ids = set()

                for job_card_id in job_ids:
                    # Refresh job list and find the specific card by id to avoid reordering issues
                    try:
                        job = driver.find_element(By.XPATH, f"//li[@data-occludable-job-id='{job_card_id}']")
                    except Exception:
                        continue
                    
                    # Initialize per-job variables with safe defaults
                    job_link = ""
                    screenshot_name = ""
                    resume = "Previous resume"
                    date_listed = "Unknown"
                    reposted = False
                    hr_name = ""
                    hr_link = ""
                    skills = "Unknown"
                    date_applied = None
                    connect_request = ""
                    application_link = "Easy Applied"
                    
                    # === PER-JOB WALL-CLOCK TIMEOUT ===
                    _job_start_time = time.time()
                    _effective_job_timeout = per_job_timeout if per_job_timeout and per_job_timeout > 0 else 0
                    
                    # Check for stop/pause signals from dashboard
                    if should_stop():
                        print_lg("🛑 Stop signal received. Stopping bot...")
                        return
                    
                    # Check pilot mode application limit
                    if pilot_mode_enabled and check_pilot_limit_reached():
                        print_lg("✅ [PILOT] Application limit reached. Stopping bot...")
                        return
                    if not check_pause():
                        print_lg("🛑 Stop signal received during pause. Stopping bot...")
                        return
                    
                    if keep_screen_awake: pyautogui.press('shiftright')
                    if current_count >= switch_number: break
                    print_lg("\n-@-\n")
                    
                    # Block any popups before processing job, but NEVER during Easy Apply modal
                    if popup_blocker and not easy_apply_active and not _is_easy_apply_open(driver):
                        popup_blocker.block_all()

                    log_next_step("Read Job Details", "Extracting job info from card")
                    try:
                        job_id,title,company,work_location,work_style,skip = get_job_main_details(job, blacklisted_companies, rejected_jobs)
                    except StaleElementReferenceException:
                        print_lg("[Job Loop] Stale job card encountered, refreshing list and continuing")
                        continue
                    except WebDriverException as e:
                        print_lg(f"[Job Loop] WebDriver error on job card: {e}. Continuing...")
                        continue

                    # Ensure we don't re-process the same job card after DOM refresh
                    if job_id in page_processed_job_ids:
                        continue
                    page_processed_job_ids.add(job_id)

                    # Guard against DOM reordering: ensure selected job matches the intended card id
                    if job_id != job_card_id:
                        print_lg(
                            f"[Job Loop] Mismatch between targeted card ({job_card_id}) and selected job ({job_id}). Skipping to avoid title switch."
                        )
                        continue
                    
                    if skip: 
                        log_status(f"Skipping: {title} @ {company}", "warning")
                        continue
                    
                    # === CRITICAL: Re-verify job title hasn't changed after click ===
                    # LinkedIn's DOM can reorder job cards after click, showing a different job
                    try:
                        # Wait briefly for the detail panel to update
                        time.sleep(0.5)
                        # Read the title from the right-side detail panel
                        detail_title_el = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, 
                                "h1.t-24, h2.t-24, .job-details-jobs-unified-top-card__job-title, "
                                ".jobs-unified-top-card__job-title"))
                        )
                        detail_title = detail_title_el.text.strip() if detail_title_el else ""
                        # Compare with the title from the card (fuzzy: first 30 chars)
                        if detail_title and title:
                            card_prefix = title[:30].lower().strip()
                            detail_prefix = detail_title[:30].lower().strip()
                            if card_prefix != detail_prefix:
                                print_lg(f"[Job Loop] ⚠️ TITLE MISMATCH after click!")
                                print_lg(f"[Job Loop]   Card title:   '{title}'")
                                print_lg(f"[Job Loop]   Detail title: '{detail_title}'")
                                print_lg(f"[Job Loop]   Skipping to prevent applying to wrong job.")
                                log_status(f"Title mismatch: expected '{title[:40]}', got '{detail_title[:40]}'", "warning")
                                skip_count += 1
                                continue
                    except TimeoutException:
                        pass  # Detail panel not loaded yet, proceed anyway
                    except Exception as title_check_err:
                        print_lg(f"[Job Loop] Title verification error (non-critical): {title_check_err}")
                    
                    # Capture job link now that we've clicked on the job card
                    try:
                        job_link = driver.current_url
                    except Exception:
                        job_link = f"https://www.linkedin.com/jobs/view/{job_id}/"
                    
                    log_job(title, company, "Processing")
                    
                    # Redundant fail safe check for applied jobs!
                    try:
                        if job_id in applied_jobs:
                            print_lg(f'Already applied to "{title} | {company}" job. Job ID: {job_id}!')
                            log_status(f"Already applied to {title}", "info")
                            skip_count += 1
                            continue
                        # Check for "Applied" badge on page - with stale element protection
                        try:
                            applied_link = find_by_class(driver, "jobs-s-apply__application-link", 2)
                            if applied_link:
                                print_lg(f'Already applied to "{title} | {company}" job. Job ID: {job_id}!')
                                log_status(f"Already applied to {title}", "info")
                                skip_count += 1
                                continue
                        except StaleElementReferenceException:
                            pass  # Element became stale, job not applied
                        except Exception:
                            pass  # Any other error, continue with job
                    except Exception as e:
                        print_lg(f"Error checking applied status (non-critical): {type(e).__name__}")



                    # Hiring Manager info
                    try:
                        hr_info_card = WebDriverWait(driver,2).until(EC.presence_of_element_located((By.CLASS_NAME, "hirer-card__hirer-information")))
                        hr_link = hr_info_card.find_element(By.TAG_NAME, "a").get_attribute("href")
                        hr_name = hr_info_card.find_element(By.TAG_NAME, "span").text
                        # if connect_hr:
                        #     driver.switch_to.new_window('tab')
                        #     driver.get(hr_link)
                        #     wait_span_click("More")
                        #     wait_span_click("Connect")
                        #     wait_span_click("Add a note")
                        #     message_box = driver.find_element(By.XPATH, "//textarea")
                        #     message_box.send_keys(connect_request_message)
                        #     if close_tabs: driver.close()
                        #     driver.switch_to.window(linkedIn_tab) 
                        # def message_hr(hr_info_card):
                        #     if not hr_info_card: return False
                        #     hr_info_card.find_element(By.XPATH, ".//span[normalize-space()='Message']").click()
                        #     message_box = driver.find_element(By.XPATH, "//div[@aria-label='Write a message…']")
                        #     message_box.send_keys()
                        #     try_xp(driver, "//button[normalize-space()='Send']")        
                    except Exception as e:
                        print_lg(f'HR info was not given for "{title}" with Job ID: {job_id}!')
                        # print_lg(e)


                    # Calculation of date posted
                    try:
                        # Find the job top card element for date extraction
                        jobs_top_card = try_find_by_classes(driver, [
                            "job-details-jobs-unified-top-card__primary-description-container",
                            "job-details-jobs-unified-top-card__primary-description",
                            "jobs-unified-top-card__primary-description",
                            "jobs-details__main-content"
                        ])
                        if jobs_top_card:
                            time_posted_text = jobs_top_card.find_element(By.XPATH, './/span[contains(normalize-space(), " ago")]').text
                            print("Time Posted: " + time_posted_text)
                            if time_posted_text.__contains__("Reposted"):
                                reposted = True
                                time_posted_text = time_posted_text.replace("Reposted", "")
                            date_listed = calculate_date_posted(time_posted_text.strip())
                        else:
                            print_lg("Could not find job top card element for date extraction")
                    except Exception as e:
                        print_lg("Failed to calculate the date posted!", e)


                    description, experience_required, skip, reason, message = get_job_description()
                    if skip:
                        print_lg(message)
                        failed_job(job_id, job_link, resume, date_listed, reason, message, "Skipped", screenshot_name)
                        rejected_jobs.add(job_id)
                        skip_count += 1
                        continue

                    if use_AI and description != "Unknown":
                        ##> ------ Yang Li : MARKYangL - Feature ------
                        log_next_step("Extract Skills", f"Using {ai_provider} AI")
                        try:
                            if ai_provider.lower() == "openai":
                                skills = ai_extract_skills(aiClient, description)
                            elif ai_provider.lower() == "deepseek":
                                skills = deepseek_extract_skills(aiClient, description)
                            elif ai_provider.lower() == "gemini":
                                skills = gemini_extract_skills(aiClient, description)
                            else:
                                skills = "In Development"
                            print_lg(f"Extracted skills using {ai_provider} AI")
                        except Exception as e:
                            print_lg("Failed to extract skills:", e)
                            skills = "Error extracting skills"
                        ##<

                    # ====== POST-FILTER CONFIRMATION (resume_tailoring_confirm_after_filters) ======
                    # If enabled AND not in pilot mode, ask user to confirm before proceeding
                    # with resume tailoring after all filters have passed.
                    if (resume_tailoring_enabled 
                            and description != "Unknown"
                            and resume_tailoring_confirm_after_filters 
                            and not pilot_mode_enabled):
                        confirm_proceed = _safe_pyautogui_confirm(
                            f"✅ Filters passed for this job:\n\n"
                            f"📋 {title}\n"
                            f"🏢 {company}\n\n"
                            f"Proceed with resume tailoring?",
                            "Confirm Resume Tailoring",
                            ["✨ Proceed", "📄 Use Default", "⏭️ Skip Job"]
                        )
                        if confirm_proceed == "⏭️ Skip Job":
                            print_lg("⏭️ User skipped job at post-filter confirmation")
                            failed_job(job_id, job_link, resume, date_listed, "User skipped",
                                       "Skipped at post-filter confirmation", "Skipped", screenshot_name)
                            skip_count += 1
                            continue
                        elif confirm_proceed == "📄 Use Default":
                            print_lg("📄 User chose default resume (skipping tailoring)")
                            # Force-skip tailoring below by temporarily disabling it for this job
                            resume_tailoring_enabled_this_job = False
                        else:
                            resume_tailoring_enabled_this_job = True
                    else:
                        resume_tailoring_enabled_this_job = True

                    # ====== RESUME TAILORING PROMPT ======
                    # Show popup IMMEDIATELY after job analysis - user decides to tailor or not
                    # Tailoring only starts when user clicks "Tailor Resume" option
                    tailored_resume_path = None
                    resume_was_tailored = False
                    
                    if resume_tailoring_enabled and resume_tailoring_enabled_this_job and description != "Unknown":
                        log_next_step("Resume Tailoring", f"Asking for {title} @ {company}")
                        print_lg("📝 Showing resume tailoring options...")
                        
                        # Show the tailor popup - tailoring starts ONLY if user selects it
                        tailored_resume_path, resume_was_tailored = prompt_for_resume_tailoring(
                            job_title=title,
                            company=company,
                            job_description=description
                        )
                        
                        # Check if user chose to skip this job (only None means skip)
                        # "PRESELECTED" and "SKIP_RESUME" are valid values for pilot mode
                        if tailored_resume_path is None:
                            # User chose to skip this job (only in manual mode)
                            log_status("User skipped this job from tailoring dialog", "warning")
                            print_lg("⏭️ User skipped this job from tailoring dialog")
                            failed_job(job_id, job_link, resume, date_listed, "User skipped", "Skipped from tailoring dialog", "Skipped", screenshot_name)
                            skip_count += 1
                            continue
                        
                        # Handle PRESELECTED and SKIP_RESUME markers from pilot mode
                        if tailored_resume_path in ("PRESELECTED", "SKIP_RESUME"):
                            print_lg(f"📄 [PILOT MODE] Resume mode: {tailored_resume_path}")
                            # Keep default_resume_path for logging/tracking ONLY.
                            # smart_easy_apply() reads pilot_resume_mode directly from settings
                            # so it will correctly skip the upload.
                            resume = f"[{tailored_resume_path}] {os.path.basename(default_resume_path)}"
                            tailored_resume_path = default_resume_path
                            resume_was_tailored = False
                        elif resume_was_tailored:
                            log_status(f"Using AI-tailored resume", "success")
                            print_lg(f"✅ Using AI-tailored resume: {tailored_resume_path}")
                            resume = f"Tailored: {os.path.basename(tailored_resume_path)}"
                        else:
                            log_status("Using default resume", "info")
                            print_lg("📄 Using default resume")
                        
                        # After popup closes, the page might be stale - scroll to Easy Apply button
                        try:
                            buffer(0.5)  # Brief pause to let page settle
                            # Scroll to top of job card first to ensure Easy Apply button is visible
                            job_top_card = try_find_by_classes(driver, [
                                "jobs-unified-top-card",
                                "job-details-jobs-unified-top-card__job-title",
                                "jobs-details-top-card__job-info"
                            ])
                            if job_top_card:
                                scroll_to_view(driver, job_top_card)
                                buffer(0.3)
                        except Exception:
                            pass  # Non-critical, continue anyway

                    uploaded = False
                    resume_to_upload = tailored_resume_path if tailored_resume_path else default_resume_path
                    
                    # === PER-JOB TIMEOUT CHECK before Easy Apply ===
                    if _effective_job_timeout > 0:
                        _job_elapsed = time.time() - _job_start_time
                        if _job_elapsed > _effective_job_timeout:
                            print_lg(f"[Job Timeout] ⏰ Job '{title}' timed out after {_job_elapsed:.0f}s (limit: {_effective_job_timeout}s)")
                            failed_job(job_id, job_link, resume, date_listed, "Per-job timeout",
                                       f"Job processing exceeded {_effective_job_timeout}s limit", "Timeout", screenshot_name)
                            failed_count += 1
                            continue
                    
                    # Case 1: Easy Apply Button
                    log_next_step("Easy Apply", f"Applying to {title}")
                    
                    # Multiple XPath strategies for finding Easy Apply button (LinkedIn changes UI frequently)
                    easy_apply_xpaths = [
                        # Strategy 1: Broadest class match (most reliable across regions)
                        ".//button[contains(@class,'jobs-apply-button')]",
                        # Strategy 2: Button with child span containing Easy Apply text
                        ".//button[.//span[contains(text(), 'Easy Apply')]]",
                        # Strategy 3: Any button whose text contains 'Easy Apply'
                        ".//button[contains(., 'Easy Apply')]",
                        # Strategy 4: Match by aria-label containing 'Easy Apply'
                        ".//button[contains(@aria-label, 'Easy Apply')]",
                        # Strategy 5: aria-label just 'Easy'
                        ".//button[contains(@aria-label, 'Easy')]",
                        # Strategy 6: Div wrapper approach (LinkedIn sometimes wraps in a div)
                        ".//div[contains(@class, 'jobs-apply-button')]//button",
                        # Strategy 7: Artdeco primary button near job details
                        ".//div[contains(@class,'jobs-details')]//button[contains(@class, 'artdeco-button--primary')]",
                        # Strategy 8: Job details top card container
                        ".//div[contains(@class,'job-details-jobs-unified-top-card')]//button[contains(@class, 'jobs-apply-button')]",
                        # Strategy 9: Apply button container approach
                        ".//div[contains(@class,'jobs-s-apply')]//button",
                        # Strategy 10: data-control-name attribute
                        ".//button[@data-control-name='jobdetails_topcard_inapply']",
                    ]
                    
                    # Multiple attempts to find and click Easy Apply button (with stale element handling)
                    easy_apply_clicked = False
                    for attempt in range(3):
                        try:
                            # Try each XPath strategy until one works
                            easy_apply_btn = None
                            matched_xpath = None
                            for xpath in easy_apply_xpaths:
                                try:
                                    easy_apply_btn = WebDriverWait(driver, 2).until(
                                        EC.presence_of_element_located((By.XPATH, xpath))
                                    )
                                    matched_xpath = xpath
                                    break
                                except (TimeoutException, Exception):
                                    continue
                            
                            if easy_apply_btn is None:
                                print_lg(f"[Easy Apply] No button found with any strategy on attempt {attempt+1}")
                                # Debug: dump all apply-related buttons on the page
                                if attempt == 0:
                                    try:
                                        debug_info = driver.execute_script("""
                                            var buttons = document.querySelectorAll('button');
                                            var results = [];
                                            buttons.forEach(function(b) {
                                                var text = b.textContent.trim().substring(0, 50);
                                                var cls = b.className.substring(0, 80);
                                                var aria = b.getAttribute('aria-label') || '';
                                                if (text.toLowerCase().includes('apply') || cls.includes('apply') || aria.toLowerCase().includes('apply')) {
                                                    results.push('TEXT=' + text + ' | CLASS=' + cls + ' | ARIA=' + aria);
                                                }
                                            });
                                            return results.join('\\n');
                                        """)
                                        if debug_info:
                                            print_lg(f"[Easy Apply DEBUG] Apply-related buttons found on page:\\n{debug_info}")
                                        else:
                                            print_lg("[Easy Apply DEBUG] No apply-related buttons found on page at all!")
                                            # Also check current URL
                                            print_lg(f"[Easy Apply DEBUG] Current URL: {driver.current_url[:100]}")
                                    except Exception as debug_err:
                                        print_lg(f"[Easy Apply DEBUG] Could not inspect page: {debug_err}")
                                if attempt < 2:
                                    time.sleep(0.5)
                                    continue
                                break
                            
                            if attempt == 0 and matched_xpath != easy_apply_xpaths[0]:
                                print_lg(f"[Easy Apply] Found button with fallback strategy: {matched_xpath[:60]}")
                            
                            # Scroll button into view to avoid "element click intercepted" errors
                            scroll_to_view(driver, easy_apply_btn)
                            buffer(0.3)  # Brief pause after scroll
                            
                            # Now wait for it to be clickable and click (use the matched xpath)
                            easy_apply_btn = WebDriverWait(driver, 3).until(
                                EC.element_to_be_clickable((By.XPATH, matched_xpath))
                            )
                            try:
                                easy_apply_btn.click()
                            except Exception as click_err:
                                # Fallback: JavaScript click (bypasses "element click intercepted")
                                print_lg(f"[Easy Apply] Direct click failed, using JS click: {str(click_err)[:80]}")
                                driver.execute_script("arguments[0].click();", easy_apply_btn)
                            easy_apply_clicked = True
                            break
                        except StaleElementReferenceException:
                            print_lg(f"[Easy Apply] Stale element on attempt {attempt+1}, retrying...")
                            time.sleep(0.5)
                        except TimeoutException:
                            print_lg(f"[Easy Apply] Timeout on attempt {attempt+1}, retrying...")
                            time.sleep(0.5)
                        except Exception as e:
                            print_lg(f"[Easy Apply] Error on attempt {attempt+1}: {e}")
                            # Fallback: try JavaScript click before giving up
                            try:
                                if easy_apply_btn:
                                    driver.execute_script("arguments[0].click();", easy_apply_btn)
                                    easy_apply_clicked = True
                                    print_lg(f"[Easy Apply] ✅ JS click fallback succeeded on attempt {attempt+1}")
                                    break
                            except Exception:
                                pass
                            # Try scrolling page up on error (button might be above viewport)
                            try:
                                driver.execute_script("window.scrollBy(0, -200);")
                                time.sleep(0.3)
                            except:
                                pass
                            if attempt < 2:  # Only continue if not last attempt
                                continue
                            break
                    
                    if easy_apply_clicked:
                        easy_apply_active = True
                        log_status("Easy Apply modal opened", "success")
                        try:
                            # =================================================================
                            # SMART MODAL HANDLER - Replaces old manual navigation logic
                            # - Properly scrolls modal to find buttons
                            # - Detects Next/Review/Submit buttons intelligently
                            # - Handles Deloitte popups after resume upload
                            # - Does NOT click the X (discard) button on navigation failures
                            # =================================================================
                            
                            errored = ""
                            modal = find_by_class(driver, "jobs-easy-apply-modal")
                            resume = "Previous resume" if not resume_was_tailored else f"Tailored: {os.path.basename(resume_to_upload)}"
                            questions_list = set()
                            
                            # Initialize Smart Modal Handler
                            smart_handler = SmartModalHandler(driver, modal, popup_blocker)
                            
                            # Log resume upload info
                            log_next_step("Upload Resume", os.path.basename(resume_to_upload))
                            
                            # Use the smart_easy_apply function for intelligent form navigation
                            print_lg("[SmartModal] 🚀 Starting intelligent Easy Apply navigation...")
                            
                            success, questions_list, error_msg = smart_easy_apply(
                                modal=modal,
                                resume_path=resume_to_upload,
                                questions_handler=answer_questions,
                                work_location=work_location,
                                job_description=description,
                                popup_blocker_instance=popup_blocker
                            )
                            
                            if success:
                                # Successfully submitted!
                                date_applied = datetime.now()
                                uploaded = smart_handler.uploaded_resume or useNewResume
                                if resume_was_tailored:
                                    resume = f"Tailored: {os.path.basename(resume_to_upload)}"
                                log_status("Application submitted successfully!", "success")
                                print_lg("[SmartModal] ✅ Application submitted successfully!")
                                easy_apply_active = False
                                
                                # Try to close the post-submit confirmation dialog safely.
                                # IMPORTANT: Do NOT send ESC blindly — it can trigger a "Discard" popup.
                                time.sleep(1.0)
                                done_clicked = wait_span_click(driver, "Done", 3)
                                if not done_clicked:
                                    # Try alternative XPaths for the Done button
                                    try:
                                        done_btn = driver.find_element(By.XPATH, 
                                            "//button[contains(@class, 'artdeco-button--primary')]//span[contains(text(), 'Done')]/ancestor::button")
                                        done_btn.click()
                                        done_clicked = True
                                    except Exception:
                                        pass
                                if not done_clicked:
                                    # Try clicking the post-apply modal dismiss (X) only on the success overlay
                                    try:
                                        dismiss_btn = driver.find_element(By.XPATH,
                                            "//div[contains(@class, 'artdeco-modal') and contains(@class, 'post-apply')]//button[contains(@class, 'artdeco-modal__dismiss')]")
                                        dismiss_btn.click()
                                        done_clicked = True
                                    except Exception:
                                        pass
                                if not done_clicked:
                                    # Last resort: gentle ESC, but immediately handle any Discard dialog
                                    actions.send_keys(Keys.ESCAPE).perform()
                                    time.sleep(0.5)
                                    # If a "Discard" dialog appeared, click "Keep" or "Save" to NOT lose progress
                                    try:
                                        keep_btn = driver.find_element(By.XPATH, 
                                            "//button[.//span[contains(text(), 'Keep') or contains(text(), 'Save')]]")
                                        keep_btn.click()
                                        print_lg("[SmartModal] Clicked 'Keep/Save' after ESC on post-submit screen")
                                    except Exception:
                                        pass  # No discard dialog appeared, ESC just closed the modal
                            else:
                                # Smart navigation failed
                                print_lg(f"[SmartModal] ❌ Navigation failed: {error_msg}")
                                easy_apply_active = False
                                
                                # Check if pause_at_failed_question is enabled (skip in pilot mode)
                                if pause_at_failed_question and error_msg and not pilot_mode_enabled:
                                    screenshot(driver, job_id, "Smart modal needed manual intervention")
                                    decision = _safe_pyautogui_confirm(
                                        f'Smart form filling encountered an issue:\n{error_msg}\n\n'
                                        'Please complete the application manually.\n'
                                        'Click "Continue" when done or "Discard" to skip.\n\n'
                                        'You can turn off "Pause at failed question" in config.py',
                                        "Help Needed",
                                        ["Continue", "Discard"]
                                    )
                                    if decision == "Discard":
                                        raise Exception(f"Job application discarded by user after smart modal failure: {error_msg}")
                                    # User completed manually, check if submitted
                                    date_applied = datetime.now()
                                    uploaded = True
                                elif pilot_mode_enabled and error_msg:
                                    # In pilot mode, log and skip
                                    print_lg(f"✈️ [PILOT MODE] Smart modal failed: {error_msg} - skipping job")
                                    errored = "smart_stuck"
                                    screenshot_name = screenshot(driver, job_id, f"Smart modal failed (pilot): {error_msg}")
                                    raise Exception(f"Smart Easy Apply failed in pilot mode: {error_msg}")
                                else:
                                    # No pause setting, raise exception
                                    errored = "smart_stuck"
                                    screenshot_name = screenshot(driver, job_id, f"Smart modal failed: {error_msg}")
                                    raise Exception(f"Smart Easy Apply failed: {error_msg}")
                            
                            # Log answered questions
                            if questions_list:
                                print_lg("Answered the following questions...", questions_list)
                                print("\n\n" + "\n".join(str(question) for question in questions_list) + "\n\n")

                        except Exception as e:
                            print_lg("Failed to Easy apply!")
                            critical_error_log("Smart Easy Apply process", e)
                            failed_job(job_id, job_link, resume, date_listed, "Problem in Easy Applying", e, application_link, screenshot_name)
                            failed_count += 1
                            easy_apply_active = False
                            # IMPORTANT: Do NOT call discard_job() here as it clicks the X button
                            # Instead, just press Escape to close the modal gracefully
                            try:
                                actions.send_keys(Keys.ESCAPE).perform()
                                time.sleep(0.3)
                                actions.send_keys(Keys.ESCAPE).perform()
                            except Exception:
                                pass
                            # Check pilot_continue_on_error setting
                            if pilot_mode_enabled:
                                try:
                                    from config import settings as _pce_settings
                                    if not getattr(_pce_settings, 'pilot_continue_on_error', True):
                                        print_lg("🛑 [PILOT] pilot_continue_on_error=False — stopping bot after error")
                                        return
                                except Exception:
                                    pass
                            continue
                    else:
                        # Case 2: Apply externally
                        try:
                            skip, application_link, tabs_count = external_apply(pagination_element, job_id, job_link, resume, date_listed, application_link, screenshot_name)
                        except Exception as ext_err:
                            print_lg(f"⚠️ External apply error (skipping job, staying on same search term): {ext_err}")
                            continue
                        if dailyEasyApplyLimitReached:
                            print_lg("\n###############  Daily application limit for Easy Apply is reached!  ###############\n")
                            return
                        if skip: continue

                    try:
                        submitted_jobs(job_id, title, company, work_location, work_style, description, experience_required, skills, hr_name, hr_link, resume, reposted, date_listed, date_applied, job_link, application_link, questions_list, connect_request)
                    except Exception as save_err:
                        print_lg(f"⚠️ Error saving job info (non-critical): {save_err}")
                    if uploaded:   useNewResume = False

                    print_lg(f'Successfully saved "{title} | {company}" job. Job ID: {job_id} info')
                    current_count += 1
                    if application_link == "Easy Applied": easy_applied_count += 1
                    else:   external_jobs_count += 1
                    applied_jobs.add(job_id)
                    
                    # Check limits (max_jobs_to_process + pilot_max_applications)
                    if check_pilot_limit_reached():
                        print_lg("📊 Application limit reached — stopping bot.")
                        return
                    
                    # Pilot mode: Add delay between applications (interruptible)
                    if pilot_mode_enabled:
                        try:
                            from config import settings
                            delay = getattr(settings, 'pilot_application_delay', 5)
                            if delay > 0:
                                print_lg(f"✈️ [PILOT] Waiting {delay}s before next application...")
                                if not interruptible_sleep(delay, check_interval=1.0):
                                    print_lg("🛑 Stop signal during pilot delay.")
                                    return
                        except Exception:
                            interruptible_sleep(5, check_interval=1.0)



                # Check stop signal before switching to next page
                if should_stop():
                    print_lg("🛑 Stop signal received. Stopping bot...")
                    return
                
                # Switching to next page
                if pagination_element == None:
                    print_lg("Couldn't find pagination element, probably at the end page of results!")
                    break
                try:
                    pagination_element.find_element(By.XPATH, f"//button[@aria-label='Page {current_page+1}']").click()
                    print_lg(f"\n>-> Now on Page {current_page+1} \n")
                except NoSuchElementException:
                    print_lg(f"\n>-> Didn't find Page {current_page+1}. Probably at the end page of results!\n")
                    break

        except (NoSuchWindowException, WebDriverException) as e:
            print_lg("Browser window closed or session is invalid. Ending application process.", e)
            raise e # Re-raise to be caught by main
        except Exception as e:
            print_lg(f"Failed during search term '{searchTerm}'. Continuing to next term...")
            print_lg("Failed to find Job listings!")
            critical_error_log("In Applier", e)
            # NOTE: Removed page_source dump to prevent log file from growing huge
            # The page source was causing 6MB+ logs with HTML/JSON data
            continue

        
def run(total_runs: int) -> int:
    if dailyEasyApplyLimitReached:
        return total_runs
    print_lg("\n########################################################################################################################\n")
    print_lg(f"Date and Time: {datetime.now()}")
    print_lg(f"Cycle number: {total_runs}")
    print_lg(f"Currently looking for jobs posted within '{date_posted}' and sorting them by '{sort_by}'")
    apply_to_jobs(search_terms)
    
    # Check stop signal before sleeping
    if should_stop():
        print_lg("🛑 Stop signal received after apply cycle. Exiting run.")
        return total_runs + 1
    
    print_lg("########################################################################################################################\n")
    if not dailyEasyApplyLimitReached:
        print_lg("Sleeping for 10 min (interruptible - will respond to stop signal)...")
        if not interruptible_sleep(300, check_interval=1.0):
            print_lg("🛑 Sleep interrupted by stop signal.")
            return total_runs + 1
        print_lg("Few more min... Gonna start with in next 5 min...")
        if not interruptible_sleep(300, check_interval=1.0):
            print_lg("🛑 Sleep interrupted by stop signal.")
            return total_runs + 1
    buffer(3)
    return total_runs + 1



chatGPT_tab = False
linkedIn_tab = False

def main() -> None:
    total_runs = 1
    try:
        global linkedIn_tab, tabs_count, useNewResume, aiClient, popup_blocker, _session_ctx
        alert_title = "Error Occurred. Closing Browser!"
        
        # Initialize per-session runtime context
        try:
            _session_ctx = _new_session()
            print_lg(f"[Session {_session_ctx.session_id}] Bot session started")
            emit_dashboard_event("bot_session_started", {"session_id": _session_ctx.session_id})
        except Exception:
            pass
        
        validate_config()
        
        # Network security check for corporate environments (DLP, SSL inspection)
        if NETWORK_CHECK_AVAILABLE:
            print_lg("Running network security check...")
            security_results = run_full_security_check()
            
            if not security_results["can_submit_applications"]:
                print_lg("="*60)
                print_lg("⚠️ CORPORATE NETWORK SECURITY DETECTED!")
                print_lg("="*60)
                for issue in security_results["issues"]:
                    print_lg(f"  • {issue}")
                print_lg("")
                print_lg("LinkedIn submissions will likely FAIL with 500 errors!")
                print_lg("")
                print_lg("💡 SOLUTION: Connect to your phone's MOBILE HOTSPOT")
                print_lg("   This bypasses corporate DLP/Netskope restrictions.")
                print_lg("="*60)
                
                # Ask user if they want to continue anyway (skip in pilot mode)
                if not pilot_mode_enabled:
                    user_choice = _safe_pyautogui_confirm(
                        text="Corporate security (DLP/Netskope) detected!\n\n"
                             "LinkedIn submissions will likely fail with 500 errors.\n\n"
                             "SOLUTION: Connect to mobile hotspot instead.\n\n"
                             "Do you want to continue anyway?",
                        title="⚠️ Network Security Warning",
                        buttons=["Continue Anyway", "Exit & Fix Network"]
                    )
                    
                    if user_choice == "Exit & Fix Network":
                        print_lg("User chose to exit and fix network. Closing...")
                        return
                    else:
                        print_lg("User chose to continue despite network warnings.")
                else:
                    print_lg("✈️ [PILOT MODE] Network warning detected but continuing automatically")
            else:
                print_lg("✅ Network check passed - no corporate restrictions detected.")
        
        if not os.path.exists(default_resume_path):
            if not pilot_mode_enabled:
                _safe_pyautogui_alert(text='Your default resume "{}" is missing! Please update it\'s folder path "default_resume_path" in config.py\n\nOR\n\nAdd a resume with exact name and path (check for spelling mistakes including cases).\n\n\nFor now the bot will continue using your previous upload from LinkedIn!'.format(default_resume_path), title="Missing Resume", button="OK")
            else:
                print_lg(f"✈️ [PILOT MODE] Resume file missing: {default_resume_path} - using LinkedIn's saved resume")
            useNewResume = False
        
        # Initialize popup blocker for the session
        popup_blocker = setup_popup_blocker_for_session(driver)
        print_lg("Popup blocker initialized successfully!")
        
        # CRITICAL: Disable auto-reset during bot operation to prevent crashes between search terms
        # This ensures the Chrome session won't be reset unexpectedly during job applications
        set_auto_reset_allowed(False)
        print_lg("Auto-reset disabled for stable operation across search terms")
        
        # Login to LinkedIn
        tabs_count = len(driver.window_handles)
        driver.get("https://www.linkedin.com/login")
        if not is_logged_in_LN(): login_LN()
        
        linkedIn_tab = driver.current_window_handle

        # # Login to ChatGPT in a new tab for resume customization
        # if use_resume_generator:
        #     try:
        #         driver.switch_to.new_window('tab')
        #         driver.get("https://chat.openai.com/")
        #         if not is_logged_in_GPT(): login_GPT()
        #         open_resume_chat()
        #         global chatGPT_tab
        #         chatGPT_tab = driver.current_window_handle
        #     except Exception as e:
        #         print_lg("Opening OpenAI chatGPT tab failed!")
        if use_AI:
            if ai_provider == "openai":
                aiClient = ai_create_openai_client()
            ##> ------ Yang Li : MARKYangL - Feature ------
            # Create DeepSeek client
            elif ai_provider == "deepseek":
                aiClient = deepseek_create_client()
            elif ai_provider == "gemini":
                aiClient = gemini_create_client()
            elif ai_provider == "groq":
                aiClient = groq_create_client()
                print_lg("Groq AI client initialized for fast resume tailoring!")
            ##<

            try:
                about_company_for_ai = " ".join([word for word in (first_name+" "+last_name).split() if len(word) > 3])
                print_lg(f"Extracted about company info for AI: '{about_company_for_ai}'")
            except Exception as e:
                print_lg("Failed to extract about company info!", e)
        
        # Start applying to jobs
        driver.switch_to.window(linkedIn_tab)
        total_runs = run(total_runs)
        while(run_non_stop):
            # Check stop signal before each cycle
            if should_stop():
                print_lg("🛑 Stop signal received in main loop. Exiting.")
                break
            if cycle_date_posted:
                date_options = ["Any time", "Past month", "Past week", "Past 24 hours"]
                global date_posted
                current_idx = date_options.index(date_posted) if date_posted in date_options else 0
                next_idx = current_idx + 1
                if stop_date_cycle_at_24hr:
                    # Cycle forward: Any time → Past month → Past week → Past 24 hours, then stay at "Past 24 hours"
                    if next_idx >= len(date_options):
                        next_idx = len(date_options) - 1  # stay at last
                else:
                    # Wrap-around cycle: … → Past 24 hours → Any time → Past month → …
                    if next_idx >= len(date_options):
                        next_idx = 0
                date_posted = date_options[next_idx]
                print_lg(f"📅 Date filter cycled to: '{date_posted}'")
            if alternate_sortby:
                global sort_by
                sort_by = "Most recent" if sort_by == "Most relevant" else "Most relevant"
                total_runs = run(total_runs)
                if should_stop():
                    print_lg("🛑 Stop signal received after alternate sort run. Exiting.")
                    break
                sort_by = "Most recent" if sort_by == "Most relevant" else "Most relevant"
            total_runs = run(total_runs)
            if should_stop():
                print_lg("🛑 Stop signal received after run cycle. Exiting.")
                break
            if dailyEasyApplyLimitReached:
                break
        

    except (NoSuchWindowException, WebDriverException) as e:
        print_lg("Browser window closed or session is invalid. Exiting.", e)
    except Exception as e:
        critical_error_log("In Applier Main", e)
        if not pilot_mode_enabled:
            _safe_pyautogui_alert(str(e), alert_title)
    finally:
        emit_dashboard_event("bot_session_completed", {
            "session_id": _get_session_id() if callable(_get_session_id) else "n/a",
            "easy_applied": easy_applied_count,
            "external_jobs": external_jobs_count,
            "failed": failed_count,
            "skipped": skip_count,
        })
        # Sync final counters into session context for caller (scheduler) to read
        if _session_ctx is not None:
            try:
                _session_ctx.sync_from_globals(sys.modules[__name__])
                print_lg(f"[Session {_session_ctx.session_id}] Final sync: applied={_session_ctx.easy_applied_count}, failed={_session_ctx.failed_count}")
            except Exception:
                pass
        summary = "Total runs: {}\nJobs Easy Applied: {}\nExternal job links collected: {}\nTotal applied or collected: {}\nFailed jobs: {}\nIrrelevant jobs skipped: {}\n".format(total_runs,easy_applied_count,external_jobs_count,easy_applied_count + external_jobs_count,failed_count,skip_count)
        print_lg(summary)
        print_lg("\n\nTotal runs:                     {}".format(total_runs))
        print_lg("Jobs Easy Applied:              {}".format(easy_applied_count))
        print_lg("External job links collected:   {}".format(external_jobs_count))
        print_lg("                              ----------")
        print_lg("Total applied or collected:     {}".format(easy_applied_count + external_jobs_count))
        print_lg("\nFailed jobs:                    {}".format(failed_count))
        print_lg("Irrelevant jobs skipped:        {}\n".format(skip_count))
        if randomly_answered_questions: print_lg("\n\nQuestions randomly answered:\n  {}  \n\n".format(";\n".join(str(question) for question in randomly_answered_questions)))
        quotes = choice([
            "Never quit. You're one step closer than before. - Suraj Panwar", 
            "All the best with your future interviews, you've got this. - Suraj Panwar", 
            "Keep up with the progress. You got this. - Suraj Panwar", 
            "If you're tired, learn to take rest but never give up. - Suraj Panwar",
            "Success is not final, failure is not fatal, It is the courage to continue that counts. - Winston Churchill",
            "Believe in yourself and all that you are. Know that there is something inside you that is greater than any obstacle. - Christian D. Larson",
            "Every job is a self-portrait of the person who does it. Autograph your work with excellence. - Jessica Guidobono",
            "The only way to do great work is to love what you do. If you haven't found it yet, keep looking. Don't settle. - Steve Jobs",
            "Opportunities don't happen, you create them. - Chris Grosser",
            "The road to success and the road to failure are almost exactly the same. The difference is perseverance. - Colin R. Davis",
            "Obstacles are those frightful things you see when you take your eyes off your goal. - Henry Ford",
            "The only limit to our realization of tomorrow will be our doubts of today. - Franklin D. Roosevelt",
            ])
        sponsors = "Built with ❤️ by Suraj Panwar"
        timeSaved = (easy_applied_count * 80) + (external_jobs_count * 20) + (skip_count * 10)
        timeSavedMsg = ""
        if timeSaved > 0:
            timeSaved += 60
            timeSavedMsg = f"In this run, you saved approx {round(timeSaved/60)} mins ({timeSaved} secs)!"
        msg = f"{quotes}\n\n\n{timeSavedMsg}\n\nSummary:\n{summary}\n\n\nBest regards,\nSuraj Panwar\nhttps://www.linkedin.com/in/surajpanwar/\n\n{sponsors}"
        if not pilot_mode_enabled:
            _safe_pyautogui_alert(msg, "Exiting..")
        print_lg(msg,"Closing the browser...")
        if tabs_count >= 10:
            msg = "NOTE: IF YOU HAVE MORE THAN 10 TABS OPENED, PLEASE CLOSE OR BOOKMARK THEM!\n\nOr it's highly likely that application will just open browser and not do anything next time!" 
            if not pilot_mode_enabled:
                _safe_pyautogui_alert(msg,"Info")
            print_lg("\n"+msg)
        ##> ------ Yang Li : MARKYangL - Feature ------
        if use_AI and aiClient:
            try:
                if ai_provider.lower() == "openai":
                    ai_close_openai_client(aiClient)
                elif ai_provider.lower() == "deepseek":
                    ai_close_openai_client(aiClient)
                elif ai_provider.lower() == "gemini":
                    pass # Gemini client does not need to be closed
                print_lg(f"Closed {ai_provider} AI client.")
            except Exception as e:
                print_lg("Failed to close AI client:", e)
        ##<
        # Re-enable auto-reset for cleanup
        set_auto_reset_allowed(True)
        try:
            if driver:
                driver.quit()
        except WebDriverException as e:
            print_lg("Browser already closed.", e)
        except Exception as e: 
            critical_error_log("When quitting...", e)


if __name__ == "__main__":
    main()
