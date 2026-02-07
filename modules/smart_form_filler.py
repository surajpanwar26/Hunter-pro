"""
Smart Form Filler v2.0 - A modern, fast, and reliable LinkedIn Easy Apply form handler.

Architecture:
1. PageAnalyzer - Scans and understands the current page state
2. ElementDetector - Finds and classifies form elements
3. AnswerEngine - Determines the best answer for each question
4. FormExecutor - Fills forms quickly and reliably

Design Principles:
- Single Responsibility: Each class does one thing well
- Fail Fast: Detect issues early, recover quickly  
- Parallel Detection: Analyze multiple elements simultaneously
- Minimal Waits: Only wait when absolutely necessary
- Smart Caching: Remember answers and page patterns
"""

from __future__ import annotations
import re
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import (
    StaleElementReferenceException, 
    NoSuchElementException,
    ElementNotInteractableException,
)


class ElementType(Enum):
    """Types of form elements we can handle."""
    TEXT_INPUT = auto()
    TEXTAREA = auto()
    SELECT_DROPDOWN = auto()
    RADIO_GROUP = auto()
    CHECKBOX = auto()
    FILE_UPLOAD = auto()
    DATE_PICKER = auto()
    AUTOCOMPLETE = auto()
    UNKNOWN = auto()


class PageState(Enum):
    """Current state of the Easy Apply modal."""
    LOADING = auto()
    FORM_READY = auto()
    UPLOADING = auto()
    SUBMITTING = auto()
    SUCCESS = auto()
    ERROR = auto()
    CLOSED = auto()


@dataclass
class FormElement:
    """Represents a detected form element with all its properties."""
    element: WebElement
    element_type: ElementType
    label: str
    label_lower: str  # Pre-computed for fast matching
    name: str
    is_required: bool
    current_value: str
    options: list[str] = field(default_factory=list)
    container: Optional[WebElement] = None
    
    def __hash__(self):
        return hash((self.label, self.element_type.name))


@dataclass  
class FormPage:
    """Represents a single page/step in the Easy Apply flow."""
    elements: list[FormElement]
    has_next: bool
    has_submit: bool
    has_review: bool
    has_upload: bool
    page_title: str = ""
    error_message: str = ""


class PageAnalyzer:
    """
    Analyzes the LinkedIn Easy Apply modal to understand its current state.
    Uses fast, parallel detection methods.
    """
    
    # LinkedIn 2024/2025 selectors - kept up to date
    SELECTORS = {
        'modal': 'jobs-easy-apply-modal',
        'form_container': '.jobs-easy-apply-content',
        'next_button': "button[aria-label='Continue to next step']",
        'review_button': "button[aria-label='Review your application']",
        'submit_button': "button[aria-label='Submit application']",
        'close_button': "button[aria-label='Dismiss']",
        'error_message': '.artdeco-inline-feedback--error',
        'progress_indicator': '.jobs-easy-apply-progress-indicator',
        'file_upload': "input[type='file']",
        'upload_button': "button[aria-label*='Upload']",
    }
    
    def __init__(self, driver: WebDriver):
        self.driver = driver
        self._cached_modal = None
        self._cache_time = 0
        
    def get_modal(self, refresh: bool = False) -> Optional[WebElement]:
        """Get the Easy Apply modal, with caching."""
        now = time.time()
        if not refresh and self._cached_modal and (now - self._cache_time) < 1.0:
            try:
                # Verify cached element is still valid
                _ = self._cached_modal.is_displayed()
                return self._cached_modal
            except StaleElementReferenceException:
                pass
        
        try:
            modal = self.driver.find_element(By.CLASS_NAME, self.SELECTORS['modal'])
            self._cached_modal = modal
            self._cache_time = now
            return modal
        except NoSuchElementException:
            self._cached_modal = None
            return None
    
    def get_page_state(self) -> PageState:
        """Quickly determine the current page state."""
        modal = self.get_modal()
        if not modal:
            return PageState.CLOSED
            
        try:
            # Check for loading indicators
            if self._has_loading_indicator(modal):
                return PageState.LOADING
                
            # Check for success state
            if self._has_success_indicator():
                return PageState.SUCCESS
                
            # Check for errors
            if self._has_error_message(modal):
                return PageState.ERROR
                
            return PageState.FORM_READY
        except StaleElementReferenceException:
            return PageState.CLOSED
    
    def analyze_current_page(self) -> FormPage:
        """Analyze the current form page and return all elements."""
        modal = self.get_modal(refresh=True)
        if not modal:
            return FormPage(elements=[], has_next=False, has_submit=False, 
                          has_review=False, has_upload=False)
        
        elements = self._detect_form_elements(modal)
        
        return FormPage(
            elements=elements,
            has_next=self._has_button(modal, 'next_button'),
            has_submit=self._has_button(modal, 'submit_button'),
            has_review=self._has_button(modal, 'review_button'),
            has_upload=self._has_upload_section(modal),
            page_title=self._get_page_title(modal),
            error_message=self._get_error_message(modal),
        )
    
    def _detect_form_elements(self, modal: WebElement) -> list[FormElement]:
        """Detect all form elements on the current page."""
        elements = []
        
        # Detect text inputs
        for input_el in modal.find_elements(By.CSS_SELECTOR, "input[type='text'], input[type='email'], input[type='tel'], input[type='number']"):
            if input_el.is_displayed():
                elements.append(self._create_form_element(input_el, ElementType.TEXT_INPUT))
        
        # Detect textareas
        for textarea in modal.find_elements(By.TAG_NAME, "textarea"):
            if textarea.is_displayed():
                elements.append(self._create_form_element(textarea, ElementType.TEXTAREA))
        
        # Detect select dropdowns
        for select in modal.find_elements(By.TAG_NAME, "select"):
            if select.is_displayed():
                elements.append(self._create_form_element(select, ElementType.SELECT_DROPDOWN))
        
        # Detect radio groups
        radio_groups = self._detect_radio_groups(modal)
        elements.extend(radio_groups)
        
        # Detect checkboxes
        for checkbox in modal.find_elements(By.CSS_SELECTOR, "input[type='checkbox']"):
            if checkbox.is_displayed():
                elements.append(self._create_form_element(checkbox, ElementType.CHECKBOX))
        
        # Detect file uploads
        for file_input in modal.find_elements(By.CSS_SELECTOR, "input[type='file']"):
            elements.append(self._create_form_element(file_input, ElementType.FILE_UPLOAD))
        
        return elements
    
    def _create_form_element(self, element: WebElement, elem_type: ElementType) -> FormElement:
        """Create a FormElement from a WebElement."""
        label = self._find_label_for_element(element)
        options = []
        
        if elem_type == ElementType.SELECT_DROPDOWN:
            try:
                select = Select(element)
                options = [opt.text for opt in select.options if opt.text.strip()]
            except Exception:
                pass
        
        return FormElement(
            element=element,
            element_type=elem_type,
            label=label,
            label_lower=label.lower(),
            name=element.get_attribute('name') or '',
            is_required=self._is_required(element),
            current_value=element.get_attribute('value') or '',
            options=options,
        )
    
    def _find_label_for_element(self, element: WebElement) -> str:
        """Find the label text for a form element."""
        # Try aria-label first
        aria_label = element.get_attribute('aria-label')
        if aria_label:
            return aria_label
        
        # Try placeholder
        placeholder = element.get_attribute('placeholder')
        if placeholder:
            return placeholder
        
        # Try finding associated label
        elem_id = element.get_attribute('id')
        if elem_id:
            try:
                label = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{elem_id}']")
                return label.text
            except Exception:
                pass
        
        # Try parent container text
        try:
            parent = element.find_element(By.XPATH, "./..")
            label_elem = parent.find_element(By.TAG_NAME, "label")
            return label_elem.text
        except Exception:
            pass
        
        # Try finding nearby legend or span
        try:
            container = element.find_element(By.XPATH, "./ancestor::fieldset | ./ancestor::div[contains(@class, 'form')]")
            legend = container.find_element(By.CSS_SELECTOR, "legend, .fb-dash-form-element__label")
            return legend.text
        except Exception:
            pass
        
        return ""
    
    def _is_required(self, element: WebElement) -> bool:
        """Check if an element is required."""
        if element.get_attribute('required'):
            return True
        if element.get_attribute('aria-required') == 'true':
            return True
        # Check for asterisk in label
        try:
            parent = element.find_element(By.XPATH, "./..")
            if '*' in parent.text:
                return True
        except (NoSuchElementException, StaleElementReferenceException):
            pass
        return False
    
    def _detect_radio_groups(self, modal: WebElement) -> list[FormElement]:
        """Detect radio button groups."""
        groups = {}
        for radio in modal.find_elements(By.CSS_SELECTOR, "input[type='radio']"):
            name = radio.get_attribute('name')
            if name:
                if name not in groups:
                    groups[name] = []
                groups[name].append(radio)
        
        elements = []
        for name, radios in groups.items():
            if radios:
                # Get the label for the group
                try:
                    fieldset = radios[0].find_element(By.XPATH, "./ancestor::fieldset")
                    legend = fieldset.find_element(By.TAG_NAME, "legend")
                    label = legend.text
                except (NoSuchElementException, StaleElementReferenceException):
                    label = name
                
                # Get options
                options = []
                for radio in radios:
                    try:
                        opt_label = radio.find_element(By.XPATH, "./following-sibling::label | ./parent::label")
                        options.append(opt_label.text)
                    except (NoSuchElementException, StaleElementReferenceException):
                        options.append(radio.get_attribute('value') or '')
                
                elements.append(FormElement(
                    element=radios[0],  # First radio for reference
                    element_type=ElementType.RADIO_GROUP,
                    label=label,
                    label_lower=label.lower(),
                    name=name,
                    is_required=any(r.get_attribute('required') for r in radios),
                    current_value='',
                    options=options,
                ))
        
        return elements
    
    def _has_loading_indicator(self, modal: WebElement) -> bool:
        """Check if page is loading."""
        try:
            spinners = modal.find_elements(By.CSS_SELECTOR, ".artdeco-spinner, .loading-indicator")
            return any(s.is_displayed() for s in spinners)
        except (NoSuchElementException, StaleElementReferenceException):
            return False
    
    def _has_success_indicator(self) -> bool:
        """Check if application was submitted successfully."""
        try:
            success_elements = self.driver.find_elements(By.XPATH, 
                "//*[contains(text(), 'Application sent') or contains(text(), 'applied')]")
            return any(el.is_displayed() for el in success_elements)
        except (NoSuchElementException, StaleElementReferenceException):
            return False
    
    def _has_error_message(self, modal: WebElement) -> bool:
        """Check for error messages."""
        try:
            errors = modal.find_elements(By.CSS_SELECTOR, self.SELECTORS['error_message'])
            return any(e.is_displayed() for e in errors)
        except:
            return False
    
    def _has_button(self, modal: WebElement, button_key: str) -> bool:
        """Check if a specific button exists."""
        try:
            selector = self.SELECTORS[button_key]
            buttons = modal.find_elements(By.CSS_SELECTOR, selector)
            return any(b.is_displayed() and b.is_enabled() for b in buttons)
        except:
            return False
    
    def _has_upload_section(self, modal: WebElement) -> bool:
        """Check if current page has file upload."""
        try:
            uploads = modal.find_elements(By.CSS_SELECTOR, "input[type='file']")
            return len(uploads) > 0
        except:
            return False
    
    def _get_page_title(self, modal: WebElement) -> str:
        """Get the current page/section title."""
        try:
            title = modal.find_element(By.CSS_SELECTOR, "h3.t-16, .jobs-easy-apply-modal__header")
            return title.text
        except:
            return ""
    
    def _get_error_message(self, modal: WebElement) -> str:
        """Get error message text if present."""
        try:
            error = modal.find_element(By.CSS_SELECTOR, self.SELECTORS['error_message'])
            if error.is_displayed():
                return error.text
        except:
            pass
        return ""


class AnswerEngine:
    """
    Determines the best answer for form questions.
    Uses pattern matching, learned answers, and AI fallback.
    """
    
    # Common patterns mapped to config keys
    PATTERNS = {
        # Contact info
        (r'first\s*name', 'first_name'),
        (r'last\s*name', 'last_name'),
        (r'full\s*name', 'full_name'),
        (r'email', 'email'),
        (r'phone|mobile|cell', 'phone_number'),
        
        # Location
        (r'city', 'city'),
        (r'state|province', 'state'),
        (r'country', 'country'),
        (r'zip|postal', 'zipcode'),
        (r'address|street', 'street'),
        
        # Professional
        (r'linkedin\s*(url|profile)?', 'linkedin_url'),
        (r'website|portfolio', 'website'),
        (r'years?\s*(of)?\s*experience', 'years_of_experience'),
        (r'current\s*(employer|company)', 'current_employer'),
        (r'salary|compensation|pay', 'desired_salary'),
        (r'notice\s*period', 'notice_period'),
        
        # Work authorization  
        (r'authorized|legally\s*allowed|right\s*to\s*work', 'work_authorized'),
        (r'sponsor|visa', 'visa_sponsorship'),
        (r'citizen', 'citizenship'),
        
        # Demographics (EEO)
        (r'gender', 'gender'),
        (r'race|ethnicity', 'ethnicity'),
        (r'veteran', 'veteran_status'),
        (r'disability|disabled', 'disability_status'),
        
        # Other
        (r'cover\s*letter', 'cover_letter'),
        (r'summary|objective|about', 'summary'),
        (r'headline', 'linkedin_headline'),
    }
    
    # Yes/No question patterns
    YES_NO_PATTERNS = {
        'yes': [
            r'authorized.*work',
            r'legal.*work', 
            r'right.*work',
            r'citizen',
            r'18\s*years',
            r'background\s*check',
            r'consent',
            r'agree',
        ],
        'no': [
            r'sponsor.*visa',
            r'require.*sponsor',
            r'need.*visa',
            r'disability',
            r'veteran',
        ],
    }
    
    def __init__(self, user_config: dict, learned_answers: dict | None = None):
        self.config = user_config
        self.learned = learned_answers or {}
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for speed."""
        self._compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), key)
            for pattern, key in self.PATTERNS
        ]
        self._yes_patterns = [re.compile(p, re.IGNORECASE) for p in self.YES_NO_PATTERNS['yes']]
        self._no_patterns = [re.compile(p, re.IGNORECASE) for p in self.YES_NO_PATTERNS['no']]
    
    def get_answer(self, element: FormElement) -> tuple[str, float]:
        """
        Get the best answer for a form element.
        Returns (answer, confidence) where confidence is 0-1.
        """
        label = element.label_lower
        
        # Check learned answers first (highest confidence)
        if label in self.learned:
            return self.learned[label], 1.0
        
        # Try pattern matching
        for pattern, config_key in self._compiled_patterns:
            if pattern.search(label):
                value = self.config.get(config_key)
                if value:
                    return str(value), 0.9
        
        # Handle dropdowns with options
        if element.element_type == ElementType.SELECT_DROPDOWN and element.options:
            return self._match_dropdown_option(element), 0.8
        
        # Handle radio groups
        if element.element_type == ElementType.RADIO_GROUP and element.options:
            return self._match_radio_option(element), 0.8
        
        # Handle yes/no questions
        yes_no_answer = self._check_yes_no(label)
        if yes_no_answer:
            return yes_no_answer, 0.85
        
        # Handle checkboxes (usually accept/agree)
        if element.element_type == ElementType.CHECKBOX:
            if any(word in label for word in ['agree', 'accept', 'consent', 'confirm']):
                return 'yes', 0.9
        
        # Low confidence fallback
        return '', 0.0
    
    def _match_dropdown_option(self, element: FormElement) -> str:
        """Find the best matching option in a dropdown."""
        label = element.label_lower
        options = element.options
        
        # Check for specific patterns
        if 'country' in label:
            return self._find_option(options, [self.config.get('country', ''), 'united states', 'usa', 'us'])
        if 'state' in label or 'province' in label:
            return self._find_option(options, [self.config.get('state', '')])
        if 'gender' in label:
            return self._find_option(options, [self.config.get('gender', ''), 'prefer not', 'decline'])
        if 'experience' in label or 'years' in label:
            yoe = self.config.get('years_of_experience', '5')
            return self._find_experience_option(options, yoe)
        
        # Default: first non-empty option
        for opt in options:
            if opt.strip() and opt.lower() not in ['select', 'choose', '--']:
                return opt
        return ''
    
    def _match_radio_option(self, element: FormElement) -> str:
        """Find the best matching radio option."""
        label = element.label_lower
        options = element.options
        
        # Yes/No type questions
        yes_no = self._check_yes_no(label)
        if yes_no:
            for opt in options:
                if yes_no.lower() in opt.lower():
                    return opt
        
        # Default: first option
        return options[0] if options else ''
    
    def _find_option(self, options: list[str], preferences: list[str]) -> str:
        """Find an option matching any preference."""
        for pref in preferences:
            if not pref:
                continue
            pref_lower = pref.lower()
            for opt in options:
                if pref_lower in opt.lower() or opt.lower() in pref_lower:
                    return opt
        return options[0] if options else ''
    
    def _find_experience_option(self, options: list[str], years: str) -> str:
        """Find the best matching experience range option."""
        try:
            yoe = int(years)
        except:
            yoe = 5
        
        for opt in options:
            # Extract numbers from option
            numbers = re.findall(r'\d+', opt)
            if len(numbers) == 2:
                low, high = int(numbers[0]), int(numbers[1])
                if low <= yoe <= high:
                    return opt
            elif len(numbers) == 1:
                num = int(numbers[0])
                if '+' in opt and yoe >= num:
                    return opt
                elif yoe == num:
                    return opt
        
        return options[-1] if options else ''  # Last option usually covers highest range
    
    def _check_yes_no(self, label: str) -> str:
        """Check if label matches yes/no patterns."""
        for pattern in self._yes_patterns:
            if pattern.search(label):
                return 'Yes'
        for pattern in self._no_patterns:
            if pattern.search(label):
                return 'No'
        return ''
    
    def learn_answer(self, label: str, answer: str):
        """Learn a new answer for future use."""
        self.learned[label.lower()] = answer


class FormExecutor:
    """
    Fills form elements quickly and reliably.
    Handles edge cases and recovery.
    """
    
    def __init__(self, driver: WebDriver, answer_engine: AnswerEngine):
        self.driver = driver
        self.answers = answer_engine
        self.filled_count = 0
        self.error_count = 0
    
    def fill_page(self, page: FormPage, resume_path: str | None = None) -> bool:
        """
        Fill all elements on a form page.
        Returns True if all required fields were filled successfully.
        """
        success = True
        
        for element in page.elements:
            try:
                if element.element_type == ElementType.FILE_UPLOAD:
                    if resume_path:
                        self._fill_file(element, resume_path)
                else:
                    answer, confidence = self.answers.get_answer(element)
                    if answer and confidence > 0.5:
                        self._fill_element(element, answer)
                    elif element.is_required:
                        success = False
                        self.error_count += 1
            except Exception as e:
                if element.is_required:
                    success = False
                    self.error_count += 1
        
        return success
    
    def _fill_element(self, element: FormElement, value: str):
        """Fill a single form element with the given value."""
        elem = element.element
        elem_type = element.element_type
        
        try:
            # Scroll element into view
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
            time.sleep(0.1)
            
            if elem_type == ElementType.TEXT_INPUT:
                self._fill_text(elem, value)
            elif elem_type == ElementType.TEXTAREA:
                self._fill_text(elem, value)
            elif elem_type == ElementType.SELECT_DROPDOWN:
                self._fill_select(elem, value)
            elif elem_type == ElementType.RADIO_GROUP:
                self._fill_radio(element, value)
            elif elem_type == ElementType.CHECKBOX:
                self._fill_checkbox(elem, value)
            
            self.filled_count += 1
            
        except StaleElementReferenceException:
            pass  # Element changed, skip
        except ElementNotInteractableException:
            # Try JavaScript fallback
            self._js_fill(elem, value)
    
    def _fill_text(self, elem: WebElement, value: str):
        """Fill a text input or textarea."""
        elem.click()
        time.sleep(0.05)
        elem.clear()
        elem.send_keys(value)
    
    def _fill_select(self, elem: WebElement, value: str):
        """Fill a select dropdown."""
        select = Select(elem)
        try:
            select.select_by_visible_text(value)
        except:
            # Try partial match
            for option in select.options:
                if value.lower() in option.text.lower():
                    select.select_by_visible_text(option.text)
                    return
            # Fallback: select first non-empty
            for option in select.options:
                if option.text.strip():
                    select.select_by_visible_text(option.text)
                    return
    
    def _fill_radio(self, element: FormElement, value: str):
        """Fill a radio button group."""
        # Find the radio with matching value/label
        name = element.name
        radios = self.driver.find_elements(By.CSS_SELECTOR, f"input[type='radio'][name='{name}']")
        
        for radio in radios:
            try:
                label = radio.find_element(By.XPATH, "./following-sibling::label | ./parent::label")
                if value.lower() in label.text.lower():
                    if not radio.is_selected():
                        radio.click()
                    return
            except:
                continue
        
        # Fallback: click first unchecked radio
        for radio in radios:
            if not radio.is_selected():
                radio.click()
                return
    
    def _fill_checkbox(self, elem: WebElement, value: str):
        """Fill a checkbox."""
        should_check = value.lower() in ['yes', 'true', '1', 'checked']
        is_checked = elem.is_selected()
        
        if should_check != is_checked:
            elem.click()
    
    def _fill_file(self, element: FormElement, file_path: str):
        """Upload a file."""
        import os
        
        if not os.path.exists(file_path):
            return
        
        elem = element.element
        
        # LinkedIn 2024/2025 often requires clicking an "Upload resume" button first
        try:
            container = elem.find_element(By.XPATH, "./ancestor::div[contains(@class, 'jobs-document-upload')]")
            upload_btn = container.find_element(By.CSS_SELECTOR, "button[aria-label*='Upload']")
            if not upload_btn:
                # Fallback: try XPath for text-based matching
                upload_btn = container.find_element(By.XPATH, ".//button[contains(text(), 'Upload')]")
            if upload_btn.is_displayed():
                upload_btn.click()
                time.sleep(0.5)
        except:
            pass
        
        # Make file input visible and send file
        self.driver.execute_script("""
            arguments[0].style.display = 'block';
            arguments[0].style.visibility = 'visible';
            arguments[0].style.opacity = '1';
        """, elem)
        
        elem.send_keys(os.path.abspath(file_path))
        time.sleep(0.5)
        
        # Dismiss any popups (Deloitte, etc.)
        self._dismiss_upload_popups()
    
    def _dismiss_upload_popups(self):
        """Dismiss popups that appear after file upload."""
        # CSS selectors for aria-label based buttons
        css_selectors = [
            "button[aria-label='Dismiss']",
            "button[aria-label='Got it']",
        ]
        # XPath selectors for text-based buttons
        xpath_selectors = [
            "//button[contains(text(), 'OK')]",
            "//button[contains(text(), 'Done')]",
        ]
        
        for selector in css_selectors:
            try:
                buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for btn in buttons:
                    if btn.is_displayed():
                        btn.click()
                        time.sleep(0.2)
            except Exception:
                continue
        
        for xpath in xpath_selectors:
            try:
                buttons = self.driver.find_elements(By.XPATH, xpath)
                for btn in buttons:
                    if btn.is_displayed():
                        btn.click()
                        time.sleep(0.2)
            except Exception:
                continue
    
    def _js_fill(self, elem: WebElement, value: str):
        """Fill element using JavaScript as fallback."""
        self.driver.execute_script("""
            arguments[0].value = arguments[1];
            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
        """, elem, value)


class SmartFormFiller:
    """
    Main class that orchestrates the form filling process.
    Coordinates PageAnalyzer, AnswerEngine, and FormExecutor.
    """
    
    def __init__(self, driver: WebDriver, user_config: dict, fast_mode: bool = True):
        self.driver = driver
        self.config = user_config
        self.fast_mode = fast_mode
        
        self.analyzer = PageAnalyzer(driver)
        self.answers = AnswerEngine(user_config)
        self.executor = FormExecutor(driver, self.answers)
        
        self._pages_filled = 0
        self._total_fields = 0
    
    def fill_application(self, resume_path: str | None = None, max_pages: int = 10) -> bool:
        """
        Fill the entire Easy Apply application.
        Returns True if application was submitted successfully.
        """
        for page_num in range(max_pages):
            # Wait for page to be ready
            if not self._wait_for_page_ready():
                return False
            
            # Analyze current page
            page = self.analyzer.analyze_current_page()
            
            if not page.elements and not page.has_next and not page.has_submit:
                # Check if we're done
                if self.analyzer.get_page_state() == PageState.SUCCESS:
                    return True
                return False
            
            # Fill the page
            self.executor.fill_page(page, resume_path)
            self._pages_filled += 1
            self._total_fields += len(page.elements)
            
            # Navigate to next step
            if page.has_submit:
                return self._click_submit()
            elif page.has_review:
                if not self._click_review():
                    return False
            elif page.has_next:
                if not self._click_next():
                    return False
            else:
                # No navigation button found - might be done
                break
            
            # Small delay between pages
            time.sleep(0.3 if self.fast_mode else 0.5)
        
        return False
    
    def fill_current_page(self, resume_path: str | None = None) -> bool:
        """Fill only the current page without navigating."""
        if not self._wait_for_page_ready():
            return False
        
        page = self.analyzer.analyze_current_page()
        return self.executor.fill_page(page, resume_path)
    
    def _wait_for_page_ready(self, timeout: float = 5.0) -> bool:
        """Wait for the page to be ready for interaction."""
        start = time.time()
        while time.time() - start < timeout:
            state = self.analyzer.get_page_state()
            if state == PageState.FORM_READY:
                return True
            if state in (PageState.CLOSED, PageState.SUCCESS):
                return False
            time.sleep(0.1)
        return False
    
    def _click_next(self) -> bool:
        """Click the Next button."""
        return self._click_button("button[aria-label='Continue to next step']")
    
    def _click_review(self) -> bool:
        """Click the Review button."""
        return self._click_button("button[aria-label='Review your application']")
    
    def _click_submit(self) -> bool:
        """Click the Submit button."""
        return self._click_button("button[aria-label='Submit application']")
    
    def _click_button(self, selector: str) -> bool:
        """Click a button by selector."""
        try:
            modal = self.analyzer.get_modal()
            if not modal:
                return False
            
            button = modal.find_element(By.CSS_SELECTOR, selector)
            if button.is_displayed() and button.is_enabled():
                button.click()
                return True
        except:
            pass
        return False
    
    @property
    def stats(self) -> dict:
        """Get filling statistics."""
        return {
            'pages_filled': self._pages_filled,
            'total_fields': self._total_fields,
            'fields_filled': self.executor.filled_count,
            'errors': self.executor.error_count,
        }


# Factory function to create a SmartFormFiller with config from settings
def create_smart_filler(driver: WebDriver) -> SmartFormFiller:
    """Create a SmartFormFiller with configuration from settings files."""
    from config.personals import (
        first_name, middle_name, last_name, 
        phone_number, current_city, state, country, zipcode, street,
        linkedIn, website, years_of_experience,
        require_visa, gender, disability_status, veteran_status,
        linkedin_headline, linkedin_summary, cover_letter,
        notice_period, desired_salary, current_ctc,
        us_citizenship, recent_employer, confidence_level
    )
    from config.secrets import username as email
    
    full_name = f"{first_name} {middle_name} {last_name}".replace("  ", " ").strip()
    
    user_config = {
        'first_name': first_name,
        'middle_name': middle_name,
        'last_name': last_name,
        'full_name': full_name,
        'email': email,
        'phone_number': phone_number,
        'city': current_city,
        'state': state,
        'country': country,
        'zipcode': zipcode,
        'street': street,
        'linkedin_url': linkedIn,
        'website': website,
        'years_of_experience': years_of_experience,
        'work_authorized': 'Yes',  # Work authorization is independent of citizenship (H-1B, Green Card, EAD holders are authorized)
        'visa_sponsorship': require_visa,
        'gender': gender,
        'disability_status': disability_status,
        'veteran_status': veteran_status,
        'citizenship': us_citizenship,
        'linkedin_headline': linkedin_headline,
        'summary': linkedin_summary,
        'cover_letter': cover_letter,
        'notice_period': notice_period,
        'desired_salary': desired_salary,
        'current_salary': current_ctc,
        'current_employer': recent_employer,
        'confidence_level': confidence_level,
        'referral_source': 'LinkedIn',
    }
    
    # Get fast mode from settings
    try:
        from config.settings import form_fill_fast_mode
        fast_mode = form_fill_fast_mode
    except:
        fast_mode = True
    
    return SmartFormFiller(driver, user_config, fast_mode)
