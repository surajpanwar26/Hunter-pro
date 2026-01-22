'''
Author:     Suraj Panwar
LinkedIn:   https://www.linkedin.com/in/surajpanwar26/

Copyright (C) 2024 Suraj Panwar

License:    GNU Affero General Public License
            https://www.gnu.org/licenses/agpl-3.0.en.html
            
GitHub:     https://github.com/surajpanwar26/Auto_job_applier_linkedIn

version:    24.12.29.12.30
'''


# Imports
import os
import csv
import re
import pyautogui

# Set CSV field size limit to prevent field size errors
csv.field_size_limit(1000000)  # Set to 1MB instead of default 131KB

from random import choice, shuffle, randint
from datetime import datetime
from time import sleep

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.select import Select
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import (
    NoSuchElementException, 
    ElementClickInterceptedException, 
    NoSuchWindowException, 
    ElementNotInteractableException, 
    WebDriverException
)

from config.personals import *
from config.questions import *
from config.search import *
from config.secrets import use_AI, username, password, ai_provider
from config.settings import *

from modules.open_chrome import start_chrome, close_driver
from modules.helpers import *
from modules.clickers_and_finders import *
from modules.validator import validate_config
from modules.ai.prompt_safety import sanitize_prompt_input, wrap_delimited

# Import fault tolerance utilities
try:
    from modules.fault_tolerance import (
        retry_with_backoff, 
        RetryConfig, 
        safe_execute, 
        get_ai_circuit_breaker,
        get_selenium_circuit_breaker,
        with_circuit_breaker
    )
    from modules.resource_manager import get_session_manager, get_resource_manager
    FAULT_TOLERANCE_AVAILABLE = True
except ImportError:
    FAULT_TOLERANCE_AVAILABLE = False
    # Fallback decorator if fault tolerance not available
    def retry_with_backoff(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    
    def safe_execute(func, *args, default=None, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            return default

# ============ LEARNED ANSWERS SYSTEM ============
import json
import tkinter as tk
from tkinter import simpledialog, messagebox
from threading import Thread, Event

LEARNED_ANSWERS_FILE = os.path.join(os.path.dirname(__file__), "config", "learned_answers.json")

def load_learned_answers() -> dict:
    """Load previously learned answers from JSON file"""
    try:
        if os.path.exists(LEARNED_ANSWERS_FILE):
            with open(LEARNED_ANSWERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print_lg(f"Warning: Could not load learned answers: {e}")
    return {
        "text_answers": {},
        "select_answers": {},
        "radio_answers": {},
        "textarea_answers": {},
        "checkbox_answers": {}
    }

def save_learned_answers(data: dict):
    """Save learned answers to JSON file"""
    try:
        data["_last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LEARNED_ANSWERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print_lg(f"✅ Saved learned answer to {LEARNED_ANSWERS_FILE}")
    except Exception as e:
        print_lg(f"Warning: Could not save learned answers: {e}")

def get_learned_answer(question: str, question_type: str) -> str | None:
    """Get a previously learned answer for a question"""
    data = load_learned_answers()
    key = f"{question_type}_answers"
    if key in data:
        # Normalize question for matching (lowercase, strip whitespace)
        normalized = question.lower().strip()
        for saved_q, answer in data[key].items():
            if saved_q.lower().strip() == normalized or normalized in saved_q.lower():
                return answer
    return None

def save_learned_answer(question: str, answer: str, question_type: str):
    """Save a new learned answer"""
    data = load_learned_answers()
    key = f"{question_type}_answers"
    if key not in data:
        data[key] = {}
    data[key][question] = answer
    save_learned_answers(data)

# Global for user intervention
_user_intervention_result = None
_user_intervention_event = Event()

def ask_user_for_answer(question: str, options: list = None, question_type: str = "text") -> str | None:
    """
    Show a popup dialog asking user for answer to unknown question.
    Returns the answer or None if skipped.
    """
    global _user_intervention_result, _user_intervention_event
    
    _user_intervention_result = None
    _user_intervention_event.clear()
    
    def show_dialog():
        global _user_intervention_result
        try:
            root = tk.Tk()
            root.withdraw()  # Hide main window
            root.attributes('-topmost', True)
            
            # Build message
            msg = f"🤖 Unknown Question Encountered!\n\n"
            msg += f"Question: {question}\n\n"
            if options:
                msg += f"Available Options:\n"
                for i, opt in enumerate(options, 1):
                    msg += f"  {i}. {opt}\n"
                msg += "\n"
            msg += f"Type: {question_type}\n\n"
            msg += "Please provide an answer (or click Cancel to skip):"
            
            if options and question_type in ["select", "radio"]:
                # Show choice dialog for select/radio
                result = simpledialog.askstring(
                    "📝 User Input Required",
                    msg,
                    parent=root
                )
            else:
                # Show text input for text/textarea
                result = simpledialog.askstring(
                    "📝 User Input Required",
                    msg,
                    parent=root
                )
            
            _user_intervention_result = result
            root.destroy()
        except Exception as e:
            print_lg(f"Dialog error: {e}")
            _user_intervention_result = None
        finally:
            _user_intervention_event.set()
    
    # Run dialog in separate thread to avoid blocking
    dialog_thread = Thread(target=show_dialog, daemon=True)
    dialog_thread.start()
    
    # Wait for user input with timeout (60 seconds)
    _user_intervention_event.wait(timeout=60)
    
    return _user_intervention_result

def robust_answer_unknown_question(question: str, options: list = None, question_type: str = "text", 
                                    job_description: str = None) -> tuple[str, bool]:
    """
    Robust handler for unknown questions:
    1. Check learned answers first
    2. Try AI if enabled
    3. Ask user for intervention
    4. Save the answer for future use
    
    Returns: (answer, was_user_input)
    """
    # 1. Check learned answers first (fastest)
    learned = get_learned_answer(question, question_type)
    if learned:
        print_lg(f"✅ Using learned answer for '{question[:50]}...': {learned[:50]}...")
        return learned, False
    
    # 2. Try AI if available
    if use_AI and aiClient:
        try:
            ai_answer = None
            if ai_provider.lower() == "ollama":
                from modules.ai import ollama_integration as _oll
                safe_q = sanitize_prompt_input(question, max_len=500)
                safe_jd = sanitize_prompt_input(job_description or "", max_len=1500)
                options_str = ", ".join(options) if options else "free text"
                prompt = f"Answer this job application question concisely. Question: {safe_q}. Options: {options_str}. Job: {safe_jd}"
                ai_answer = _oll.generate(prompt, timeout=20)
            elif ai_provider.lower() == "openai":
                ai_answer = ai_answer_question(aiClient, question, question_type=question_type, 
                                               job_description=job_description, user_information_all=user_information_all)
            elif ai_provider.lower() == "deepseek":
                ai_answer = deepseek_answer_question(aiClient, question, options=options, question_type=question_type,
                                                    job_description=job_description, user_information_all=user_information_all)
            elif ai_provider.lower() == "gemini":
                ai_answer = gemini_answer_question(aiClient, question, options=options, question_type=question_type,
                                                  job_description=job_description, user_information_all=user_information_all)
            
            if ai_answer and len(ai_answer.strip()) > 0:
                # Save AI answer for future
                save_learned_answer(question, ai_answer.strip(), question_type)
                print_lg(f"✅ AI answered and saved: '{question[:40]}...' -> '{ai_answer[:40]}...'")
                return ai_answer.strip(), False
        except Exception as e:
            print_lg(f"AI failed for question: {e}")
    
    # 3. Ask user for intervention if pause_at_failed_question is True
    if pause_at_failed_question and not run_in_background:
        print_lg(f"⚠️ UNKNOWN QUESTION - Requesting user input for: {question[:60]}...")
        user_answer = ask_user_for_answer(question, options, question_type)
        
        if user_answer and len(user_answer.strip()) > 0:
            # Save user answer for future reference
            save_learned_answer(question, user_answer.strip(), question_type)
            print_lg(f"✅ User provided answer saved: '{question[:40]}...' -> '{user_answer[:40]}...'")
            return user_answer.strip(), True
    
    # 4. Fallback to default or empty
    print_lg(f"⚠️ No answer found for: {question[:60]}... Using fallback")
    return "", False

# ============ END LEARNED ANSWERS SYSTEM ============

if use_AI:
    from modules.ai.openaiConnections import ai_create_openai_client, ai_extract_skills, ai_answer_question, ai_close_openai_client
    from modules.ai.deepseekConnections import deepseek_create_client, deepseek_extract_skills, deepseek_answer_question, deepseek_close_client
    from modules.ai.geminiConnections import gemini_create_client, gemini_extract_skills, gemini_answer_question
    from modules.ai.resume_tailoring import tailor_resume_to_files, open_preview

from typing import Literal


pyautogui.FAILSAFE = False


# Global error tracking for fault tolerance
_consecutive_failures = 0
_max_consecutive_failures = 10
_last_successful_operation = None


def track_success():
    """Track successful operations to reset failure counter."""
    global _consecutive_failures, _last_successful_operation
    _consecutive_failures = 0
    _last_successful_operation = datetime.now()


def track_failure():
    """Track failures and check if we should abort."""
    global _consecutive_failures
    _consecutive_failures += 1
    if _consecutive_failures >= _max_consecutive_failures:
        print_lg(f"WARNING: {_consecutive_failures} consecutive failures detected!")
        return True
    return False


def should_abort():
    """Check if we should abort due to too many failures."""
    return _consecutive_failures >= _max_consecutive_failures
# if use_resume_generator:    from resume_generator import is_logged_in_GPT, login_GPT, open_resume_chat, create_custom_resume


#< Global Variables and logics

if run_in_background == True:
    pause_at_failed_question = False
    pause_before_submit = False
    run_non_stop = False

first_name = first_name.strip()
middle_name = middle_name.strip()
last_name = last_name.strip()
full_name = first_name + " " + middle_name + " " + last_name if middle_name else first_name + " " + last_name

useNewResume = True
randomly_answered_questions = set()

tabs_count = 1
easy_applied_count = 0
external_jobs_count = 0
failed_count = 0
skip_count = 0
dailyEasyApplyLimitReached = False

re_experience = re.compile(r'[(]?\s*(\d+)\s*[)]?\s*[-to]*\s*\d*[+]*\s*year[s]?', re.IGNORECASE)

desired_salary_lakhs = str(round(desired_salary / 100000, 2))
desired_salary_monthly = str(round(desired_salary/12, 2))
desired_salary = str(desired_salary)

current_ctc_lakhs = str(round(current_ctc / 100000, 2))
current_ctc_monthly = str(round(current_ctc/12, 2))
current_ctc = str(current_ctc)

notice_period_months = str(notice_period//30)
notice_period_weeks = str(notice_period//7)
notice_period = str(notice_period)

aiClient = None
##> ------ Dheeraj Deshwal : dheeraj9811 Email:dheeraj20194@iiitd.ac.in/dheerajdeshwal9811@gmail.com - Feature ------
about_company_for_ai = None # TODO extract about company for AI
##<

#>


# Runner control helpers
import threading
import subprocess
_bot_thread: threading.Thread | None = None
_stop_requested = False
_chrome_pid: int | None = None


def is_stop_requested() -> bool:
    """Check if stop has been requested - use this in loops."""
    return _stop_requested


def start_bot_thread() -> bool:
    """Start the bot in a background thread. Returns False if already running."""
    global _bot_thread, _stop_requested
    if _bot_thread and _bot_thread.is_alive():
        return False
    _stop_requested = False
    _bot_thread = threading.Thread(target=main, daemon=True)
    _bot_thread.start()
    return True


def _kill_chrome_processes() -> None:
    """Kill all Chrome processes associated with this bot."""
    import os
    print_lg("Killing Chrome processes...")
    try:
        if os.name == 'nt':  # Windows
            # Kill chromedriver and chrome processes
            subprocess.run(['taskkill', '/F', '/IM', 'chromedriver.exe'], 
                         capture_output=True, timeout=5)
            subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], 
                         capture_output=True, timeout=5)
        else:  # Linux/Mac
            subprocess.run(['pkill', '-f', 'chromedriver'], 
                         capture_output=True, timeout=5)
            subprocess.run(['pkill', '-f', 'chrome'], 
                         capture_output=True, timeout=5)
        print_lg("Chrome processes terminated.")
    except Exception as e:
        print_lg(f"Error killing Chrome processes: {e}")


def stop_bot() -> None:
    """Request stop and forcefully terminate all bot processes."""
    global _stop_requested, run_non_stop, driver, _bot_thread
    _stop_requested = True
    print_lg("Stop requested - shutting down bot...")
    
    # Stop the run loop
    try:
        run_non_stop = False
    except Exception:
        pass
    
    # Try graceful driver close first
    try:
        close_driver()
    except Exception as e:
        print_lg(f"Error during graceful close: {e}")
    
    # Give a moment for graceful shutdown
    sleep(0.5)
    
    # Force kill Chrome processes if still running
    _kill_chrome_processes()
    
    # Wait for the thread to finish (with timeout)
    if _bot_thread and _bot_thread.is_alive():
        print_lg("Waiting for bot thread to finish...")
        _bot_thread.join(timeout=3.0)
        if _bot_thread.is_alive():
            print_lg("Bot thread did not stop gracefully - processes killed.")
        else:
            print_lg("Bot thread stopped cleanly.")
    
    _bot_thread = None
    print_lg("Bot stopped completely.")


def is_bot_running() -> bool:
    return _bot_thread is not None and _bot_thread.is_alive()


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
    try:
        wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Forgot password?")))
        try:
            text_input_by_ID(driver, "username", username, 1)
        except Exception:
            print_lg("Couldn't find username field.")
            # print_lg(e)
        try:
            text_input_by_ID(driver, "password", password, 1)
        except Exception:
            print_lg("Couldn't find password field.")
            # print_lg(e)
        # Find the login submit button and click it
        login_button = driver.find_element(By.XPATH, '//button[@type="submit" and contains(text(), "Sign in")]')
        login_button.click()
        buffer(3)  # Wait for login to process
    except Exception:
        try:
            profile_button = find_by_class(driver, "profile__details")
            profile_button.click()
        except Exception:
            # print_lg(e1, e2)
            print_lg("Couldn't Login!")

    try:
        # Wait until successful redirect, indicating successful login
        wait.until(EC.url_to_be("https://www.linkedin.com/feed/")) # wait.until(EC.presence_of_element_located((By.XPATH, '//button[normalize-space(.)="Start a post"]')))
        return print_lg("Login successful!")
    except Exception:
        # Check if already logged in by checking if we're on the feed page
        if driver.current_url == "https://www.linkedin.com/feed/":
            return print_lg("Already logged in!")
        # Check if we're on the home page which is also a valid logged-in state
        elif "linkedin.com" in driver.current_url and ("feed" in driver.current_url or "home" in driver.current_url):
            return print_lg("Successfully logged in!")
        else:
            print_lg("Seems like login attempt failed! Possibly due to wrong credentials. Try logging in manually!")
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
    Function to apply job search filters
    '''
    set_search_location()

    try:
        # Use shorter waits for faster execution
        recommended_wait = 1
        short_wait = 0.5

        # Wait before clicking All filters
        buffer(short_wait)
        wait.until(EC.presence_of_element_located((By.XPATH, '//button[normalize-space()="All filters"]'))).click()
        buffer(recommended_wait)

        wait_span_click(driver, sort_by)
        wait_span_click(driver, date_posted)
        buffer(short_wait)

        multi_sel_noWait(driver, experience_level) 
        multi_sel_noWait(driver, companies, actions)
        if experience_level or companies: buffer(short_wait)

        multi_sel_noWait(driver, job_type)
        multi_sel_noWait(driver, on_site)
        if job_type or on_site: buffer(short_wait)

        if easy_apply_only: 
            boolean_button_click(driver, actions, "Easy Apply")
        
        multi_sel_noWait(driver, location)
        multi_sel_noWait(driver, industry)
        if location or industry: buffer(short_wait)

        multi_sel_noWait(driver, job_function)
        multi_sel_noWait(driver, job_titles)
        if job_function or job_titles: buffer(short_wait)

        if under_10_applicants: 
            boolean_button_click(driver, actions, "Under 10 applicants")
        if in_your_network: 
            boolean_button_click(driver, actions, "In your network")
        if fair_chance_employer: 
            boolean_button_click(driver, actions, "Fair Chance Employer")

        wait_span_click(driver, salary)
        
        multi_sel_noWait(driver, benefits)
        multi_sel_noWait(driver, commitments)
        if benefits or commitments: buffer(short_wait)

        # Brief wait before clicking show results
        buffer(recommended_wait)
        
        # Try multiple selectors for the show results button
        show_results_button = None
        button_selectors = [
            '//button[contains(@aria-label, "Apply current filters")]',
            '//button[contains(@aria-label, "Show") and contains(@aria-label, "result")]',
            '//button[starts-with(normalize-space(), "Show") and contains(normalize-space(), "result")]',
            '//button[contains(normalize-space(), "Show") and (contains(normalize-space(), "result") or contains(normalize-space(), "+"))]',
            '//div[contains(@class, "search-reusables__filters")]//button[contains(@class, "artdeco-button--primary")]',
            '//button[contains(@class, "search-reusables__filter") and contains(@class, "apply")]',
            '//footer//button[contains(@class, "artdeco-button--primary")]',
        ]
        
        for selector in button_selectors:
            try:
                show_results_button = driver.find_element(By.XPATH, selector)
                if show_results_button and show_results_button.is_displayed() and show_results_button.is_enabled():
                    break
                show_results_button = None
            except:
                continue
        
        if show_results_button:
            scroll_to_view(driver, show_results_button)
            try:
                show_results_button.click()
            except ElementClickInterceptedException:
                # Try JavaScript click as fallback
                driver.execute_script("arguments[0].click();", show_results_button)
            buffer(recommended_wait)
            print_lg("Filters applied successfully!")
        else:
            # Fallback: try to find any primary button in the filter modal footer
            try:
                footer_btn = driver.find_element(By.XPATH, '//div[contains(@class, "artdeco-modal__actionbar")]//button[contains(@class, "primary")]')
                footer_btn.click()
                buffer(recommended_wait)
                print_lg("Filters applied using footer button!")
            except:
                print_lg("Could not find the 'Show results' button, trying to close filter panel...")
                try:
                    close_btn = driver.find_element(By.XPATH, '//button[@aria-label="Dismiss"]')
                    close_btn.click()
                except:
                    # Press Escape as last resort
                    actions.send_keys(Keys.ESCAPE).perform()

        global pause_after_filters
        if pause_after_filters and "Turn off Pause after search" == pyautogui.confirm("These are your configured search results and filter. It is safe to change them while this dialog is open, any changes later could result in errors and skipping this search run.", "Please check your results", ["Turn off Pause after search", "Look's good, Continue"]):
            pause_after_filters = False

    except Exception as e:
        print_lg("Setting the preferences failed!")
        print_lg(e)



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
    job_details_button = job.find_element(By.TAG_NAME, 'a')  # job.find_element(By.CLASS_NAME, "job-card-list__title")  # Problem in India
    scroll_to_view(driver, job_details_button, True)
    job_id = job.get_dom_attribute('data-occludable-job-id')
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
    
    # Skip if previously rejected due to blacklist or already applied
    skip = False
    if company in blacklisted_companies:
        print_lg(f'⛔ BLACKLISTED: {company} - skipping')
        skip = True
    elif job_id in rejected_jobs: 
        print_lg(f'⏭️ SKIP: Previously rejected job')
        skip = True
    try:
        if job.find_element(By.CLASS_NAME, "job-card-container__footer-job-state").text == "Applied":
            skip = True
            print_lg(f'⏭️ SKIP: Already applied to {company}')
    except: pass
    try: 
        if not skip: 
            # Add human-like delay before clicking on job
            human_delay(0.5, 1.5)
            job_details_button.click()
    except Exception:
        print_lg(f'⚠️ Could not click job details button') 
        # print_lg(e)
        discard_job()
        human_delay(0.3, 0.8)
        job_details_button.click() # To pass the error outside
    # Wait for job details to load
    human_delay(1.0, 2.0)
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
    try:
        ##> ------ Dheeraj Deshwal : dheeraj9811 Email:dheeraj20194@iiitd.ac.in/dheerajdeshwal9811@gmail.com - Feature ------
        jobDescription = "Unknown"
        ##<
        experience_required = "Unknown"
        found_masters = 0
        jobDescription = find_by_class(driver, "jobs-box__html-content").text
        jobDescriptionLow = jobDescription.lower()
        skip = False
        skipReason = None
        skipMessage = None
        for word in bad_words:
            if word.lower() in jobDescriptionLow:
                skipMessage = f'\n{jobDescription}\n\nContains bad word "{word}". Skipping this job!\n'
                skipReason = "Found a Bad Word in About Job"
                skip = True
                break
        if not skip and security_clearance == False and ('polygraph' in jobDescriptionLow or 'clearance' in jobDescriptionLow or 'secret' in jobDescriptionLow):
            skipMessage = f'\n{jobDescription}\n\nFound "Clearance" or "Polygraph". Skipping this job!\n'
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
    except Exception:
        if jobDescription == "Unknown":    print_lg("Unable to extract job description!")
        else:
            experience_required = "Error in extraction"
            print_lg("Unable to extract years of experience required!")
            # print_lg(e)
    
    return jobDescription, experience_required, skip, skipReason, skipMessage
        


# Function to dismiss popups that may appear during application
def dismiss_deloitte_popup() -> None:
    """Dismiss Deloitte or similar upload popup if it appears.
    Handles both browser-based popups and external/overlay popups from corporate tools.
    """
    try:
        from modules.helpers import human_delay
        import pyautogui
        
        human_delay(0.5, 1.0)  # Wait for popup to appear
        
        # First, try to dismiss using keyboard (works for most popups)
        # Press Enter to click the default OK button, or Escape to close
        try:
            pyautogui.press('enter')
            human_delay(0.3, 0.5)
            print_lg("Pressed Enter to dismiss popup")
        except Exception:
            pass
        
        # Try browser-based selectors as backup
        popup_selectors = [
            # LinkedIn modal popups with OK button
            "//div[contains(@class, 'artdeco-modal')]//button[normalize-space()='OK']",
            "//div[contains(@class, 'artdeco-modal')]//button[contains(text(), 'OK')]",
            "//div[contains(@class, 'modal')]//button[normalize-space()='OK']",
            # Footer buttons in modals
            "//footer//button[normalize-space()='OK']",
            # Generic OK buttons
            "//button[normalize-space()='OK']",
            "//button[text()='OK']",
            # Primary buttons
            "//button[contains(@class, 'artdeco-button--primary')][last()]",
            # Toast notifications
            "//div[contains(@class, 'artdeco-toast')]//button",
            # Dismiss buttons
            "//button[@aria-label='Dismiss']",
            # Dialog buttons
            "//div[@role='dialog']//button[normalize-space()='OK']",
        ]
        
        for selector in popup_selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for elem in elements:
                    if elem.is_displayed() and elem.is_enabled():
                        try:
                            elem.click()
                            human_delay(0.3, 0.5)
                            print_lg("Dismissed browser popup")
                            return
                        except Exception:
                            try:
                                driver.execute_script("arguments[0].click();", elem)
                                human_delay(0.3, 0.5)
                                return
                            except Exception:
                                continue
            except Exception:
                continue
        
        # If browser selectors didn't work, try clicking bottom-right area with pyautogui
        # This handles external/overlay popups from corporate tools like Deloitte Pendo
        try:
            screen_width, screen_height = pyautogui.size()
            # Bottom-right corner where OK buttons typically appear
            ok_button_x = screen_width - 150  # 150 pixels from right edge
            ok_button_y = screen_height - 100  # 100 pixels from bottom
            
            # Try clicking in the approximate area where OK button might be
            pyautogui.click(ok_button_x, ok_button_y)
            human_delay(0.2, 0.4)
            print_lg(f"Clicked bottom-right area ({ok_button_x}, {ok_button_y}) to dismiss external popup")
        except Exception:
            pass
            
    except Exception:
        pass


# Function to upload resume
def upload_resume(modal: WebElement, resume: str) -> tuple[bool, str]:
    try:
        # Check if the resume file exists before attempting upload
        if not os.path.exists(resume):
            print_lg(f"Resume file does not exist: {resume}")
            return False, "Previous resume"
        
        # Check if the resume is a valid PDF file
        if not resume.lower().endswith('.pdf'):
            print_lg(f"Resume file is not a PDF: {resume}")
            return False, "Previous resume"
        
        # Try multiple selectors to find the file input
        file_input = None
        selectors = [
            (By.NAME, "file"),
            (By.CSS_SELECTOR, "input[type='file']"),
            (By.XPATH, ".//input[@type='file']"),
            (By.CSS_SELECTOR, "input[name='resume']"),
            (By.XPATH, ".//input[contains(@id, 'file')]"),
        ]
        
        for by, selector in selectors:
            try:
                file_input = modal.find_element(by, selector)
                if file_input:
                    break
            except NoSuchElementException:
                continue
        
        # Also try searching in the whole driver if not found in modal
        if not file_input:
            for by, selector in selectors:
                try:
                    file_input = driver.find_element(by, selector)
                    if file_input:
                        break
                except NoSuchElementException:
                    continue
        
        if file_input:
            file_input.send_keys(os.path.abspath(resume))
            dismiss_deloitte_popup()
            print_lg(f"Successfully uploaded resume: {os.path.basename(resume)}")
            return True, os.path.basename(resume)
        else:
            print_lg("Could not find file input field for resume upload - might already have resume uploaded")
            return False, "Previous resume"
    except Exception as e:
        print_lg(f"Failed to upload resume: {e}")
        return False, "Previous resume"

# Function to answer common questions for Easy Apply
def answer_common_questions(label: str, answer: str) -> str:
    if 'sponsorship' in label or 'visa' in label: answer = require_visa
    return answer


# Function to answer the questions for Easy Apply
def answer_questions(modal: WebElement, questions_list: set, work_location: str, job_description: str | None = None ) -> set:
    # Get all questions from the page
     
    all_questions = modal.find_elements(By.XPATH, ".//div[@data-test-form-element]")
    # all_questions = modal.find_elements(By.CLASS_NAME, "jobs-easy-apply-form-element")
    # all_list_questions = modal.find_elements(By.XPATH, ".//div[@data-test-text-entity-list-form-component]")
    # all_single_line_questions = modal.find_elements(By.XPATH, ".//div[@data-test-single-line-text-form-component]")
    # all_questions = all_questions + all_list_questions + all_single_line_questions

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
            if label != "phone country code":
                optionsText = [option.text for option in select.options]
                options = "".join([f' "{option}",' for option in optionsText])
            prev_answer = selected_option
            if overwrite_previous_answers or selected_option == "Select an option":
                ##> ------ WINDY_WINDWARD Email:karthik.sarode23@gmail.com - Added fuzzy logic to answer location based questions ------
                if 'email' in label or 'phone' in label: 
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
                except NoSuchElementException:
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
                        # Try robust answer system with user intervention
                        print_lg(f'⚠️ No matching option for "{answer}" in question "{label_org}"')
                        
                        # Check learned answers first
                        learned = get_learned_answer(label_org, "select")
                        if learned:
                            # Try to match learned answer to an option
                            for option in optionsText:
                                if learned.lower() in option.lower() or option.lower() in learned.lower():
                                    select.select_by_visible_text(option)
                                    answer = option
                                    foundOption = True
                                    print_lg(f"✅ Used learned answer: {option}")
                                    break
                        
                        if not foundOption:
                            # Ask user for intervention
                            user_answer, _ = robust_answer_unknown_question(
                                label_org,
                                options=optionsText,
                                question_type="select",
                                job_description=job_description
                            )
                            
                            if user_answer:
                                # Try to match user answer to options
                                for option in optionsText:
                                    if user_answer.lower() in option.lower() or option.lower() in user_answer.lower():
                                        select.select_by_visible_text(option)
                                        answer = option
                                        foundOption = True
                                        break
                                    # Also try by index if user entered a number
                                    try:
                                        idx = int(user_answer) - 1
                                        if 0 <= idx < len(optionsText):
                                            select.select_by_visible_text(optionsText[idx])
                                            answer = optionsText[idx]
                                            foundOption = True
                                            break
                                    except ValueError:
                                        pass
                        
                        # Ultimate fallback - random selection
                        if not foundOption:
                            print_lg(f'Answering randomly for "{label_org}"')
                            select.select_by_index(randint(1, len(select.options)-1))
                            answer = select.first_selected_option.text
                            randomly_answered_questions.add((f'{label_org} [ {options} ]',"select"))
            questions_list.add((f'{label_org} [ {options} ]', answer, "select", prev_answer))
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
                    
                    # If still not found, use robust answer system
                    if not foundOption:
                        # Check learned answers
                        learned = get_learned_answer(label_org, "radio")
                        if learned:
                            for i, opt_label in enumerate(options_labels):
                                if learned.lower() in opt_label.lower():
                                    ele = options[i]
                                    answer = opt_label
                                    foundOption = ele
                                    print_lg(f"✅ Used learned answer for radio: {opt_label}")
                                    break
                        
                        if not foundOption:
                            # Ask user
                            clean_options = [ol.split('"')[1] if '"' in ol else ol for ol in options_labels]
                            user_answer, _ = robust_answer_unknown_question(
                                label_org.replace(' [ ', ''),
                                options=clean_options,
                                question_type="radio",
                                job_description=job_description
                            )
                            if user_answer:
                                for i, opt_label in enumerate(options_labels):
                                    if user_answer.lower() in opt_label.lower():
                                        ele = options[i]
                                        answer = opt_label
                                        foundOption = ele
                                        break
                                    # Try by index
                                    try:
                                        idx = int(user_answer) - 1
                                        if 0 <= idx < len(options):
                                            ele = options[idx]
                                            answer = options_labels[idx]
                                            foundOption = ele
                                            break
                                    except ValueError:
                                        pass
                    
                    actions.move_to_element(ele).click().perform()
                    if not foundOption: randomly_answered_questions.add((f'{label_org} ]',"radio"))
            else: answer = prev_answer
            questions_list.add((label_org+" ]", answer, "radio", prev_answer))
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
                if 'experience' in label or 'years' in label: answer = years_of_experience
                elif 'phone' in label or 'mobile' in label: answer = phone_number
                elif 'street' in label: answer = street
                elif 'city' in label or 'location' in label or 'address' in label:
                    answer = current_city if current_city else work_location
                    do_actions = True
                elif 'signature' in label: answer = full_name # 'signature' in label or 'legal name' in label or 'your name' in label or 'full name' in label: answer = full_name     # What if question is 'name of the city or university you attend, name of referral etc?'
                elif 'name' in label:
                    if 'full' in label: answer = full_name
                    elif 'first' in label and 'last' not in label: answer = first_name
                    elif 'middle' in label and 'last' not in label: answer = middle_name
                    elif 'last' in label and 'first' not in label: answer = last_name
                    elif 'employer' in label: answer = recent_employer
                    else: answer = full_name
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
                elif ('hear' in label or 'come across' in label) and 'this' in label and ('job' in label or 'position' in label): answer = "https://github.com/GodsScion/Auto_job_applier_linkedIn"
                elif 'state' in label or 'province' in label: answer = state
                elif 'zip' in label or 'postal' in label or 'code' in label: answer = zipcode
                elif 'country' in label: answer = country
                else: answer = answer_common_questions(label,answer)
                
                # Use robust answer system for unknown questions
                if answer == "":
                    answer, was_user_input = robust_answer_unknown_question(
                        label_org, 
                        options=None, 
                        question_type="text",
                        job_description=job_description
                    )
                    if not answer:
                        answer = years_of_experience  # Ultimate fallback
                        randomly_answered_questions.add((label_org, "text"))
                
                text.clear()
                text.send_keys(answer)
                if do_actions:
                    sleep(1)  # Reduced from 2 seconds
                    actions.send_keys(Keys.ARROW_DOWN)
                    actions.send_keys(Keys.ENTER).perform()
            questions_list.add((label, text.get_attribute("value"), "text", prev_answer))
            continue

        # Check if it's a textarea question
        text_area = try_xp(Question, ".//textarea", False)
        if text_area:
            label = try_xp(Question, ".//label[@for]", False)
            label_org = label.text if label else "Unknown"
            label = label_org.lower()
            answer = ""
            prev_answer = text_area.get_attribute("value")
            if not prev_answer or overwrite_previous_answers:
                if 'summary' in label: answer = linkedin_summary
                elif 'cover' in label: answer = cover_letter
                
                # Use robust answer system for unknown textarea questions
                if answer == "":
                    answer, was_user_input = robust_answer_unknown_question(
                        label_org,
                        options=None,
                        question_type="textarea",
                        job_description=job_description
                    )
                    if not answer:
                        randomly_answered_questions.add((label_org, "textarea"))
                        
            text_area.clear()
            text_area.send_keys(answer)
            if do_actions:
                    sleep(1)  # Reduced from 2 seconds
                    actions.send_keys(Keys.ARROW_DOWN)
                    actions.send_keys(Keys.ENTER).perform()
            questions_list.add((label, text_area.get_attribute("value"), "textarea", prev_answer))
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



def follow_company(modal: WebDriver = None) -> None:
    '''
    Function to follow or un-follow easy applied companies based om `follow_companies`
    '''
    global driver
    if modal is None:
        modal = driver
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
        with open(failed_file_name, 'a', newline='', encoding='utf-8') as file:
            fieldnames = ['Job ID', 'Job Link', 'Resume Tried', 'Date listed', 'Date Tried', 'Assumed Reason', 'Stack Trace', 'External Job link', 'Screenshot Name']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if file.tell() == 0: writer.writeheader()
            writer.writerow({'Job ID':truncate_for_csv(job_id), 'Job Link':truncate_for_csv(job_link), 'Resume Tried':truncate_for_csv(resume), 'Date listed':truncate_for_csv(date_listed), 'Date Tried':datetime.now(), 'Assumed Reason':truncate_for_csv(error), 'Stack Trace':truncate_for_csv(exception), 'External Job link':truncate_for_csv(application_link), 'Screenshot Name':truncate_for_csv(screenshot_name)})
            file.close()
    except Exception as e:
        print_lg("Failed to update failed jobs list!", e)
        pyautogui.alert("Failed to update the excel of failed jobs!\nProbably because of 1 of the following reasons:\n1. The file is currently open or in use by another program\n2. Permission denied to write to the file\n3. Failed to find the file", "Failed Logging")


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
        with open(file_name, mode='a', newline='', encoding='utf-8') as csv_file:
            fieldnames = ['Job ID', 'Title', 'Company', 'Work Location', 'Work Style', 'About Job', 'Experience required', 'Skills required', 'HR Name', 'HR Link', 'Resume', 'Re-posted', 'Date Posted', 'Date Applied', 'Job Link', 'External Job link', 'Questions Found', 'Connect Request']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            if csv_file.tell() == 0: writer.writeheader()
            writer.writerow({'Job ID':truncate_for_csv(job_id), 'Title':truncate_for_csv(title), 'Company':truncate_for_csv(company), 'Work Location':truncate_for_csv(work_location), 'Work Style':truncate_for_csv(work_style), 
                            'About Job':truncate_for_csv(description), 'Experience required': truncate_for_csv(experience_required), 'Skills required':truncate_for_csv(skills), 
                                'HR Name':truncate_for_csv(hr_name), 'HR Link':truncate_for_csv(hr_link), 'Resume':truncate_for_csv(resume), 'Re-posted':truncate_for_csv(reposted), 
                                'Date Posted':truncate_for_csv(date_listed), 'Date Applied':truncate_for_csv(date_applied), 'Job Link':truncate_for_csv(job_link), 
                                'External Job link':truncate_for_csv(application_link), 'Questions Found':truncate_for_csv(questions_list), 'Connect Request':truncate_for_csv(connect_request)})
        csv_file.close()
    except Exception as e:
        print_lg("Failed to update submitted jobs list!", e)
        pyautogui.alert("Failed to update the excel of applied jobs!\nProbably because of 1 of the following reasons:\n1. The file is currently open or in use by another program\n2. Permission denied to write to the file\n3. Failed to find the file", "Failed Logging")



# Function to discard the job application
def discard_job() -> None:
    actions.send_keys(Keys.ESCAPE).perform()
    wait_span_click(driver, 'Discard', 2)






# Function to apply to jobs
def apply_to_jobs(search_terms: list[str]) -> None:
    applied_jobs = get_applied_job_ids()
    rejected_jobs = set()
    blacklisted_companies = set()
    global current_city, failed_count, skip_count, easy_applied_count, external_jobs_count, tabs_count, pause_before_submit, pause_at_failed_question, useNewResume
    current_city = current_city.strip()

    if randomize_search_order:  shuffle(search_terms)
    for searchTerm in search_terms:
        driver.get(f"https://www.linkedin.com/jobs/search/?keywords={searchTerm}")
        # Wait for page to fully load before interacting
        human_delay(1.0, 2.0)
        print_lg("\n________________________________________________________________________________________________________________________\n")
        print_lg(f'\n>>>> Now searching for "{searchTerm}" <<<<\n\n')

        apply_filters()

        # Resume tailoring confirmation after filters
        tailor_resume_for_search = resume_tailoring_enabled
        if resume_tailoring_enabled and resume_tailoring_confirm_after_filters:
            decision = pyautogui.confirm(
                "Resume tailoring is enabled. Do you want to tailor resume and apply for this search?",
                "Resume Tailoring",
                ["Tailor resume and apply", "Apply without tailoring"],
            )
            tailor_resume_for_search = decision == "Tailor resume and apply"
        if tailor_resume_for_search:
            global master_resume_path
            if not master_resume_path or not os.path.exists(master_resume_path):
                new_path = pyautogui.prompt(
                    "Please enter the full path to your master resume (docx/pdf).",
                    "Master Resume Required",
                    default=master_resume_path or "",
                )
                if new_path and os.path.exists(new_path):
                    try:
                        base_dir = os.path.abspath(master_resume_folder)
                        candidate = os.path.abspath(new_path)
                        if candidate.startswith(base_dir):
                            master_resume_path = new_path
                        else:
                            print_lg("Master resume must be inside the master resume folder. Tailoring disabled for this search.")
                            tailor_resume_for_search = False
                    except Exception:
                        master_resume_path = new_path
                else:
                    print_lg("Master resume not found. Tailoring disabled for this search.")
                    tailor_resume_for_search = False

        current_count = 0
        try:
            while current_count < switch_number:
                # Check for stop request at each page
                if is_stop_requested():
                    print_lg("Stop requested - exiting job search loop...")
                    return
                # Wait until job listings are loaded
                wait.until(EC.presence_of_all_elements_located((By.XPATH, "//li[@data-occludable-job-id]")))

                pagination_element, current_page = get_page_info()

                # Find all job listings in current page
                buffer(3)
                job_listings = driver.find_elements(By.XPATH, "//li[@data-occludable-job-id]")  

            
                for job in job_listings:
                    # Check for stop request at each job
                    if is_stop_requested():
                        print_lg("🛑 Stop requested - exiting...")
                        return
                    import time
                    if keep_screen_awake: pyautogui.press('shiftright')
                    if current_count >= switch_number: break
                    print_lg("\n" + "═"*50)

                    job_start_time = time.perf_counter()

                    job_id,title,company,work_location,work_style,skip = get_job_main_details(job, blacklisted_companies, rejected_jobs)
                    
                    if skip: continue
                    # Redundant fail safe check for applied jobs!
                    try:
                        if job_id in applied_jobs or find_by_class(driver, "jobs-s-apply__application-link", 2):
                            print_lg(f'⏭️ SKIP: Already applied to {company}')
                            continue
                    except Exception:
                        print_lg(f'🎯 NEW JOB FOUND')
                        print_lg(f'   └─ {title[:45]}{"..." if len(title)>45 else ""}')
                        print_lg(f'   └─ {company} | {work_location}')

                    job_link = "https://www.linkedin.com/jobs/view/"+job_id
                    application_link = "Easy Applied"
                    date_applied = "Pending"
                    hr_link = "Unknown"
                    hr_name = "Unknown"
                    connect_request = "In Development" # Still in development
                    date_listed = "Unknown"
                    skills = "Needs an AI" # Still in development
                    resume = "Pending"
                    resume_to_upload = default_resume_path
                    force_resume_upload = False
                    reposted = False
                    questions_list = None
                    screenshot_name = "Not Available"

                    try:
                        rejected_jobs, blacklisted_companies, jobs_top_card = check_blacklist(rejected_jobs,job_id,company,blacklisted_companies)
                    except ValueError as e:
                        print_lg(e, 'Skipping this job!\n')
                        failed_job(job_id, job_link, resume, date_listed, "Found Blacklisted words in About Company", e, "Skipped", screenshot_name)
                        skip_count += 1
                        continue
                    except Exception:
                        print_lg("Failed to scroll to About Company!")
                        # print_lg(e)



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
                    except Exception:
                        print_lg(f'HR info was not given for "{title}" with Job ID: {job_id}!')
                        # print_lg(e)


                    # Calculation of date posted
                    try:
                        # try: time_posted_text = find_by_class(driver, "jobs-unified-top-card__posted-date", 2).text
                        # except: 
                        time_posted_text = jobs_top_card.find_element(By.XPATH, './/span[contains(normalize-space(), " ago")]').text
                        print("Time Posted: " + time_posted_text)
                        if time_posted_text.__contains__("Reposted"):
                            reposted = True
                            time_posted_text = time_posted_text.replace("Reposted", "")
                        date_listed = calculate_date_posted(time_posted_text.strip())
                    except Exception as e:
                        print_lg("Failed to calculate the date posted!",e)


                    description, experience_required, skip, reason, message = get_job_description()
                    if skip:
                        print_lg(message)
                        failed_job(job_id, job_link, resume, date_listed, reason, message, "Skipped", screenshot_name)
                        rejected_jobs.add(job_id)
                        skip_count += 1
                        continue

                    # Reset per-job progress indicators
                    try:
                        from modules.dashboard import metrics as _dash_metrics
                        _dash_metrics.set_metric('jd_progress', 0)
                        _dash_metrics.set_metric('resume_progress', 0)
                    except Exception:
                        pass

                    
                    if use_AI and description != "Unknown":
                        # Optional resume tailoring prompt before JD analysis
                        tailoring_instruction = None
                        if resume_tailoring_enabled and resume_tailoring_prompt_before_jd and tailor_resume_for_search:
                            tailoring_instruction = pyautogui.prompt(
                                "Enter optional tailoring instructions for this job (leave blank to use defaults):",
                                "Resume Tailoring Prompt",
                                default="",
                            )

                        if resume_tailoring_enabled and tailor_resume_for_search:
                            # Ask user if they want to tailor resume for this job
                            tailor_choice = pyautogui.confirm(
                                f"🎯 New Job Found:\n{title[:50]}...\n\nCompany: {company}\n\nWould you like to tailor your resume for this job?",
                                "Resume Tailoring",
                                ["Tailor Resume", "Skip & Continue", "Skip All"]
                            )
                            
                            if tailor_choice == "Skip All":
                                # Disable tailoring for this session
                                tailor_resume_for_search = False
                                print_lg("⏭️ Resume tailoring disabled for this session")
                            elif tailor_choice == "Skip & Continue":
                                print_lg("⏭️ Skipping resume tailoring for this job")
                            elif tailor_choice == "Tailor Resume":
                              try:
                                import time
                                from modules.dashboard import metrics as _dash_metrics
                                
                                # Step 1: Initialize (10%)
                                _dash_metrics.set_metric('resume_progress', 10)
                                print_lg(f"📝 RESUME TAILORING STARTED")
                                print_lg(f"   └─ Job: {title[:50]}{'...' if len(title)>50 else ''}")
                                print_lg(f"   └─ Company: {company}")
                                print_lg(f"   └─ Using: {ai_provider.upper()} AI")
                                
                                # Step 2: Reading resume (20%)
                                _dash_metrics.set_metric('resume_progress', 20)
                                print_lg(f"   └─ Reading master resume...")
                                
                                t_start = time.perf_counter()
                                
                                # Step 3: Sending to AI (40%)
                                _dash_metrics.set_metric('resume_progress', 40)
                                print_lg(f"   └─ Analyzing with AI...")
                                
                                tailored_paths = tailor_resume_to_files(
                                    resume_text=None,
                                    job_description=description,
                                    instructions=tailoring_instruction,
                                    provider=ai_provider,
                                    client=aiClient,
                                    resume_path=master_resume_path,
                                    job_title=title,
                                    candidate_name=first_name,
                                    enable_preview=True,
                                )
                                
                                # Step 4: Files created (80%)
                                _dash_metrics.set_metric('resume_progress', 80)
                                print_lg(f"   └─ Generating files...")
                                
                                t_duration = time.perf_counter() - t_start
                                
                                # Step 5: Complete (100%)
                                _dash_metrics.set_metric('resume_progress', 100)
                                _dash_metrics.append_sample('resume_tailoring', t_duration)
                                _dash_metrics.set_metric('resume_last', t_duration)
                                
                                resume_to_upload = tailored_paths.get("pdf") or tailored_paths.get("docx") or default_resume_path
                                resume = os.path.basename(resume_to_upload)
                                force_resume_upload = True
                                
                                print_lg(f"✅ RESUME TAILORED ({t_duration:.1f}s)")
                                print_lg(f"   └─ File: {resume}")
                                if tailored_paths.get('diff'):
                                    print_lg(f"   └─ Changes report generated")

                                # Show preview dialog
                                preview_choice = pyautogui.confirm(
                                    f"✅ Resume tailored for:\n{title[:40]}...\n\n"
                                    f"📄 {resume}\n"
                                    f"⏱️ {t_duration:.1f}s\n\n"
                                    f"Preview before applying?",
                                    "✨ Resume Ready",
                                    ["Preview", "Continue"],
                                )
                                if preview_choice == "Preview":
                                    print_lg("📖 Opening preview GUI...")
                                    open_preview(
                                        tailored_paths, 
                                        tailored_paths.get("diff"),
                                        master_text=tailored_paths.get("master_text", ""),
                                        tailored_text=tailored_paths.get("tailored_text", ""),
                                        jd_text=tailored_paths.get("jd_text", ""),
                                        job_title=tailored_paths.get("job_title", job_title or "Job")
                                    )
                                    # User can view PDF/DOCX from GUI buttons, then close and continue
                                    continue_choice = pyautogui.confirm(
                                        "Ready to continue with application?\n\n(Use the Preview window buttons to open PDF/DOCX if needed)",
                                        "Continue?",
                                        ["Apply Now", "Cancel"]
                                    )
                                    if continue_choice == "Cancel":
                                        print_lg("❌ Cancelled by user")
                                        raise Exception("Application cancelled after preview")
                              except Exception as e:
                                _dash_metrics.set_metric('resume_progress', 0)
                                print_lg(f"❌ RESUME TAILORING FAILED: {str(e)[:100]}")
                        ##> ------ Yang Li : MARKYangL - Feature ------
                        try:
                            import time
                            from modules.dashboard import metrics as _dash_metrics
                            
                            # Step 1: Initialize (10%)
                            _dash_metrics.set_metric('jd_progress', 10)
                            print_lg(f"📋 JD ANALYSIS STARTED")
                            print_lg(f"   └─ Using: {ai_provider.upper()} AI")
                            
                            ai_start = time.perf_counter()
                            
                            # Step 2: Sending to AI (30%)
                            _dash_metrics.set_metric('jd_progress', 30)
                            
                            if ai_provider.lower() == "openai":
                                _dash_metrics.set_metric('jd_progress', 50)
                                skills = ai_extract_skills(aiClient, description)
                            elif ai_provider.lower() == "deepseek":
                                _dash_metrics.set_metric('jd_progress', 50)
                                skills = deepseek_extract_skills(aiClient, description)
                            elif ai_provider.lower() == "gemini":
                                _dash_metrics.set_metric('jd_progress', 50)
                                skills = gemini_extract_skills(aiClient, description)
                            elif ai_provider.lower() == "ollama":
                                # Use local Ollama wrapper; prefer streaming if available
                                try:
                                    from modules.ai import ollama_integration as _oll
                                    _dash_metrics.set_metric('jd_progress', 40)
                                    res = _oll.generate(description, timeout=120, stream=True)
                                    if isinstance(res, str):
                                        skills = res
                                        _dash_metrics.set_metric('jd_progress', 80)
                                    else:
                                        # res is an iterator - track streaming progress
                                        out = []
                                        chunk_count = 0
                                        for chunk in res:
                                            text = str(chunk).strip()
                                            out.append(text)
                                            chunk_count += 1
                                            # Update progress incrementally (40-80%)
                                            progress = min(40 + (chunk_count * 2), 80)
                                            _dash_metrics.set_metric('jd_progress', progress)
                                        skills = ' '.join(out)
                                except Exception as e:
                                    skills = f"[Ollama Error] {e}"
                            else:
                                skills = "In Development"
                            
                            duration = time.perf_counter() - ai_start
                            
                            # Step 3: Complete (100%)
                            _dash_metrics.set_metric('jd_progress', 100)
                            _dash_metrics.append_sample('jd_analysis', duration)
                            _dash_metrics.append_sample('jd_analysis_time', duration)
                            _dash_metrics.inc('jd_analysis_count')
                            
                            print_lg(f"✅ JD ANALYZED ({duration:.1f}s)")
                            print_lg(f"   └─ Skills extracted successfully")
                        except Exception as e:
                            _dash_metrics.set_metric('jd_progress', 0)
                            print_lg(f"❌ JD ANALYSIS FAILED: {str(e)[:80]}")
                            skills = "Error extracting skills"
                        ##<

                    uploaded = False
                    # Case 1: Easy Apply Button
                    # Add delay before clicking Easy Apply to be more human-like
                    human_delay(0.5, 1.2)
                    if try_xp(driver, ".//button[contains(@class,'jobs-apply-button') and contains(@class, 'artdeco-button--3') and contains(@aria-label, 'Easy')]"):
                        try: 
                            try:
                                errored = ""
                                # Wait for modal to fully load
                                human_delay(0.8, 1.5)
                                modal = find_by_class(driver, "jobs-easy-apply-modal")
                                human_delay(0.3, 0.6)
                                wait_span_click(driver, "Next", 1)
                                # if description != "Unknown":
                                #     resume = create_custom_resume(description)
                                resume = "Previous resume"
                                next_button = True
                                questions_list = set()
                                next_counter = 0
                                max_iterations = 20  # Increased from 15 to give more attempts
                                while next_button:
                                    # Small delay between loop iterations
                                    human_delay(0.3, 0.8)
                                    # Check for and dismiss any popups at start of each iteration
                                    dismiss_deloitte_popup()
                                    # Re-fetch modal to avoid stale element references
                                    try:
                                        modal = find_by_class(driver, "jobs-easy-apply-modal")
                                    except Exception:
                                        print_lg("Could not re-fetch modal, continuing with existing reference")
                                    next_counter += 1
                                    if next_counter >= max_iterations: 
                                        if pause_at_failed_question:
                                            screenshot(driver, job_id, "Needed manual intervention for failed question")
                                            pyautogui.alert("Couldn't answer one or more questions.\nPlease click \"Continue\" once done.\nDO NOT CLICK Back, Next or Review button in LinkedIn.\n\n\n\n\nYou can turn off \"Pause at failed question\" setting in config.py", "Help Needed", "Continue")
                                            next_counter = 1
                                            continue
                                        if questions_list: print_lg("Stuck for one or some of the following questions...", questions_list)
                                        screenshot_name = screenshot(driver, job_id, "Failed at questions")
                                        errored = "stuck"
                                        raise Exception("Seems like stuck in a continuous loop of next, probably because of new questions.")
                                    questions_list = answer_questions(modal, questions_list, work_location, job_description=description)
                                    if (force_resume_upload or useNewResume) and not uploaded:
                                        uploaded, resume = upload_resume(modal, resume_to_upload)
                                        # Dismiss any popups that may appear after upload (e.g., Deloitte)
                                        dismiss_deloitte_popup()
                                                                
                                    # Check if we've reached the review stage
                                    try: 
                                        next_button = modal.find_element(By.XPATH, './/span[normalize-space(.)="Review"]')
                                        # If we find the Review button, break the loop as we're at the final step
                                        break
                                    except NoSuchElementException:  
                                        try:
                                            # Look for Next or Continue button
                                            next_button = modal.find_element(By.XPATH, './/button[contains(span, "Next")]')
                                            if not next_button.is_enabled():
                                                print_lg("Next button is disabled, breaking loop")
                                                break
                                        except NoSuchElementException:
                                            # If neither Next nor Review buttons are found, try other selectors
                                            try:
                                                next_button = modal.find_element(By.XPATH, './/button[contains(@aria-label, "Continue") or contains(span, "Continue")]')
                                            except NoSuchElementException:
                                                print_lg("Could not find Next/Review/Continue button, breaking loop")
                                                break
                                                                
                                    try: 
                                        # Add human-like delay before clicking
                                        human_delay(0.4, 1.0)
                                        next_button.click()
                                        buffer(click_gap)
                                        # Dismiss any popup that may appear after clicking Next
                                        dismiss_deloitte_popup()
                                    except ElementClickInterceptedException: 
                                        print_lg("Element click intercepted, trying to dismiss popup...")
                                        dismiss_deloitte_popup()
                                        human_delay(0.3, 0.5)
                                        # Retry the click after dismissing popup
                                        try:
                                            next_button.click()
                                            buffer(click_gap)
                                        except Exception:
                                            print_lg("Still can't click, breaking loop")
                                            break
                                    except Exception as e:
                                        print_lg(f"Error clicking next button: {e}")
                                        break
                                    # Add extra delay after clicking for page to load
                                    human_delay(0.5, 1.2)
                                    buffer(click_gap)

                            except NoSuchElementException: errored = "nose"
                            finally:
                                if questions_list and errored != "stuck": 
                                    print_lg("Answered the following questions...", questions_list)
                                    print("\n\n" + "\n".join(str(question) for question in questions_list) + "\n\n")
                                # Add delay before clicking Review
                                human_delay(0.5, 1.0)
                                wait_span_click(driver, "Review", 1, scrollTop=True)
                                human_delay(0.8, 1.2)
                                cur_pause_before_submit = pause_before_submit
                                if errored != "stuck" and cur_pause_before_submit:
                                    decision = pyautogui.confirm('1. Please verify your information.\n2. If you edited something, please return to this final screen.\n3. DO NOT CLICK "Submit Application".\n\n\n\n\nYou can turn off "Pause before submit" setting in config.py\nTo TEMPORARILY disable pausing, click "Disable Pause"', "Confirm your information",["Disable Pause", "Discard Application", "Submit Application"])
                                    if decision == "Discard Application": raise Exception("Job application discarded by user!")
                                    pause_before_submit = False if "Disable Pause" == decision else True
                                    # try_xp(modal, ".//span[normalize-space(.)='Review']")
                                follow_company(modal)
                                # Add delay before submitting - important for appearing human
                                human_delay(0.8, 1.5)
                                if wait_span_click(driver, "Submit application", 2, scrollTop=True): 
                                    date_applied = datetime.now()
                                    # Wait after submission
                                    human_delay(0.8, 1.5)
                                    if not wait_span_click(driver, "Done", 2): actions.send_keys(Keys.ESCAPE).perform()
                                elif errored != "stuck" and cur_pause_before_submit and "Yes" in pyautogui.confirm("You submitted the application, didn't you 😒?", "Failed to find Submit Application!", ["Yes", "No"]):
                                    date_applied = datetime.now()
                                    wait_span_click(driver, "Done", 2)
                                else:
                                    print_lg("Since, Submit Application failed, discarding the job application...")
                                    # if screenshot_name == "Not Available":  screenshot_name = screenshot(driver, job_id, "Failed to click Submit application")
                                    # else:   screenshot_name = [screenshot_name, screenshot(driver, job_id, "Failed to click Submit application")]
                                    if errored == "nose": raise Exception("Failed to click Submit application 😑")


                        except Exception as e:
                            print_lg("❌ APPLICATION FAILED")
                            print_lg(f"   └─ Reason: {str(e)[:60]}")
                            critical_error_log("Somewhere in Easy Apply process",e)
                            failed_job(job_id, job_link, resume, date_listed, "Problem in Easy Applying", e, application_link, screenshot_name)
                            failed_count += 1
                            discard_job()
                            continue
                    else:
                        # Case 2: Apply externally
                        skip, application_link, tabs_count = external_apply(pagination_element, job_id, job_link, resume, date_listed, application_link, screenshot_name)
                        if dailyEasyApplyLimitReached:
                            print_lg("\n⚠️ DAILY LIMIT REACHED - Easy Apply limit hit!\n")
                            return
                        if skip: continue

                    submitted_jobs(job_id, title, company, work_location, work_style, description, experience_required, skills, hr_name, hr_link, resume, reposted, date_listed, date_applied, job_link, application_link, questions_list, connect_request)
                    if uploaded and not force_resume_upload:
                        useNewResume = False

                    print_lg(f'✅ APPLICATION SENT!')
                    print_lg(f'   └─ {title[:40]}{"..." if len(title)>40 else ""} at {company}')
                    current_count += 1
                    if application_link == "Easy Applied":
                        easy_applied_count += 1
                        print_lg(f'   └─ Type: Easy Apply')
                        try:
                            from modules.dashboard import metrics as _dash_metrics
                            _dash_metrics.inc('easy_applied')
                        except Exception:
                            pass
                    else:
                        external_jobs_count += 1
                        print_lg(f'   └─ Type: External Application')
                        try:
                            from modules.dashboard import metrics as _dash_metrics
                            _dash_metrics.inc('external_jobs')
                        except Exception:
                            pass
                    applied_jobs.add(job_id)

                    # Job timing & ETA updates for dashboard metrics
                    try:
                        import time
                        from modules.dashboard import metrics as _dash_metrics
                        duration = time.perf_counter() - job_start_time
                        _dash_metrics.append_sample('job_time', duration)
                        _dash_metrics.inc('jobs_processed')
                        jobs_done = _dash_metrics.get_metrics().get('jobs_processed', 0)
                        eta = _dash_metrics.get_eta(jobs_done, max_jobs_to_process)
                        _dash_metrics.set_metric('eta_seconds', eta if eta is not None else 0)
                        if max_jobs_to_process and max_jobs_to_process > 0:
                            percent = int(100 * jobs_done / max_jobs_to_process)
                            _dash_metrics.set_metric('overall_progress', percent)
                    except Exception:
                        pass



                # Switching to next page
                if pagination_element == None:
                    print_lg("Couldn't find pagination element, probably at the end page of results!")
                    break
                try:
                    pagination_element.find_element(By.XPATH, f"//button[@aria-label='Page {current_page+1}']").click()
                    print_lg(f"\n>-> Now on Page {current_page+1} \n")
                    # Wait for new page to fully load
                    human_delay(1.5, 2.5)
                except NoSuchElementException:
                    print_lg(f"\n>-> Didn't find Page {current_page+1}. Probably at the end page of results!\n")
                    break

        except (NoSuchWindowException, WebDriverException) as e:
            print_lg("Browser window closed or session is invalid. Ending application process.", e)
            raise e # Re-raise to be caught by main
        except Exception as e:
            print_lg("Failed to find Job listings!")
            critical_error_log("In Applier", e)
            try:
                print_lg(driver.page_source, pretty=True)
            except Exception as page_source_error:
                print_lg(f"Failed to get page source, browser might have crashed. {page_source_error}")
            # print_lg(e)

        
def run(total_runs: int) -> int:
    if dailyEasyApplyLimitReached:
        return total_runs
    # Check if stop was requested
    if is_stop_requested():
        print_lg("Stop requested - skipping run cycle...")
        return total_runs
    print_lg("\n########################################################################################################################\n")
    print_lg(f"Date and Time: {datetime.now()}")
    print_lg(f"Cycle number: {total_runs}")
    print_lg(f"Currently looking for jobs posted within '{date_posted}' and sorting them by '{sort_by}'")
    apply_to_jobs(search_terms)
    print_lg("########################################################################################################################\n")
    if not dailyEasyApplyLimitReached and not is_stop_requested():
        print_lg("Sleeping for 10 min...")
        # Sleep in smaller increments so we can check for stop requests
        for _ in range(60):  # 60 * 5 seconds = 5 minutes
            if is_stop_requested():
                print_lg("Stop requested during sleep - exiting...")
                return total_runs + 1
            sleep(5)
        print_lg("Few more min... Gonna start with in next 5 min...")
        for _ in range(60):  # 60 * 5 seconds = 5 minutes
            if is_stop_requested():
                print_lg("Stop requested during sleep - exiting...")
                return total_runs + 1
            sleep(5)
    buffer(3)
    return total_runs + 1



chatGPT_tab = False
linkedIn_tab = False

# Global driver references (will be set when Chrome starts)
driver = None
wait = None
actions = None

def main() -> None:
    global driver, wait, actions
    try:
        global linkedIn_tab, tabs_count, useNewResume, aiClient
        alert_title = "Error Occurred. Closing Browser!"
        total_runs = 1        
        validate_config()
        
        # Start Chrome browser
        print_lg("Initializing automation...")
        driver, wait, actions = start_chrome()
        
        if not os.path.exists(default_resume_path):
            pyautogui.alert(text=('Your default resume "{}" is missing! Please update it\'s folder path "default_resume_path" in config.py' + 
                                '\n\nOR\n\n' + 
                                'Add a resume with exact name and path (check for spelling mistakes including cases).' + 
                                '\n\n\n' + 
                                'For now the bot will continue using your previous upload from LinkedIn!').format(default_resume_path), title="Missing Resume", button="OK")
            useNewResume = False
        
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
            ##<

            try:
                about_company_for_ai = " ".join([word for word in (first_name+" "+last_name).split() if len(word) > 3])
                print_lg(f"Extracted about company info for AI: '{about_company_for_ai}'")
            except Exception as e:
                print_lg("Failed to extract about company info!", e)
        
        # Start applying to jobs
        driver.switch_to.window(linkedIn_tab)
        total_runs = run(total_runs)
        while(run_non_stop and not is_stop_requested()):
            # Check for stop request at each iteration
            if is_stop_requested():
                print_lg("Stop requested - exiting main loop...")
                break
            if cycle_date_posted:
                date_options = ["Any time", "Past month", "Past week", "Past 24 hours"]
                global date_posted
                date_posted = date_options[date_options.index(date_posted)+1 if date_options.index(date_posted)+1 > len(date_options) else -1] if stop_date_cycle_at_24hr else date_options[0 if date_options.index(date_posted)+1 >= len(date_options) else date_options.index(date_posted)+1]
            if alternate_sortby:
                global sort_by
                sort_by = "Most recent" if sort_by == "Most relevant" else "Most relevant"
                if not is_stop_requested():
                    total_runs = run(total_runs)
                sort_by = "Most recent" if sort_by == "Most relevant" else "Most relevant"
            if not is_stop_requested():
                total_runs = run(total_runs)
            if dailyEasyApplyLimitReached:
                break
        

    except (NoSuchWindowException, WebDriverException) as e:
        print_lg("Browser window closed or session is invalid. Exiting.", e)
    except Exception as e:
        critical_error_log("In Applier Main", e)
        pyautogui.alert(e,alert_title)
    finally:
        print_lg("\n\nTotal runs:                     {}".format(total_runs))
        print_lg("Jobs Easy Applied:              {}".format(easy_applied_count))
        print_lg("External job links collected:   {}".format(external_jobs_count))
        print_lg("                              ----------")
        print_lg("Total applied or collected:     {}".format(easy_applied_count + external_jobs_count))
        print_lg("\nFailed jobs:                    {}".format(failed_count))
        print_lg("Irrelevant jobs skipped:        {}\n".format(skip_count))
        if randomly_answered_questions: print_lg("\n\nQuestions randomly answered:\n  {}  \n\n".format(";\n".join(str(question) for question in randomly_answered_questions)))
        quote = choice([
            "You're one step closer than before.", 
            "All the best with your future interviews.", 
            "Keep up with the progress. You got this.", 
            "If you're tired, learn to take rest but never give up.",
            "Success is not final, failure is not fatal: It is the courage to continue that counts. - Winston Churchill",
            "Believe in yourself and all that you are. Know that there is something inside you that is greater than any obstacle. - Christian D. Larson",
            "Every job is a self-portrait of the person who does it. Autograph your work with excellence.",
            "The only way to do great work is to love what you do. If you haven't found it yet, keep looking. Don't settle. - Steve Jobs",
            "Opportunities don't happen, you create them. - Chris Grosser",
            "The road to success and the road to failure are almost exactly the same. The difference is perseverance.",
            "Obstacles are those frightful things you see when you take your eyes off your goal. - Henry Ford",
            "The only limit to our realization of tomorrow will be our doubts of today. - Franklin D. Roosevelt"
            ])
        msg = f"\n{quote}\n\n\nBest regards,\nSuraj Panwar\nhttps://www.linkedin.com/in/surajpanwar26/\n\n"
        pyautogui.alert(msg, "Exiting..")
        print_lg(msg,"Closing the browser...")
        if tabs_count >= 10:
            msg = "NOTE: IF YOU HAVE MORE THAN 10 TABS OPENED, PLEASE CLOSE OR BOOKMARK THEM!\n\nOr it's highly likely that application will just open browser and not do anything next time!" 
            pyautogui.alert(msg,"Info")
            print_lg("\n"+msg)
        ##> ------ Yang Li : MARKYangL - Feature ------
        if use_AI and aiClient:
            try:
                if ai_provider.lower() == "openai":
                    ai_close_openai_client(aiClient)
                elif ai_provider.lower() == "deepseek":
                    deepseek_close_client(aiClient)
                elif ai_provider.lower() == "gemini":
                    pass # Gemini client does not need to be closed
                print_lg(f"Closed {ai_provider} AI client.")
            except Exception as e:
                print_lg("Failed to close AI client:", e)
        ##<
        # Close Chrome browser properly
        try:
            close_driver()
        except Exception as e: 
            critical_error_log("When closing browser...", e)


if __name__ == "__main__":
    main()
