'''
PILOT MODE - LinkedIn Job Application Testing Script
=====================================================
Purpose: Test form filling and tailored resume functionality in a controlled environment
Features:
- Uses persistent Chrome session (no login/logout after each test)
- Directly navigates to job search URL with "software engineer" 
- Bypasses popups for streamlined testing
- Tests full application flow: form filling + tailored resume upload
- Allows selecting new jobs after completing applications

Author: Suraj Panwar
'''

import os
import sys
import time
from datetime import datetime
from random import randint
import pyautogui

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.select import Select
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    NoSuchElementException, 
    ElementClickInterceptedException, 
    StaleElementReferenceException,
    TimeoutException
)

# Import configuration
from config.personals import *
from config.questions import *
from config.search import *
from config.secrets import use_AI, username, password, ai_provider
from config.settings import *

# Import modules
from modules.open_chrome import start_chrome, close_driver
from modules.helpers import *
from modules.clickers_and_finders import *

# Import AI modules if enabled
if use_AI:
    try:
        from modules.ai.openaiConnections import ai_create_openai_client, ai_extract_skills, ai_answer_question
    except ImportError:
        pass
    try:
        from modules.ai.deepseekConnections import deepseek_create_client, deepseek_extract_skills, deepseek_answer_question
    except ImportError:
        pass
    try:
        from modules.ai.geminiConnections import gemini_create_client, gemini_extract_skills, gemini_answer_question
    except ImportError:
        pass
    try:
        from modules.ai.resume_tailoring import tailor_resume_to_files, open_preview
    except ImportError:
        pass

# ============ PILOT MODE CONFIGURATION ============
PILOT_CONFIG = {
    "search_keyword": "software engineer",
    "location": search_location if search_location else "United States",
    "max_jobs_to_test": 3,  # Number of jobs to test per run
    "pause_between_jobs": True,  # Pause after each job for inspection
    "test_resume_upload": True,  # Test resume upload functionality
    "test_form_filling": True,  # Test form filling functionality
    "skip_submit": True,  # Skip actual submission (review only)
    "verbose_logging": True,  # Detailed logging
    "login_wait_time": 120,  # Seconds to wait for manual login
}

# Global variables
driver = None
wait = None
actions = None
aiClient = None
linkedIn_tab = None
jobs_tested = 0
successful_tests = 0
failed_tests = 0


def pilot_log(message: str, level: str = "INFO"):
    """Enhanced logging for pilot mode"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix = {
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "DEBUG": "🔍",
        "TEST": "🧪",
    }.get(level, "📌")
    print(f"[{timestamp}] {prefix} {message}")


def is_logged_in_LN() -> bool:
    """Check if user is logged in to LinkedIn"""
    global driver
    try:
        if driver.current_url == "https://www.linkedin.com/feed/":
            return True
        if "feed" in driver.current_url:
            return True
        if try_linkText(driver, "Sign in"):
            return False
        if try_xp(driver, '//button[@type="submit" and contains(text(), "Sign in")]'):
            return False
        if try_linkText(driver, "Join now"):
            return False
        # If no sign-in indicators found, probably logged in
        return True
    except:
        return False


def login_LN() -> bool:
    """Login to LinkedIn with user credentials"""
    global driver, wait
    
    driver.get("https://www.linkedin.com/login")
    time.sleep(2)
    
    try:
        # Wait for login page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.LINK_TEXT, "Forgot password?"))
        )
        
        # Fill username
        try:
            text_input_by_ID(driver, "username", username, 1)
        except Exception:
            pilot_log("Couldn't find username field", "WARNING")
        
        # Fill password
        try:
            text_input_by_ID(driver, "password", password, 1)
        except Exception:
            pilot_log("Couldn't find password field", "WARNING")
        
        # Click sign in
        try:
            login_button = driver.find_element(By.XPATH, '//button[@type="submit" and contains(text(), "Sign in")]')
            login_button.click()
            time.sleep(3)
        except Exception:
            pilot_log("Couldn't click sign in button", "WARNING")
        
        # Wait for redirect to feed
        try:
            WebDriverWait(driver, 15).until(EC.url_contains("feed"))
            pilot_log("Login successful!", "SUCCESS")
            return True
        except TimeoutException:
            # Check if already on feed
            if "feed" in driver.current_url:
                pilot_log("Login successful!", "SUCCESS")
                return True
            return False
            
    except Exception as e:
        pilot_log(f"Login error: {e}", "ERROR")
        return False


def dismiss_all_popups():
    """Aggressively dismiss any popups that may appear"""
    global driver
    
    popup_selectors = [
        # LinkedIn modals
        "//button[@aria-label='Dismiss']",
        "//button[@aria-label='Close']",
        "//button[contains(@class, 'artdeco-modal__dismiss')]",
        "//button[normalize-space()='OK']",
        "//button[normalize-space()='Got it']",
        "//button[normalize-space()='Continue']",
        "//button[normalize-space()='Done']",
        "//button[normalize-space()='Not now']",
        "//button[normalize-space()='Skip']",
        # Generic close buttons
        "//div[@role='dialog']//button[contains(@class, 'close')]",
        "//div[contains(@class, 'modal')]//button[contains(@class, 'dismiss')]",
        # Corporate popups (Deloitte, etc.)
        "//button[contains(@class, 'pendo-close')]",
        "//div[contains(@class, 'pendo')]//button",
    ]
    
    dismissed_count = 0
    for selector in popup_selectors:
        try:
            elements = driver.find_elements(By.XPATH, selector)
            for elem in elements:
                if elem.is_displayed() and elem.is_enabled():
                    try:
                        elem.click()
                        dismissed_count += 1
                        time.sleep(0.2)
                    except:
                        try:
                            driver.execute_script("arguments[0].click();", elem)
                            dismissed_count += 1
                            time.sleep(0.2)
                        except:
                            pass
        except:
            pass
    
    # Try keyboard dismiss as fallback
    try:
        from selenium.webdriver.common.action_chains import ActionChains
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        time.sleep(0.1)
    except:
        pass
    
    if dismissed_count > 0:
        pilot_log(f"Dismissed {dismissed_count} popup(s)", "DEBUG")
    
    return dismissed_count


def navigate_to_job_search():
    """Navigate directly to LinkedIn job search with software engineer keyword"""
    global driver, wait
    
    keyword = PILOT_CONFIG["search_keyword"].replace(" ", "%20")
    location = PILOT_CONFIG["location"].replace(" ", "%20")
    
    # Build direct search URL with Easy Apply filter
    search_url = f"https://www.linkedin.com/jobs/search/?keywords={keyword}&location={location}&f_AL=true"
    
    pilot_log(f"Navigating to: {search_url}", "INFO")
    driver.get(search_url)
    
    # Wait for page to load
    time.sleep(3)
    dismiss_all_popups()
    
    # Wait for job listings
    try:
        wait.until(EC.presence_of_element_located((By.XPATH, "//li[@data-occludable-job-id]")))
        pilot_log("Job listings loaded successfully", "SUCCESS")
        return True
    except TimeoutException:
        pilot_log("Failed to load job listings", "ERROR")
        return False


def get_job_listings():
    """Get all job listings from current page"""
    global driver
    
    try:
        listings = driver.find_elements(By.XPATH, "//li[@data-occludable-job-id]")
        pilot_log(f"Found {len(listings)} job listings", "INFO")
        return listings
    except Exception as e:
        pilot_log(f"Error getting job listings: {e}", "ERROR")
        return []


def click_job_and_get_details(job_element):
    """Click on a job and extract its details"""
    global driver, wait
    
    try:
        # Get job ID
        job_id = job_element.get_dom_attribute('data-occludable-job-id')
        
        # Find and click the job link
        job_link = job_element.find_element(By.TAG_NAME, 'a')
        scroll_to_view(driver, job_link, True)
        time.sleep(0.5)
        
        job_link.click()
        time.sleep(1.5)
        
        dismiss_all_popups()
        
        # Extract job details
        title = job_link.text.split('\n')[0] if job_link.text else "Unknown"
        
        try:
            details_elem = job_element.find_element(By.CLASS_NAME, 'artdeco-entity-lockup__subtitle')
            details_text = details_elem.text
            company = details_text.split(' · ')[0] if ' · ' in details_text else details_text
        except:
            company = "Unknown"
        
        # Get job description
        try:
            jd_elem = find_by_class(driver, "jobs-box__html-content", 3)
            job_description = jd_elem.text if jd_elem else "Unknown"
        except:
            job_description = "Unknown"
        
        pilot_log(f"Selected job: {title[:50]}... at {company}", "INFO")
        
        return {
            "id": job_id,
            "title": title,
            "company": company,
            "description": job_description,
            "link": f"https://www.linkedin.com/jobs/view/{job_id}"
        }
        
    except Exception as e:
        pilot_log(f"Error getting job details: {e}", "ERROR")
        return None


def check_if_already_applied():
    """Check if already applied to this job"""
    global driver
    
    try:
        applied_indicator = driver.find_elements(By.CLASS_NAME, "jobs-s-apply__application-link")
        if applied_indicator:
            return True
        
        footer_state = driver.find_elements(By.CLASS_NAME, "job-card-container__footer-job-state")
        for elem in footer_state:
            if elem.text == "Applied":
                return True
        
        return False
    except:
        return False


def click_easy_apply_button():
    """Click the Easy Apply button"""
    global driver, wait
    
    try:
        # Look for Easy Apply button
        easy_apply_btn = wait.until(EC.element_to_be_clickable((
            By.XPATH, 
            ".//button[contains(@class,'jobs-apply-button') and contains(@aria-label, 'Easy')]"
        )))
        
        time.sleep(0.5)
        easy_apply_btn.click()
        time.sleep(1)
        
        dismiss_all_popups()
        pilot_log("Clicked Easy Apply button", "SUCCESS")
        return True
        
    except TimeoutException:
        pilot_log("Easy Apply button not found or not clickable", "WARNING")
        return False
    except Exception as e:
        pilot_log(f"Error clicking Easy Apply: {e}", "ERROR")
        return False


def test_form_filling(modal, job_description: str):
    """Test form filling functionality"""
    global driver, actions
    
    questions_answered = []
    
    try:
        # Find all form elements
        form_elements = modal.find_elements(By.XPATH, ".//div[@data-test-form-element]")
        pilot_log(f"Found {len(form_elements)} form elements", "TEST")
        
        for elem in form_elements:
            try:
                # Check for select dropdowns
                select = try_xp(elem, ".//select", False)
                if select:
                    label_elem = try_xp(elem, ".//label//span", False)
                    label = label_elem.text if label_elem else "Unknown"
                    
                    select_obj = Select(select)
                    current = select_obj.first_selected_option.text
                    
                    if current == "Select an option":
                        # Try to select first valid option
                        options = select_obj.options
                        if len(options) > 1:
                            select_obj.select_by_index(1)
                            new_val = select_obj.first_selected_option.text
                            questions_answered.append(f"SELECT: {label[:30]}... -> {new_val}")
                            pilot_log(f"Filled select: {label[:40]}...", "DEBUG")
                    continue
                
                # Check for text inputs
                text_input = try_xp(elem, ".//input[@type='text']", False)
                if text_input:
                    label_elem = try_xp(elem, ".//label", False)
                    label = label_elem.text if label_elem else "Unknown"
                    label_lower = label.lower()
                    
                    current_val = text_input.get_attribute("value")
                    if not current_val:
                        # Determine answer based on label
                        answer = ""
                        if 'experience' in label_lower or 'years' in label_lower:
                            answer = str(years_of_experience)
                        elif 'phone' in label_lower:
                            answer = phone_number
                        elif 'city' in label_lower:
                            answer = current_city if current_city else "San Francisco"
                        elif 'name' in label_lower:
                            if 'first' in label_lower:
                                answer = first_name
                            elif 'last' in label_lower:
                                answer = last_name
                            else:
                                answer = f"{first_name} {last_name}"
                        elif 'salary' in label_lower:
                            answer = str(desired_salary)
                        else:
                            answer = years_of_experience  # Default fallback
                        
                        if answer:
                            text_input.clear()
                            text_input.send_keys(str(answer))
                            questions_answered.append(f"TEXT: {label[:30]}... -> {str(answer)[:20]}")
                            pilot_log(f"Filled text: {label[:40]}...", "DEBUG")
                    continue
                
                # Check for radio buttons
                radio = try_xp(elem, './/fieldset[@data-test-form-builder-radio-button-form-component="true"]', False)
                if radio:
                    label_elem = try_xp(radio, './/span[@data-test-form-builder-radio-button-form-component__title]', False)
                    label = label_elem.text if label_elem else "Unknown"
                    
                    # Try to click "Yes" option first
                    yes_option = try_xp(radio, ".//label[contains(text(), 'Yes')]", False)
                    if yes_option:
                        actions.move_to_element(yes_option).click().perform()
                        questions_answered.append(f"RADIO: {label[:30]}... -> Yes")
                        pilot_log(f"Filled radio: {label[:40]}...", "DEBUG")
                    continue
                
                # Check for checkboxes
                checkbox = try_xp(elem, ".//input[@type='checkbox']", False)
                if checkbox:
                    if not checkbox.is_selected():
                        try:
                            actions.move_to_element(checkbox).click().perform()
                            questions_answered.append(f"CHECKBOX: checked")
                            pilot_log("Checked checkbox", "DEBUG")
                        except:
                            pass
                    continue
                    
            except StaleElementReferenceException:
                continue
            except Exception as e:
                pilot_log(f"Error processing form element: {e}", "DEBUG")
                continue
        
        pilot_log(f"Answered {len(questions_answered)} questions", "TEST")
        return questions_answered
        
    except Exception as e:
        pilot_log(f"Form filling error: {e}", "ERROR")
        return questions_answered


def test_resume_upload(modal, resume_path: str):
    """Test resume upload functionality"""
    global driver
    
    if not resume_path or not os.path.exists(resume_path):
        pilot_log(f"Resume file not found: {resume_path}", "WARNING")
        return False
    
    try:
        # First try to click upload button
        upload_button_selectors = [
            "//button[contains(., 'Upload resume')]",
            "//button[contains(@aria-label, 'Upload resume')]",
            "//span[contains(text(), 'Upload resume')]/ancestor::button",
            "//label[contains(., 'Upload resume')]",
        ]
        
        for selector in upload_button_selectors:
            try:
                buttons = modal.find_elements(By.XPATH, selector)
                for btn in buttons:
                    if btn.is_displayed():
                        driver.execute_script("arguments[0].click();", btn)
                        pilot_log("Clicked upload button", "DEBUG")
                        time.sleep(0.5)
                        break
            except:
                continue
        
        # Find file input
        file_input_selectors = [
            (By.CSS_SELECTOR, "input[id*='jobs-document-upload-file-input']"),
            (By.XPATH, "//input[@type='file']"),
            (By.CSS_SELECTOR, "input[type='file']"),
        ]
        
        file_input = None
        for by, selector in file_input_selectors:
            try:
                elements = driver.find_elements(by, selector)
                for elem in elements:
                    file_input = elem
                    break
                if file_input:
                    break
            except:
                continue
        
        if file_input:
            # Make visible if hidden
            driver.execute_script("""
                arguments[0].style.display = 'block';
                arguments[0].style.visibility = 'visible';
                arguments[0].style.opacity = '1';
            """, file_input)
            
            abs_path = os.path.abspath(resume_path)
            file_input.send_keys(abs_path)
            time.sleep(1)
            
            dismiss_all_popups()
            
            pilot_log(f"Uploaded resume: {os.path.basename(resume_path)}", "SUCCESS")
            return True
        else:
            pilot_log("No file input found - resume may be pre-filled", "WARNING")
            return False
            
    except Exception as e:
        pilot_log(f"Resume upload error: {e}", "ERROR")
        return False


def navigate_application_form(job_details: dict, resume_path: str = None):
    """Navigate through the application form pages"""
    global driver, wait, actions
    
    results = {
        "pages_navigated": 0,
        "questions_answered": [],
        "resume_uploaded": False,
        "reached_review": False,
        "error": None
    }
    
    try:
        # Wait for modal to appear
        modal = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "jobs-easy-apply-modal"))
        )
        pilot_log("Application modal opened", "INFO")
        
        # Try clicking Next to start
        wait_span_click(driver, "Next", 1)
        time.sleep(0.5)
        
        max_pages = 15
        page = 0
        
        while page < max_pages:
            page += 1
            dismiss_all_popups()
            
            # Re-fetch modal to avoid stale reference
            try:
                modal = driver.find_element(By.CLASS_NAME, "jobs-easy-apply-modal")
            except:
                pilot_log("Modal not found - application may have closed", "WARNING")
                break
            
            pilot_log(f"Processing page {page}", "DEBUG")
            
            # Test form filling
            if PILOT_CONFIG["test_form_filling"]:
                questions = test_form_filling(modal, job_details.get("description", ""))
                results["questions_answered"].extend(questions)
            
            # Test resume upload (only once)
            if PILOT_CONFIG["test_resume_upload"] and not results["resume_uploaded"] and resume_path:
                results["resume_uploaded"] = test_resume_upload(modal, resume_path)
            
            results["pages_navigated"] = page
            
            # Check for Review button (final page)
            try:
                review_btn = modal.find_element(By.XPATH, './/span[normalize-space(.)="Review"]')
                if review_btn:
                    pilot_log("Reached Review page!", "SUCCESS")
                    results["reached_review"] = True
                    break
            except NoSuchElementException:
                pass
            
            # Click Next button
            try:
                next_btn = modal.find_element(By.XPATH, './/button[contains(span, "Next")]')
                if next_btn.is_enabled():
                    next_btn.click()
                    time.sleep(0.8)
                    dismiss_all_popups()
                else:
                    pilot_log("Next button disabled", "WARNING")
                    break
            except NoSuchElementException:
                # Try Continue button
                try:
                    cont_btn = modal.find_element(By.XPATH, './/button[contains(span, "Continue")]')
                    cont_btn.click()
                    time.sleep(0.8)
                except:
                    pilot_log("No navigation button found", "WARNING")
                    break
        
    except Exception as e:
        results["error"] = str(e)
        pilot_log(f"Navigation error: {e}", "ERROR")
    
    return results


def discard_current_application():
    """Discard the current application"""
    global driver, actions
    
    try:
        actions.send_keys(Keys.ESCAPE).perform()
        time.sleep(0.3)
        wait_span_click(driver, 'Discard', 2)
        pilot_log("Application discarded", "INFO")
    except:
        try:
            actions.send_keys(Keys.ESCAPE).perform()
        except:
            pass


def test_single_job(job_details: dict, resume_path: str = None):
    """Test application flow for a single job"""
    global jobs_tested, successful_tests, failed_tests
    
    jobs_tested += 1
    
    pilot_log("=" * 60, "INFO")
    pilot_log(f"TESTING JOB #{jobs_tested}: {job_details['title'][:50]}...", "TEST")
    pilot_log(f"Company: {job_details['company']}", "INFO")
    pilot_log("=" * 60, "INFO")
    
    # Check if already applied
    if check_if_already_applied():
        pilot_log("Already applied to this job - skipping", "WARNING")
        return {"status": "skipped", "reason": "already_applied"}
    
    # Click Easy Apply
    if not click_easy_apply_button():
        pilot_log("Could not start Easy Apply", "ERROR")
        failed_tests += 1
        return {"status": "failed", "reason": "no_easy_apply"}
    
    # Navigate through application
    nav_results = navigate_application_form(job_details, resume_path)
    
    # Log results
    pilot_log("-" * 40, "INFO")
    pilot_log("TEST RESULTS:", "TEST")
    pilot_log(f"  Pages navigated: {nav_results['pages_navigated']}", "INFO")
    pilot_log(f"  Questions answered: {len(nav_results['questions_answered'])}", "INFO")
    pilot_log(f"  Resume uploaded: {nav_results['resume_uploaded']}", "INFO")
    pilot_log(f"  Reached review: {nav_results['reached_review']}", "INFO")
    
    if nav_results.get('error'):
        pilot_log(f"  Error: {nav_results['error']}", "ERROR")
    
    # Determine success
    if nav_results['reached_review']:
        successful_tests += 1
        pilot_log("TEST PASSED - Reached review stage!", "SUCCESS")
        
        if PILOT_CONFIG["skip_submit"]:
            pilot_log("Skipping submission (pilot mode)", "INFO")
            discard_current_application()
    else:
        failed_tests += 1
        pilot_log("TEST INCOMPLETE - Did not reach review", "WARNING")
        discard_current_application()
    
    pilot_log("-" * 40, "INFO")
    
    return {
        "status": "success" if nav_results['reached_review'] else "incomplete",
        "details": nav_results
    }


def run_pilot_mode():
    """Main pilot mode execution"""
    global driver, wait, actions, aiClient, linkedIn_tab
    
    pilot_log("=" * 70, "INFO")
    pilot_log("STARTING PILOT MODE - LinkedIn Job Application Tester", "INFO")
    pilot_log("=" * 70, "INFO")
    
    try:
        # Initialize Chrome with persistent session
        pilot_log("Initializing Chrome browser...", "INFO")
        driver, wait, actions = start_chrome()
        
        # Initialize AI client if enabled
        if use_AI:
            pilot_log(f"Initializing AI client ({ai_provider})...", "INFO")
            try:
                if ai_provider.lower() == "openai":
                    aiClient = ai_create_openai_client()
                elif ai_provider.lower() == "deepseek":
                    aiClient = deepseek_create_client()
                elif ai_provider.lower() == "gemini":
                    aiClient = gemini_create_client()
                elif ai_provider.lower() == "groq":
                    # Groq uses different initialization
                    pilot_log("Groq AI provider detected", "INFO")
            except Exception as e:
                pilot_log(f"AI client initialization error (non-critical): {e}", "WARNING")
        
        # Navigate to LinkedIn and check login
        driver.get("https://www.linkedin.com/login")
        time.sleep(2)
        
        # Try automatic login first
        if not is_logged_in_LN():
            pilot_log("Attempting automatic login...", "INFO")
            login_success = login_LN()
            
            if not login_success:
                pilot_log("Automatic login failed - please log in manually", "WARNING")
                pilot_log(f"Waiting {PILOT_CONFIG['login_wait_time']} seconds for manual login...", "INFO")
                
                # Show alert to user
                try:
                    pyautogui.alert(
                        "Please log in to LinkedIn manually in the browser window.\n\nClick OK when done.",
                        "Manual Login Required"
                    )
                except:
                    pass
                
                # Wait and check periodically
                wait_time = PILOT_CONFIG['login_wait_time']
                check_interval = 5
                for i in range(0, wait_time, check_interval):
                    time.sleep(check_interval)
                    if is_logged_in_LN():
                        pilot_log("Login detected!", "SUCCESS")
                        break
                    if i % 15 == 0:
                        pilot_log(f"Still waiting for login... ({wait_time - i}s remaining)", "INFO")
                
                if not is_logged_in_LN():
                    pilot_log("Login timeout - exiting", "ERROR")
                    return
        
        pilot_log("Logged into LinkedIn", "SUCCESS")
        linkedIn_tab = driver.current_window_handle
        
        # Navigate to job search
        if not navigate_to_job_search():
            pilot_log("Failed to load job search", "ERROR")
            return
        
        # Get job listings
        job_listings = get_job_listings()
        if not job_listings:
            pilot_log("No jobs found", "ERROR")
            return
        
        # Determine resume to use
        resume_path = default_resume_path if os.path.exists(default_resume_path) else None
        if resume_path:
            pilot_log(f"Using resume: {os.path.basename(resume_path)}", "INFO")
        else:
            pilot_log("No resume found - will test without upload", "WARNING")
        
        # Test jobs
        max_jobs = min(PILOT_CONFIG["max_jobs_to_test"], len(job_listings))
        pilot_log(f"Will test {max_jobs} jobs", "INFO")
        
        for i in range(max_jobs):
            # Get fresh listing reference (avoid stale element)
            job_listings = get_job_listings()
            if i >= len(job_listings):
                break
            
            job = job_listings[i]
            
            # Get job details
            job_details = click_job_and_get_details(job)
            if not job_details:
                continue
            
            # Test the job
            result = test_single_job(job_details, resume_path)
            
            # Pause between jobs if configured
            if PILOT_CONFIG["pause_between_jobs"] and i < max_jobs - 1:
                pilot_log("Pausing between jobs...", "INFO")
                try:
                    decision = pyautogui.confirm(
                        f"Completed job #{i+1}\n\nContinue to next job?",
                        "Pilot Mode",
                        ["Continue", "Stop"]
                    )
                    if decision == "Stop":
                        pilot_log("Stopped by user", "INFO")
                        break
                except:
                    time.sleep(2)
            
            time.sleep(1)
            dismiss_all_popups()
        
        # Final summary
        pilot_log("=" * 70, "INFO")
        pilot_log("PILOT MODE COMPLETE - SUMMARY", "INFO")
        pilot_log("=" * 70, "INFO")
        pilot_log(f"Jobs tested: {jobs_tested}", "INFO")
        pilot_log(f"Successful: {successful_tests}", "SUCCESS")
        pilot_log(f"Failed/Incomplete: {failed_tests}", "WARNING")
        pilot_log("=" * 70, "INFO")
        
        # Keep browser open for inspection
        pilot_log("Browser will remain open for inspection.", "INFO")
        try:
            pyautogui.alert(
                f"Pilot Mode Complete!\n\n"
                f"Jobs tested: {jobs_tested}\n"
                f"Successful: {successful_tests}\n"
                f"Failed: {failed_tests}\n\n"
                f"Click OK to close browser.",
                "Pilot Mode Summary"
            )
        except:
            pilot_log("Press Enter to close...", "INFO")
            input()
        
    except KeyboardInterrupt:
        pilot_log("Interrupted by user", "WARNING")
    except Exception as e:
        pilot_log(f"Fatal error: {e}", "ERROR")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        try:
            close_driver()
        except:
            pass
        pilot_log("Pilot mode ended", "INFO")


if __name__ == "__main__":
    run_pilot_mode()
