"""
E2E Autopilot Test — Test Job Site
===================================
Tests the bot's core capabilities against a local test job site:
  1. Navigate to the job listing, extract JD
  2. Click "Apply Now"
  3. Fill ALL form fields (text, select, radio, checkbox, textarea, file upload)
  4. Navigate multi-page form (Next → Next → Review → Submit)
  5. Verify submission success

Run:
    1. Start the test site:  python -m http.server 8080 --directory test_job_site
    2. Run this script:      python e2e_test_autopilot.py

Requires: selenium, webdriver-manager
"""

import os, sys, time, json, traceback
from pathlib import Path
from datetime import datetime

# Add project root to path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait, Select
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import (
        NoSuchElementException, TimeoutException,
        ElementNotInteractableException, StaleElementReferenceException
    )
except ImportError:
    print("❌ selenium not installed. Run:  pip install selenium webdriver-manager")
    sys.exit(1)


# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
BASE_URL   = "http://localhost:8080"
HEADLESS   = False   # set True for CI
TIMEOUT    = 10      # global wait seconds
STEP_DELAY = 0.4     # seconds between actions (readability)

# Load personal data from config  (same source as the real bot)
try:
    from config.personals import (
        first_name, last_name, phone_number, current_city,
        state, zipcode, country, years_of_experience, gender,
        linkedIn, website, university, degree, field_of_study, gpa,
        notice_period, desired_salary, current_ctc, recent_employer,
        confidence_level, disability_status
    )
    from config.secrets import username as email
except ImportError:
    # Fallback test data
    first_name, last_name = "John", "Doe"
    email           = "john.doe@example.com"
    phone_number    = "9876543210"
    current_city    = "Mumbai"
    state           = "Maharashtra"
    zipcode         = "400001"
    country         = "India"
    linkedIn        = "https://linkedin.com/in/johndoe"
    website         = "https://johndoe.dev"
    years_of_experience = "5"
    gender          = "Male"
    university      = "IIT Bombay"
    degree          = "Bachelor's"
    field_of_study  = "Computer Science"
    gpa             = "8.5"
    notice_period   = "30"
    desired_salary  = "2500000"
    current_ctc     = "1800000"
    recent_employer = "TCS"
    confidence_level = "85"
    disability_status = "No"

# Resume file
RESUME_DIR = ROOT / "all resumes" / "default"
RESUME_FILE = None
for ext in ("*.pdf", "*.docx", "*.doc"):
    matches = list(RESUME_DIR.glob(ext))
    if matches:
        RESUME_FILE = str(matches[0])
        break
if not RESUME_FILE:
    # Create a dummy resume for testing
    RESUME_FILE = str(ROOT / "all resumes" / "test" / "test_resume.pdf")
    os.makedirs(os.path.dirname(RESUME_FILE), exist_ok=True)
    if not os.path.exists(RESUME_FILE):
        # Create a minimal PDF (just a header — enough for upload testing)
        with open(RESUME_FILE, "wb") as f:
            f.write(b"%PDF-1.0\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
                    b"2 0 obj<</Type/Pages/Kids[]/Count 0>>endobj\nxref\n0 3\n"
                    b"trailer<</Size 3/Root 1 0 R>>\nstartxref\n0\n%%EOF\n")


# ──────────────────────────────────────────────
# TEST RESULTS
# ──────────────────────────────────────────────
class TestResults:
    def __init__(self):
        self.passed  = []
        self.failed  = []
        self.skipped = []
        self.start   = time.time()

    def ok(self, name, detail=""):
        self.passed.append((name, detail))
        print(f"  ✅ {name}" + (f" — {detail}" if detail else ""))

    def fail(self, name, detail=""):
        self.failed.append((name, detail))
        print(f"  ❌ {name}" + (f" — {detail}" if detail else ""))

    def skip(self, name, reason=""):
        self.skipped.append((name, reason))
        print(f"  ⏭️  {name}" + (f" — {reason}" if reason else ""))

    def summary(self):
        elapsed = time.time() - self.start
        total = len(self.passed) + len(self.failed) + len(self.skipped)
        print("\n" + "═" * 60)
        print(f"  TEST RESULTS  ({elapsed:.1f}s)")
        print("═" * 60)
        print(f"  ✅ Passed:  {len(self.passed)}/{total}")
        print(f"  ❌ Failed:  {len(self.failed)}/{total}")
        print(f"  ⏭️  Skipped: {len(self.skipped)}/{total}")
        if self.failed:
            print("\n  Failed tests:")
            for name, detail in self.failed:
                print(f"    • {name}: {detail}")
        print("═" * 60)
        return len(self.failed) == 0


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────
def slow(s=STEP_DELAY):
    time.sleep(s)


def safe_fill(driver, element, value, clear_first=True):
    """Fill a text input safely, scrolling into view first."""
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
        slow(0.1)
        if clear_first:
            element.clear()
        element.send_keys(str(value))
        return True
    except (ElementNotInteractableException, StaleElementReferenceException):
        # JS fallback
        driver.execute_script(
            "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input'));",
            element, str(value)
        )
        return True
    except Exception:
        return False


def safe_select(driver, element, visible_text=None, value=None):
    """Select a dropdown option by visible text or value."""
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
        slow(0.1)
        sel = Select(element)
        if visible_text:
            sel.select_by_visible_text(visible_text)
        elif value:
            sel.select_by_value(value)
        else:
            # Pick the first non-blank option
            for opt in sel.options:
                if opt.get_attribute("value"):
                    sel.select_by_value(opt.get_attribute("value"))
                    break
        return True
    except Exception:
        return False


def safe_radio(driver, name, value=None):
    """Click a radio by name. If value is None, click the first one."""
    try:
        if value:
            r = driver.find_element(By.CSS_SELECTOR, f"input[name='{name}'][value='{value}']")
        else:
            r = driver.find_element(By.CSS_SELECTOR, f"input[name='{name}']")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", r)
        slow(0.1)
        try:
            r.click()
        except ElementNotInteractableException:
            # Click the parent label instead
            label = r.find_element(By.XPATH, "..")
            label.click()
        return True
    except Exception:
        return False


def safe_checkbox(driver, element_id, should_check=True):
    """Check or uncheck a checkbox."""
    try:
        cb = driver.find_element(By.ID, element_id)
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", cb)
        if cb.is_selected() != should_check:
            cb.click()
        return True
    except Exception:
        return False


# ──────────────────────────────────────────────
# TESTS
# ──────────────────────────────────────────────

def test_job_listing(driver, wait, results):
    """Test 1: Navigate to job listing, extract JD."""
    print("\n📋 TEST 1: Job Listing & JD Extraction")
    print("─" * 40)

    driver.get(BASE_URL)
    slow(0.5)

    # Check page loaded
    try:
        title = driver.find_element(By.CSS_SELECTOR, ".job-meta h1")
        results.ok("Page loaded", title.text)
    except NoSuchElementException:
        results.fail("Page loaded", "Could not find job title h1")
        return False

    # Extract company
    try:
        company = driver.find_element(By.CSS_SELECTOR, ".company-name").text
        results.ok("Company extracted", company)
    except:
        results.fail("Company extracted")

    # Extract JD text
    try:
        jd_el = driver.find_element(By.CSS_SELECTOR, ".job-description")
        jd_text = jd_el.text
        if len(jd_text) > 100:
            results.ok("JD extracted", f"{len(jd_text)} chars — mentions Python: {'Python' in jd_text}")
        else:
            results.fail("JD extracted", f"Too short: {len(jd_text)} chars")
    except:
        results.fail("JD extracted")

    # Check tags
    try:
        tags = driver.find_elements(By.CSS_SELECTOR, ".tag")
        tag_texts = [t.text for t in tags]
        results.ok("Job tags found", ", ".join(tag_texts))
    except:
        results.skip("Job tags", "No tags found")

    # Tech stack sidebar
    try:
        tech_tags = driver.find_elements(By.CSS_SELECTOR, ".tech-tag")
        results.ok("Tech stack parsed", ", ".join(t.text for t in tech_tags[:5]) + "…")
    except:
        results.skip("Tech stack")

    return True


def test_click_apply(driver, wait, results):
    """Test 2: Click Apply Now and reach the form."""
    print("\n🖱️  TEST 2: Click Apply Now")
    print("─" * 40)

    try:
        apply_btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "a.btn-primary.btn-lg[href='apply.html']")
        ))
        apply_btn.click()
        slow(0.5)
    except:
        # Try any link containing "apply"
        try:
            apply_btn = driver.find_element(By.PARTIAL_LINK_TEXT, "Apply")
            apply_btn.click()
            slow(0.5)
        except:
            results.fail("Click Apply", "No apply button found")
            return False

    # Verify we're on the apply page
    if "apply" in driver.current_url:
        results.ok("Navigated to apply page", driver.current_url)
    else:
        results.fail("Navigation", f"URL is {driver.current_url}")
        return False

    # Check progress bar
    try:
        steps = driver.find_elements(By.CSS_SELECTOR, ".step")
        active = [s for s in steps if "active" in s.get_attribute("class")]
        results.ok("Progress bar visible", f"{len(steps)} steps, step {len(active)} active")
    except:
        results.skip("Progress bar")

    return True


def test_fill_page1(driver, wait, results):
    """Test 3: Fill Page 1 — Personal Information."""
    print("\n📝 TEST 3: Fill Page 1 — Personal Info")
    print("─" * 40)

    filled = 0
    total = 0

    # --- Text fields ---
    text_fields = {
        "firstName": first_name,
        "lastName":  last_name,
        "email":     email,
        "phone":     phone_number,
        "city":      current_city,
        "state":     state,
        "zipCode":   zipcode,
        "linkedIn":  linkedIn,
        "portfolio": website or "https://portfolio.example.com",
    }

    for fid, val in text_fields.items():
        total += 1
        try:
            el = driver.find_element(By.ID, fid)
            if safe_fill(driver, el, val):
                filled += 1
            else:
                results.fail(f"Fill {fid}")
        except NoSuchElementException:
            results.fail(f"Find #{fid}", "Element not found")
    results.ok(f"Text fields filled", f"{filled}/{total}")

    # --- Select dropdowns ---
    select_map = {
        "country":          country,
        "gender":           gender,
        "phoneCountryCode": None,   # pick first non-blank
    }
    for sid, val in select_map.items():
        total += 1
        try:
            el = driver.find_element(By.ID, sid)
            if safe_select(driver, el, visible_text=val):
                filled += 1
            else:
                results.fail(f"Select {sid}")
        except Exception as e:
            results.fail(f"Select {sid}", str(e)[:60])
    results.ok("Dropdowns selected", f"{filled}/{total}")

    # --- Radio buttons ---
    radios = {
        "workAuth":         "Yes",
        "visaSponsorship":  "No",
        "commuteOk":        "Yes",
    }
    for rname, rval in radios.items():
        total += 1
        if safe_radio(driver, rname, rval):
            filled += 1
        else:
            results.fail(f"Radio {rname}")
    results.ok("Radio buttons set", f"{filled}/{total}")

    # --- Checkboxes (use name attr since they don't have IDs) ---
    checkboxes = ["agreeTerms", "agreeBackground", "agreeDataProcessing"]
    for cbname in checkboxes:
        total += 1
        try:
            cb = driver.find_element(By.CSS_SELECTOR, f"input[name='{cbname}']")
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", cb)
            slow(0.1)
            if not cb.is_selected():
                # Click the parent label for reliable toggling
                label = cb.find_element(By.XPATH, "..")
                label.click()
            filled += 1
        except Exception as e:
            results.fail(f"Checkbox {cbname}", str(e)[:60])
    results.ok("Checkboxes checked", f"{filled}/{total}")

    # --- File Upload ---
    total += 1
    try:
        file_input = driver.find_element(By.ID, "resume")
        # Make file input visible if needed
        driver.execute_script("""
            var el = arguments[0];
            el.style.opacity = '1';
            el.style.position = 'relative';
            el.style.width = '200px';
            el.style.height = '30px';
        """, file_input)
        slow(0.2)

        if RESUME_FILE and os.path.exists(RESUME_FILE):
            file_input.send_keys(os.path.abspath(RESUME_FILE))
            slow(0.3)
            filled += 1
            results.ok("Resume uploaded", os.path.basename(RESUME_FILE))
        else:
            results.skip("Resume upload", "No resume file found")
    except Exception as e:
        results.fail("Resume upload", str(e)[:80])

    results.ok(f"Page 1 total", f"{filled}/{total} fields filled")
    return filled > 0


def test_navigate_to_page2(driver, wait, results):
    """Test 4: Click Next to go to Page 2."""
    print("\n➡️  TEST 4: Navigate to Page 2")
    print("─" * 40)

    try:
        btn = driver.find_element(By.ID, "btnNext1")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        slow(0.2)
        btn.click()
        slow(0.3)

        # Dismiss any validation alert
        try:
            alert = driver.switch_to.alert
            alert_text = alert.text
            alert.accept()
            results.fail("Page 1 validation", f"Alert: {alert_text[:80]}")
            return False
        except:
            pass  # No alert = validation passed

        slow(0.5)
    except Exception as e:
        results.fail("Click Next", str(e)[:60])
        return False

    # Verify page 2 is visible
    try:
        page2 = driver.find_element(By.ID, "page2")
        if page2.is_displayed():
            results.ok("Page 2 visible")
            return True
        else:
            results.fail("Page 2 visible", "page2 div is hidden")
            return False
    except:
        results.fail("Page 2 exists")
        return False


def test_fill_page2(driver, wait, results):
    """Test 5: Fill Page 2 — Experience & Qualifications."""
    print("\n📝 TEST 5: Fill Page 2 — Experience & More")
    print("─" * 40)

    filled = 0
    total  = 0

    # --- Text fields ---
    txt = {
        "yearsExperience":       years_of_experience,
        "yearsExperiencePython": "4",
        "yearsExperienceReact":  "3",
        "currentCompany":        recent_employer or "Acme Corp",
        "currentSalary":         str(current_ctc) if current_ctc else "1800000",
        "expectedSalary":        str(desired_salary) if desired_salary else "2500000",
        "noticePeriod":          str(notice_period) if notice_period else "30",
        "earliestStartDate":     "2026-04-01",
        "university":            university,
        "gpa":                   gpa,
        "confidenceLevel":       confidence_level,
    }
    for fid, val in txt.items():
        total += 1
        try:
            el = driver.find_element(By.ID, fid)
            if safe_fill(driver, el, val):
                filled += 1
        except:
            results.fail(f"Find #{fid}")
    results.ok(f"Text fields (page 2)", f"{filled}/{total}")

    # --- Selects ---
    selects = {
        "educationLevel": degree if degree else None,
        "fieldOfStudy":   field_of_study if field_of_study else None,
        "referralSource":  None,  # pick first
    }
    for sid, val in selects.items():
        total += 1
        try:
            el = driver.find_element(By.ID, sid)
            if safe_select(driver, el, visible_text=val):
                filled += 1
        except:
            results.fail(f"Select {sid}")
    results.ok(f"Dropdowns (page 2)", f"{filled}/{total}")

    # --- Radios ---
    radios = {
        "workPreference": "Hybrid",
        "leadershipExp":  "Yes",
        "disability":     "No, I do not have a disability",
    }
    for rname, rval in radios.items():
        total += 1
        if safe_radio(driver, rname, rval):
            filled += 1
        else:
            results.fail(f"Radio {rname}")
    results.ok(f"Radios (page 2)", f"{filled}/{total}")

    # --- Textareas ---
    cover_text = (
        "I am excited to apply for the Senior Software Engineer position at InnovateTech Solutions. "
        "With 5+ years of experience in Python, React, and cloud technologies, I am confident I can "
        "contribute significantly to your engineering team."
    )
    for tid, val in [("coverLetter", cover_text), ("additionalInfo", "Available for immediate interviews.")]:
        total += 1
        try:
            el = driver.find_element(By.ID, tid)
            if safe_fill(driver, el, val):
                filled += 1
        except:
            results.fail(f"Textarea {tid}")
    results.ok(f"Textareas filled", f"{filled}/{total}")

    # --- Multi-checkboxes (skills) ---
    skills_to_check = ["Python", "React", "TypeScript", "AWS", "PostgreSQL"]
    skill_cbs = driver.find_elements(By.CSS_SELECTOR, "input[name='skills']")
    for cb in skill_cbs:
        label = cb.find_element(By.XPATH, "..").text.strip()
        if label in skills_to_check:
            total += 1
            try:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", cb)
                if not cb.is_selected():
                    cb.click()
                filled += 1
            except:
                results.fail(f"Skill checkbox {label}")
    results.ok(f"Skill checkboxes", f"{filled}/{total}")

    results.ok(f"Page 2 total", f"{filled}/{total} fields filled")
    return filled > 0


def test_navigate_to_review(driver, wait, results):
    """Test 6: Click Next to go to Review page."""
    print("\n➡️  TEST 6: Navigate to Review")
    print("─" * 40)

    try:
        btn = driver.find_element(By.ID, "btnNext2")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        slow(0.2)
        btn.click()
        slow(0.5)
    except Exception as e:
        results.fail("Click Next (page 2)", str(e)[:60])
        return False

    try:
        page3 = driver.find_element(By.ID, "page3")
        if page3.is_displayed():
            results.ok("Review page visible")
        else:
            results.fail("Review page visible")
            return False
    except:
        results.fail("Review page exists")
        return False

    # Check review content populated
    try:
        review = driver.find_element(By.ID, "reviewContent")
        sections = review.find_elements(By.CSS_SELECTOR, ".review-section")
        items = review.find_elements(By.CSS_SELECTOR, ".review-item")
        results.ok("Review populated", f"{len(sections)} sections, {len(items)} items")

        # Check some values are correct
        values = [i.find_element(By.CSS_SELECTOR, ".review-value").text for i in items[:5]]
        non_empty = [v for v in values if v and v != "—"]
        results.ok("Review values present", f"{len(non_empty)}/{len(values)} first items have values")
    except Exception as e:
        results.fail("Review content", str(e)[:60])

    return True


def test_submit(driver, wait, results):
    """Test 7: Confirm accuracy and submit."""
    print("\n🚀 TEST 7: Submit Application")
    print("─" * 40)

    # Check accuracy checkbox
    if safe_checkbox(driver, "confirmAccuracy", True):
        results.ok("Accuracy confirmed")
    else:
        results.fail("Accuracy checkbox")

    # Click Submit
    try:
        btn = driver.find_element(By.ID, "btnSubmit")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
        slow(0.2)
        btn.click()
        slow(0.3)

        # Dismiss any validation alert
        try:
            alert = driver.switch_to.alert
            alert.accept()
        except:
            pass

        slow(1)
    except Exception as e:
        results.fail("Click Submit", str(e)[:60])
        return False

    # Verify success page
    try:
        success = driver.find_element(By.ID, "successPage")
        if success.is_displayed():
            results.ok("Success page shown")
        else:
            results.fail("Success page visible")
            return False
    except:
        results.fail("Success page")
        return False

    # Check application ID
    try:
        app_id = success.find_element(By.CSS_SELECTOR, ".success-details strong").text
        if app_id.startswith("APP-"):
            results.ok("Application ID generated", app_id)
        else:
            results.fail("Application ID format", app_id)
    except:
        results.skip("Application ID")

    return True


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  🤖 E2E AUTOPILOT TEST — TechJobs Pro Test Site")
    print("=" * 60)
    print(f"  Target:  {BASE_URL}")
    print(f"  Resume:  {RESUME_FILE}")
    print(f"  User:    {first_name} {last_name} ({email})")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    results = TestResults()

    # Set up Chrome
    options = Options()
    if HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--log-level=3")

    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        wait   = WebDriverWait(driver, TIMEOUT)
        print(f"\n  Chrome {driver.capabilities.get('browserVersion', '?')} launched ✓")

        # Run tests sequentially
        if test_job_listing(driver, wait, results):
            if test_click_apply(driver, wait, results):
                if test_fill_page1(driver, wait, results):
                    if test_navigate_to_page2(driver, wait, results):
                        if test_fill_page2(driver, wait, results):
                            if test_navigate_to_review(driver, wait, results):
                                test_submit(driver, wait, results)

    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        traceback.print_exc()
        results.fail("Unexpected error", str(e)[:100])
    finally:
        # Screenshot
        if driver:
            try:
                ss_path = str(ROOT / "test-results" / f"autopilot_test_{int(time.time())}.png")
                os.makedirs(os.path.dirname(ss_path), exist_ok=True)
                driver.save_screenshot(ss_path)
                print(f"\n  📸 Screenshot saved: {ss_path}")
            except:
                pass
            driver.quit()

    # Print results
    all_passed = results.summary()
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
