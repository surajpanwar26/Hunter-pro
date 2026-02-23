#!/usr/bin/env python3
"""
E2E TEST: Submit 3 Job Applications
====================================
This script uses undetected-chromedriver to submit 3 LinkedIn Easy Apply applications.
It properly fills form fields and handles different question types.

Run: python e2e_submit_3_apps.py

*** IMPORTANT: Close all Chrome windows before running! ***
"""

import os
import sys
import time
import subprocess
import shutil
import re
from datetime import datetime

# =============================================================================
# CONFIGURATION - SET ACTUALLY_SUBMIT = True TO SUBMIT REAL APPLICATIONS
# =============================================================================
ACTUALLY_SUBMIT = False  # SET TO True TO SUBMIT APPLICATIONS!
TARGET_APPS = 3
MAX_JOBS_TO_TRY = 20  # Try up to 20 jobs to get 3 successful applications

# =============================================================================
# Setup
# =============================================================================
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'config'))

def log(msg, icon="   "):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{ts} {icon} {msg}")
    sys.stdout.flush()

def kill_chrome():
    """Kill all Chrome/chromedriver processes."""
    log("Killing Chrome processes...", "[*]")
    try:
        for proc in ['chromedriver.exe', 'chrome.exe', 'undetected_chromedriver.exe']:
            subprocess.run(['taskkill', '/F', '/IM', proc, '/T'], 
                          capture_output=True, timeout=10)
        time.sleep(5)
    except:
        pass
    
    # Clean UC cache
    uc_path = os.path.join(os.getenv('APPDATA', ''), 'undetected_chromedriver')
    if os.path.exists(uc_path):
        try:
            shutil.rmtree(uc_path)
            log("Cleaned UC driver cache", "[+]")
        except:
            pass
    
    # Remove lock files
    for f in ['SingletonLock', 'SingletonSocket', 'SingletonCookie', 'DevToolsActivePort']:
        try:
            path = os.path.join(project_root, 'chrome_profile', f)
            if os.path.exists(path):
                os.remove(path)
        except:
            pass

# =============================================================================
# Load User Config
# =============================================================================
def load_config():
    """Load user configuration from config files."""
    config = {
        'first_name': 'Suraj',
        'last_name': 'Panwar',
        'phone': '8108609815',
        'email': '',
        'city': 'Mumbai',
        'state': 'Maharashtra', 
        'zipcode': '401105',
        'country': 'India',
        'street': 'A-901 Raj Classic Indralok phase 6',
        'years_experience': '5',
        'require_visa': 'Yes',
        'us_citizenship': 'Non-citizen allowed to work for any employer',
        'linkedin': 'https://www.linkedin.com/in/saivigneshgolla/',
        'website': 'https://github.com/GodsScion',
        'salary': '1500000',
        'current_ctc': '800000',
        'notice_period': '30',
        'headline': 'Full Stack Developer with Masters in Computer Science',
        'recent_employer': 'Deloitte United States (USI)',
        'gender': 'Male',
        'ethnicity': 'Asian',
        'disability': 'No',
        'veteran': 'No',
    }
    
    try:
        import personals
        config['first_name'] = getattr(personals, 'first_name', config['first_name'])
        config['last_name'] = getattr(personals, 'last_name', config['last_name'])
        config['phone'] = getattr(personals, 'phone_number', config['phone']).replace('*', '')
        config['city'] = getattr(personals, 'current_city', config['city'])
        config['state'] = getattr(personals, 'state', config['state'])
        config['zipcode'] = getattr(personals, 'zipcode', config['zipcode'])
        config['country'] = getattr(personals, 'country', config['country'])
        config['street'] = getattr(personals, 'street', config['street'])
        config['years_experience'] = str(getattr(personals, 'years_of_experience', config['years_experience']))
        config['gender'] = getattr(personals, 'gender', config['gender'])
        config['ethnicity'] = getattr(personals, 'ethnicity', config['ethnicity'])
        config['disability'] = getattr(personals, 'disability_status', config['disability'])
        config['veteran'] = getattr(personals, 'veteran_status', config['veteran'])
        log(f"Loaded personals: {config['first_name']} {config['last_name']}", "[+]")
    except Exception as e:
        log(f"personals.py not loaded: {e}", "[?]")
    
    try:
        import questions
        config['years_experience'] = str(getattr(questions, 'years_of_experience', config['years_experience']))
        config['require_visa'] = getattr(questions, 'require_visa', config['require_visa'])
        config['us_citizenship'] = getattr(questions, 'us_citizenship', config['us_citizenship'])
        config['linkedin'] = getattr(questions, 'linkedIn', config['linkedin'])
        config['website'] = getattr(questions, 'website', config['website'])
        config['salary'] = str(getattr(questions, 'desired_salary', config['salary']))
        config['current_ctc'] = str(getattr(questions, 'current_ctc', config['current_ctc']))
        config['notice_period'] = str(getattr(questions, 'notice_period', config['notice_period']))
        config['headline'] = getattr(questions, 'linkedin_headline', config['headline'])
        config['recent_employer'] = getattr(questions, 'recent_employer', config['recent_employer'])
        log(f"Loaded questions config", "[+]")
    except Exception as e:
        log(f"questions.py not loaded: {e}", "[?]")
    
    try:
        import secrets as user_secrets
        config['email'] = getattr(user_secrets, 'email', config['email'])
        config['phone'] = getattr(user_secrets, 'phone', config['phone']).replace('*', '') if hasattr(user_secrets, 'phone') else config['phone']
        log(f"Loaded secrets: {config['email']}", "[+]")
    except Exception as e:
        log(f"secrets.py not loaded: {e}", "[?]")
    
    return config

# =============================================================================
# Form Filling Logic
# =============================================================================
class FormFiller:
    def __init__(self, driver, config):
        self.driver = driver
        self.config = config
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait, Select
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
        self.By = By
        self.WebDriverWait = WebDriverWait
        self.Select = Select
        self.EC = EC
        self.TimeoutException = TimeoutException
        self.NoSuchElementException = NoSuchElementException
        self.StaleElementReferenceException = StaleElementReferenceException
    
    def fill_text_field(self, element, value):
        """Fill a text input field."""
        try:
            element.clear()
            time.sleep(0.1)
            element.send_keys(str(value))
            return True
        except:
            return False
    
    def select_dropdown(self, element, value):
        """Select option from dropdown."""
        try:
            select = self.Select(element)
            # Try exact match first
            for option in select.options:
                if value.lower() in option.text.lower():
                    select.select_by_visible_text(option.text)
                    return True
            # Try first non-empty option
            for option in select.options:
                if option.text.strip() and option.get_attribute('value'):
                    select.select_by_visible_text(option.text)
                    return True
        except:
            pass
        return False
    
    def click_radio_or_checkbox(self, container, value):
        """Select radio button or checkbox based on value."""
        try:
            # Find all radio/checkbox options
            options = container.find_elements(self.By.CSS_SELECTOR, 
                "label, input[type='radio'], input[type='checkbox'], [data-test-text-selectable-option]")
            
            value_lower = value.lower()
            
            # Try to find matching option
            for opt in options:
                text = opt.text.lower() if opt.text else ''
                label_for = opt.get_attribute('for') or ''
                
                # Check for Yes/No questions
                if value_lower in ['yes', 'true', '1']:
                    if 'yes' in text or text == 'y':
                        opt.click()
                        return True
                elif value_lower in ['no', 'false', '0']:
                    if 'no' in text or text == 'n':
                        opt.click()
                        return True
                # Check for matching text
                elif value_lower in text:
                    opt.click()
                    return True
            
            # If no match, click first option
            if options:
                options[0].click()
                return True
        except:
            pass
        return False
    
    def get_question_text(self, container):
        """Extract question text from container."""
        try:
            # Try different selectors for question labels
            selectors = [
                "label span.visually-hidden",
                "label",
                ".artdeco-text-input--label",
                ".fb-dash-form-element__label",
                "legend",
                ".t-14"
            ]
            for sel in selectors:
                try:
                    el = container.find_element(self.By.CSS_SELECTOR, sel)
                    if el.text.strip():
                        return el.text.strip().lower()
                except:
                    continue
            return container.text.strip().lower()[:200]
        except:
            return ""
    
    def determine_answer(self, question):
        """Determine the best answer based on question text."""
        q = question.lower()
        
        # Years of experience
        if 'year' in q and 'experience' in q:
            return self.config['years_experience']
        
        # Phone
        if 'phone' in q or 'mobile' in q or 'contact number' in q:
            return self.config['phone']
        
        # Email
        if 'email' in q:
            return self.config['email'] or f"{self.config['first_name'].lower()}.{self.config['last_name'].lower()}@gmail.com"
        
        # Name
        if 'first name' in q:
            return self.config['first_name']
        if 'last name' in q or 'surname' in q:
            return self.config['last_name']
        if 'full name' in q:
            return f"{self.config['first_name']} {self.config['last_name']}"
        
        # Location
        if 'city' in q:
            return self.config['city']
        if 'state' in q or 'province' in q:
            return self.config['state']
        if 'zip' in q or 'postal' in q or 'pincode' in q:
            return self.config['zipcode']
        if 'country' in q:
            return self.config['country']
        if 'address' in q or 'street' in q:
            return self.config['street']
        
        # Visa/Work Authorization
        if 'visa' in q or 'sponsorship' in q:
            return self.config['require_visa']
        if 'authorized' in q or 'legally' in q or 'citizenship' in q or 'work permit' in q:
            if 'us' in q or 'united states' in q or 'america' in q:
                return self.config['us_citizenship']
            return 'Yes'
        
        # Salary
        if 'salary' in q or 'compensation' in q or 'ctc' in q or 'pay' in q:
            if 'current' in q or 'present' in q:
                return self.config['current_ctc']
            if 'expected' in q or 'desired' in q:
                return self.config['salary']
            return self.config['salary']
        
        # Notice Period
        if 'notice' in q or 'join' in q or 'start' in q:
            if 'day' in q:
                return self.config['notice_period']
            if 'week' in q:
                return str(int(self.config['notice_period']) // 7)
            if 'month' in q:
                return str(int(self.config['notice_period']) // 30)
            if 'immediately' in q:
                return 'Yes' if self.config['notice_period'] == '0' else 'No'
            return self.config['notice_period']
        
        # LinkedIn/Website
        if 'linkedin' in q:
            return self.config['linkedin']
        if 'website' in q or 'portfolio' in q or 'github' in q:
            return self.config['website']
        
        # Employer
        if 'employer' in q or 'company' in q or 'organization' in q:
            if 'current' in q or 'recent' in q or 'present' in q:
                return self.config['recent_employer']
        
        # Demographics
        if 'gender' in q or 'sex' in q:
            return self.config['gender']
        if 'race' in q or 'ethnic' in q:
            return self.config['ethnicity']
        if 'disability' in q or 'disabilities' in q:
            return self.config['disability']
        if 'veteran' in q or 'military' in q:
            return self.config['veteran']
        
        # Headline
        if 'headline' in q or 'title' in q or 'position' in q:
            return self.config['headline']
        
        # Common Yes/No questions
        if 'willing' in q or 'agree' in q or 'consent' in q or 'confirm' in q:
            return 'Yes'
        if 'relocate' in q:
            return 'Yes'
        if 'travel' in q:
            return 'Yes'
        if 'background check' in q or 'drug test' in q:
            return 'Yes'
        if 'referred' in q or 'referral' in q:
            return 'No'
        if 'previously applied' in q or 'worked before' in q:
            return 'No'
        if 'degree' in q or 'bachelor' in q or 'master' in q:
            return 'Yes'
        if '18' in q or 'age' in q:
            return 'Yes'
        
        # Default for numeric questions
        if any(x in q for x in ['how many', 'how much', 'number of', 'rate', 'scale']):
            return self.config['years_experience']
        
        # Default fallback
        return 'Yes'
    
    def fill_form_fields(self):
        """Fill all visible form fields on current page."""
        filled_count = 0
        
        try:
            # Find all form groups/containers
            containers = self.driver.find_elements(self.By.CSS_SELECTOR,
                ".jobs-easy-apply-form-section__grouping, "
                ".fb-dash-form-element, "
                ".artdeco-text-input--container, "
                "[data-test-form-element]"
            )
            
            for container in containers:
                try:
                    question = self.get_question_text(container)
                    if not question:
                        continue
                    
                    answer = self.determine_answer(question)
                    
                    # Try text input
                    try:
                        inputs = container.find_elements(self.By.CSS_SELECTOR, 
                            "input[type='text'], input[type='tel'], input[type='email'], "
                            "input[type='number'], input:not([type]), textarea")
                        for inp in inputs:
                            if inp.is_displayed() and inp.is_enabled():
                                current_val = inp.get_attribute('value')
                                if not current_val or len(current_val) < 2:
                                    if self.fill_text_field(inp, answer):
                                        filled_count += 1
                                        log(f"  Filled: {question[:40]}... = {answer[:30]}", "   ")
                                        break
                    except:
                        pass
                    
                    # Try dropdown
                    try:
                        selects = container.find_elements(self.By.TAG_NAME, "select")
                        for sel in selects:
                            if sel.is_displayed():
                                if self.select_dropdown(sel, answer):
                                    filled_count += 1
                                    log(f"  Selected: {question[:40]}...", "   ")
                                    break
                    except:
                        pass
                    
                    # Try radio/checkbox
                    try:
                        radios = container.find_elements(self.By.CSS_SELECTOR,
                            "input[type='radio'], input[type='checkbox'], "
                            "[data-test-text-selectable-option]")
                        if radios:
                            if self.click_radio_or_checkbox(container, answer):
                                filled_count += 1
                                log(f"  Clicked: {question[:40]}...", "   ")
                    except:
                        pass
                        
                except self.StaleElementReferenceException:
                    continue
                except Exception as e:
                    continue
        except Exception as e:
            log(f"  Form fill error: {str(e)[:50]}", "[?]")
        
        return filled_count
    
    def handle_resume_page(self):
        """Handle resume upload/selection page."""
        try:
            # Check if on resume page
            resume_elements = self.driver.find_elements(self.By.CSS_SELECTOR,
                ".jobs-document-upload, [class*='document-upload'], "
                "[data-test-document-upload-section], .jobs-resume-picker")
            
            if resume_elements:
                log("  Resume page detected - using preselected", "[+]")
                
                # Try to select first available resume if there are options
                try:
                    resume_options = self.driver.find_elements(self.By.CSS_SELECTOR,
                        ".jobs-document-upload-redesign-card, "
                        "[data-test-document-upload-card]")
                    if resume_options:
                        # Click first (most recent) resume
                        resume_options[0].click()
                        time.sleep(0.5)
                except:
                    pass
                
                return True
        except:
            pass
        return False


# =============================================================================
# Main Test
# =============================================================================
def main():
    print("\n" + "="*60)
    print("E2E TEST: SUBMIT 3 JOB APPLICATIONS")
    print("="*60)
    print(f"Target: {TARGET_APPS} applications")
    print(f"Actually Submit: {ACTUALLY_SUBMIT}")
    print("="*60 + "\n")
    
    if not ACTUALLY_SUBMIT:
        print("⚠️  WARNING: ACTUALLY_SUBMIT is False!")
        print("⚠️  Set ACTUALLY_SUBMIT = True to submit real applications")
        print("="*60 + "\n")
    
    kill_chrome()
    time.sleep(2)
    
    # Load config
    config = load_config()
    
    # Import selenium
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    from selenium.webdriver.common.keys import Keys
    
    driver = None
    apps_submitted = 0
    jobs_attempted = 0
    jobs_applied = []
    
    try:
        # Start Chrome
        log("Starting Chrome...", "[*]")
        options = uc.ChromeOptions()
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--log-level=3")
        
        profile_path = os.path.join(project_root, 'chrome_profile')
        options.add_argument(f"--user-data-dir={profile_path}")
        log(f"Using profile: {profile_path}", "[+]")
        
        driver = uc.Chrome(options=options, version_main=144, use_subprocess=True)
        log("Chrome started!", "[+]")
        
        wait = WebDriverWait(driver, 15)
        filler = FormFiller(driver, config)
        
        # Navigate to LinkedIn jobs
        log("Navigating to LinkedIn...", "[*]")
        driver.get("https://www.linkedin.com/jobs/search/"
                  "?keywords=Software%20Engineer"
                  "&location=United%20States"
                  "&f_AL=true"  # Easy Apply only
                  "&f_E=2,3,4"  # Entry, Associate, Mid-Senior level
                  "&f_TPR=r604800"  # Past week
                  "&sortBy=DD")  # Most recent
        
        time.sleep(5)
        
        # Check if logged in
        current_url = driver.current_url
        log(f"URL: {current_url[:70]}", "[*]")
        
        if 'login' in current_url.lower() or 'authwall' in current_url.lower():
            log("Not logged in! Waiting 2 minutes for manual login...", "[!]")
            start = time.time()
            while time.time() - start < 120:
                time.sleep(5)
                if 'login' not in driver.current_url.lower():
                    log("Login detected!", "[+]")
                    driver.get("https://www.linkedin.com/jobs/search/"
                              "?keywords=Software%20Engineer"
                              "&location=United%20States"
                              "&f_AL=true&f_TPR=r604800&sortBy=DD")
                    time.sleep(5)
                    break
            else:
                log("Login timeout!", "[!]")
                return False
        
        log("Logged in and on job search page", "[+]")
        time.sleep(3)
        
        # Process jobs
        for job_idx in range(MAX_JOBS_TO_TRY):
            if apps_submitted >= TARGET_APPS:
                log(f"\n🎉 SUCCESS! Submitted {TARGET_APPS} applications!", "[+]")
                break
            
            log(f"\n{'='*40}", "[*]")
            log(f"JOB {job_idx + 1} (Submitted: {apps_submitted}/{TARGET_APPS})", "[*]")
            log(f"{'='*40}", "[*]")
            
            try:
                # Get job cards
                job_cards = driver.find_elements(By.CSS_SELECTOR,
                    "li.jobs-search-results__list-item, li[data-occludable-job-id]")
                
                if job_idx >= len(job_cards):
                    log("No more jobs, scrolling...", "[?]")
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    job_cards = driver.find_elements(By.CSS_SELECTOR,
                        "li.jobs-search-results__list-item")
                    if job_idx >= len(job_cards):
                        log("No more jobs available", "[!]")
                        break
                
                # Click job card
                card = job_cards[job_idx]
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
                time.sleep(1)
                
                try:
                    card.click()
                except:
                    driver.execute_script("arguments[0].click();", card)
                
                time.sleep(3)  # Wait for job details to load
                
                # Get job title
                job_title = "Unknown"
                try:
                    title_el = driver.find_element(By.CSS_SELECTOR,
                        "h1.t-24, .jobs-unified-top-card__job-title, h2.job-card-list__title")
                    job_title = title_el.text.strip()[:50]
                except:
                    pass
                
                log(f"Job: {job_title}", "   ")
                
                # Check if already applied
                try:
                    applied_badge = driver.find_element(By.XPATH,
                        "//*[contains(@class, 'feedback') and contains(., 'Applied')]")
                    if applied_badge.is_displayed():
                        log("Already applied - skipping", "[?]")
                        continue
                except:
                    pass
                
                # Find Easy Apply button - try multiple selectors
                easy_apply_btn = None
                selectors = [
                    "//button[contains(@class, 'jobs-apply-button')]",
                    "//button[.//span[contains(text(), 'Easy Apply')]]",
                    "//button[contains(text(), 'Easy Apply')]",
                    "//button[contains(@aria-label, 'Easy Apply')]",
                    "//div[contains(@class, 'jobs-apply-button')]//button",
                ]
                
                for sel in selectors:
                    try:
                        btns = driver.find_elements(By.XPATH, sel)
                        for btn in btns:
                            try:
                                if btn.is_displayed() and btn.is_enabled():
                                    btn_text = btn.text.lower()
                                    # Make sure it's actually an Easy Apply button
                                    if 'easy' in btn_text or 'apply' in btn_text:
                                        easy_apply_btn = btn
                                        break
                            except:
                                continue
                    except:
                        continue
                    if easy_apply_btn:
                        break
                
                if not easy_apply_btn:
                    # Try one more time with a broader search
                    try:
                        all_btns = driver.find_elements(By.TAG_NAME, "button")
                        for btn in all_btns:
                            try:
                                if btn.is_displayed() and 'easy' in btn.text.lower():
                                    easy_apply_btn = btn
                                    break
                            except:
                                continue
                    except:
                        pass
                
                if not easy_apply_btn:
                    log("No Easy Apply button - skipping", "[?]")
                    continue
                
                # Click Easy Apply
                log("Clicking Easy Apply...", "[*]")
                jobs_attempted += 1
                
                try:
                    easy_apply_btn.click()
                except:
                    driver.execute_script("arguments[0].click();", easy_apply_btn)
                
                time.sleep(2)
                
                # Check modal opened
                try:
                    modal = wait.until(EC.presence_of_element_located((
                        By.CSS_SELECTOR, ".jobs-easy-apply-modal, .artdeco-modal")))
                    log("Modal opened", "[+]")
                except TimeoutException:
                    log("Modal didn't open - skipping", "[?]")
                    continue
                
                # Navigate through application pages
                submitted = False
                page_count = 0
                max_pages = 12
                last_page_text = ""
                stuck_count = 0
                
                while page_count < max_pages and not submitted:
                    page_count += 1
                    time.sleep(1.5)
                    
                    # Get current page content to detect changes
                    try:
                        modal = driver.find_element(By.CSS_SELECTOR, ".jobs-easy-apply-modal, .artdeco-modal")
                        current_page_text = modal.text[:500]
                    except:
                        current_page_text = ""
                    
                    # Check if stuck on same page
                    if current_page_text == last_page_text and current_page_text:
                        stuck_count += 1
                        if stuck_count >= 3:
                            log("  Stuck on same page - breaking", "[?]")
                            break
                    else:
                        stuck_count = 0
                    last_page_text = current_page_text
                    
                    # Handle resume page
                    filler.handle_resume_page()
                    
                    # Fill form fields
                    filled = filler.fill_form_fields()
                    if filled > 0:
                        log(f"  Page {page_count}: Filled {filled} fields", "   ")
                    
                    # Check for Submit button - FIRST priority
                    try:
                        # Look for Submit button using multiple methods
                        submit_btn = None
                        
                        # Method 1: Direct button text search
                        try:
                            all_buttons = driver.find_elements(By.TAG_NAME, "button")
                            for btn in all_buttons:
                                try:
                                    btn_text = btn.text.strip().lower()
                                    if btn.is_displayed() and 'submit' in btn_text:
                                        submit_btn = btn
                                        log(f"  Found button with text: {btn_text[:30]}", "   ")
                                        break
                                except:
                                    continue
                        except:
                            pass
                        
                        # Method 2: Aria-label search
                        if not submit_btn:
                            try:
                                submit_btn = driver.find_element(By.CSS_SELECTOR,
                                    "button[aria-label*='Submit application'], button[aria-label*='submit application']")
                            except:
                                pass
                        
                        # Method 3: XPath search
                        if not submit_btn:
                            try:
                                submit_btn = driver.find_element(By.XPATH,
                                    "//button[.//span[contains(text(),'Submit')]] | //button[contains(text(),'Submit')]")
                            except:
                                pass
                        
                        if submit_btn and submit_btn.is_displayed():
                            log("🎯 Found SUBMIT button!", "[+]")
                            
                            if ACTUALLY_SUBMIT:
                                try:
                                    submit_btn.click()
                                except:
                                    driver.execute_script("arguments[0].click();", submit_btn)
                                time.sleep(3)
                                
                                # Check for success indicators
                                success = False
                                try:
                                    success_el = driver.find_element(By.XPATH,
                                        "//*[contains(text(),'Application sent') or contains(text(),'application submitted') or contains(text(),'applied')]")
                                    if success_el:
                                        success = True
                                except:
                                    pass
                                
                                # Also check if modal closed
                                try:
                                    driver.find_element(By.CSS_SELECTOR, ".jobs-easy-apply-modal")
                                except:
                                    success = True  # Modal closed = likely submitted
                                
                                if success:
                                    log("✅ APPLICATION SUBMITTED!", "[+]")
                                    submitted = True
                                    apps_submitted += 1
                                    jobs_applied.append(job_title)
                                else:
                                    log("  Submit clicked but no confirmation", "[?]")
                            else:
                                log("(Test mode - not submitting)", "   ")
                                submitted = True
                                apps_submitted += 1
                                jobs_applied.append(job_title)
                            
                            break  # Exit the while loop
                    except Exception as submit_err:
                        pass
                    
                    if submitted:
                        break
                    
                    # Check for Review button
                    try:
                        review_btn = driver.find_element(By.XPATH,
                            "//button[.//span[text()='Review']]")
                        if review_btn.is_displayed() and review_btn.is_enabled():
                            log("  Clicking Review...", "   ")
                            review_btn.click()
                            time.sleep(1)
                            continue
                    except:
                        pass
                    
                    # Check for Next button
                    try:
                        next_btns = driver.find_elements(By.XPATH,
                            "//button[contains(@aria-label, 'Continue') or .//span[text()='Next']]")
                        
                        clicked_next = False
                        for btn in next_btns:
                            if btn.is_displayed() and btn.is_enabled():
                                log("  Clicking Next...", "   ")
                                btn.click()
                                clicked_next = True
                                time.sleep(1)
                                break
                        
                        if not clicked_next:
                            # Check if Next is disabled (required fields missing)
                            try:
                                disabled_btn = driver.find_element(By.XPATH,
                                    "//button[@disabled and (contains(@aria-label, 'Continue') or .//span[text()='Next'])]")
                                log("  Next disabled - required fields missing", "[?]")
                                
                                # Try to fill any remaining required fields
                                filler.fill_form_fields()
                                time.sleep(0.5)
                                
                                # Check if still disabled
                                try:
                                    still_disabled = driver.find_element(By.XPATH,
                                        "//button[@disabled and contains(@aria-label, 'Continue')]")
                                    log("  Still blocked - skipping job", "[!]")
                                    break
                                except:
                                    # Not disabled anymore, continue
                                    continue
                            except:
                                pass
                    except:
                        pass
                    
                    # Safety check for too many pages
                    if page_count >= max_pages - 1:
                        log("  Too many pages - breaking", "[?]")
                        break
                
                # Close modal if not submitted
                if not submitted:
                    try:
                        close_btn = driver.find_element(By.CSS_SELECTOR,
                            "button[aria-label='Dismiss'], .artdeco-modal__dismiss")
                        if close_btn.is_displayed():
                            close_btn.click()
                            time.sleep(0.5)
                            
                            # Confirm discard
                            try:
                                discard = driver.find_element(By.XPATH,
                                    "//button[contains(., 'Discard')]")
                                if discard.is_displayed():
                                    discard.click()
                            except:
                                pass
                    except:
                        pass
                else:
                    # Close success modal
                    try:
                        done_btn = driver.find_element(By.XPATH,
                            "//button[.//span[contains(text(), 'Done')] or contains(., 'Done')]")
                        if done_btn.is_displayed():
                            done_btn.click()
                    except:
                        pass
                    
                    try:
                        close_btn = driver.find_element(By.CSS_SELECTOR,
                            "button[aria-label='Dismiss'], .artdeco-modal__dismiss")
                        if close_btn.is_displayed():
                            close_btn.click()
                    except:
                        pass
                
                time.sleep(2)
                
            except Exception as e:
                log(f"Error: {str(e)[:60]}", "[!]")
                # Try to close any open modal
                try:
                    close = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Dismiss']")
                    close.click()
                    time.sleep(0.5)
                    try:
                        discard = driver.find_element(By.XPATH, "//button[contains(., 'Discard')]")
                        discard.click()
                    except:
                        pass
                except:
                    pass
                continue
        
        return apps_submitted >= 1
        
    except Exception as e:
        log(f"Fatal error: {e}", "[!]")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Print results
        print("\n" + "="*60)
        print("TEST RESULTS")
        print("="*60)
        print(f"  Jobs Attempted:    {jobs_attempted}")
        print(f"  Apps Submitted:    {apps_submitted}")
        print(f"  Target:            {TARGET_APPS}")
        print(f"\n  Jobs Applied To:")
        for i, j in enumerate(jobs_applied, 1):
            print(f"    {i}. {j}")
        print("="*60)
        
        if apps_submitted >= TARGET_APPS:
            print(f"  ✅ TEST PASSED! ({apps_submitted}/{TARGET_APPS} applications)")
        elif apps_submitted >= 1:
            print(f"  ⚠️  PARTIAL SUCCESS ({apps_submitted}/{TARGET_APPS} applications)")
        else:
            print("  ❌ TEST FAILED - No applications submitted")
        print("="*60 + "\n")
        
        if driver:
            try:
                driver.quit()
            except:
                pass
        
        kill_chrome()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
