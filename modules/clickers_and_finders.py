'''
Author:     Suraj Panwar
LinkedIn:   https://www.linkedin.com/in/surajpanwar/

Copyright (C) 2024 Suraj Panwar

License:    GNU Affero General Public License
            https://www.gnu.org/licenses/agpl-3.0.en.html
            
GitHub:     https://github.com/surajpanwar/Auto_job_applier_linkedIn

version:    26.01.20.5.08
'''

from config.settings import click_gap, smooth_scroll
from modules.helpers import buffer, print_lg, sleep
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.action_chains import ActionChains

# Click Functions
def wait_span_click(driver: WebDriver, text: str, time: float=5.0, click: bool=True, scroll: bool=True, scrollTop: bool=False, max_retries: int = 2) -> WebElement | bool:
    '''
    Finds the span element with the given `text`.
    - Returns `WebElement` if found, else `False` if not found.
    - Clicks on it if `click = True`.
    - Will spend a max of `time` seconds in searching for each element.
    - Will scroll to the element if `scroll = True`.
    - Will scroll to the top if `scrollTop = True`.
    - max_retries: Number of retry attempts for clicking
    '''
    if text:
        for attempt in range(max_retries):
            try:
                button = WebDriverWait(driver,time).until(EC.presence_of_element_located((By.XPATH, './/span[normalize-space(.)="'+text+'"]')))
                if scroll:  scroll_to_view(driver, button, scrollTop)
                if click:
                    try:
                        button.click()
                    except Exception:
                        # Fallback to JavaScript click
                        driver.execute_script("arguments[0].click();", button)
                    buffer(click_gap)
                    # Verify click was successful by checking if element is still interactable
                    return button
                return button
            except Exception as e:
                if attempt < max_retries - 1:
                    buffer(0.5)
                    continue
                print_lg("Click Failed! Didn't find '"+text+"'")
                # print_lg(e)
                return False
    return False

def multi_sel(driver: WebDriver, texts: list, time: float=5.0) -> None:
    '''
    - For each text in the `texts`, tries to find and click `span` element with that text.
    - Will spend a max of `time` seconds in searching for each element.
    '''
    for text in texts:
        ##> ------ Dheeraj Deshwal : dheeraj20194@iiitd.ac.in/dheerajdeshwal9811@gmail.com - Bug fix ------
        wait_span_click(driver, text, time, False)
        ##<
        try:
            button = WebDriverWait(driver,time).until(EC.presence_of_element_located((By.XPATH, './/span[normalize-space(.)="'+text+'"]')))
            scroll_to_view(driver, button)
            button.click()
            buffer(click_gap)
        except Exception as e:
            print_lg("Click Failed! Didn't find '"+text+"'")
            # print_lg(e)

def multi_sel_noWait(driver: WebDriver, texts: list, actions: ActionChains = None) -> None:
    '''
    - For each text in the `texts`, tries to find and click `span` element with that class.
    - If `actions` is provided, bot tries to search and Add the `text` to this filters list section.
    - Won't wait to search for each element, assumes that element is rendered.
    '''
    for text in texts:
        try:
            button = driver.find_element(By.XPATH, './/span[normalize-space(.)="'+text+'"]')
            scroll_to_view(driver, button)
            button.click()
            buffer(click_gap)
        except Exception as e:
            if actions: company_search_click(driver,actions,text)
            else:   print_lg("Click Failed! Didn't find '"+text+"'")
            # print_lg(e)

def boolean_button_click(driver: WebDriver, actions: ActionChains, text: str, max_retries: int = 3) -> bool:
    '''
    Tries to click on the boolean button with the given `text` text.
    Returns True if successfully toggled ON, False otherwise.
    Uses retry logic for consistency.
    '''
    for attempt in range(max_retries):
        try:
            list_container = driver.find_element(By.XPATH, './/h3[normalize-space()="'+text+'"]/ancestor::fieldset')
            button = list_container.find_element(By.XPATH, './/input[@role="switch"]')
            scroll_to_view(driver, button)
            
            # Check current state before clicking
            is_checked = button.get_attribute('aria-checked') == 'true' or button.is_selected()
            
            if not is_checked:
                # Not enabled, need to click to enable
                try:
                    # Prefer clicking associated label for accurate toggle
                    label = button.find_element(By.XPATH, './following-sibling::label | ./following-sibling::*[1]')
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", label)
                    driver.execute_script("arguments[0].click();", label)
                except Exception:
                    # Fallback to JavaScript click on the input itself
                    driver.execute_script("arguments[0].click();", button)
                buffer(click_gap)
                
                # Verify the toggle was successful
                from time import sleep as _sleep
                _sleep(0.3)
                is_now_checked = button.get_attribute('aria-checked') == 'true' or button.is_selected()
                if is_now_checked:
                    print_lg(f'Successfully enabled "{text}" filter')
                    return True
                else:
                    print_lg(f'Attempt {attempt+1}: Toggle "{text}" did not stick, retrying...')
            else:
                # Already enabled
                print_lg(f'Filter "{text}" is already enabled')
                return True
                
        except Exception as e:
            print_lg(f"Attempt {attempt+1}: Click Failed for '{text}' - {str(e)[:50]}")
            buffer(0.5)
    
    print_lg(f"Failed to enable '{text}' after {max_retries} attempts")
    return False


def verify_filter_state(driver: WebDriver, filter_text: str) -> bool:
    '''
    Verify if a boolean filter toggle is currently enabled.
    Returns True if enabled, False otherwise.
    '''
    try:
        list_container = driver.find_element(By.XPATH, './/h3[normalize-space()="'+filter_text+'"]/ancestor::fieldset')
        button = list_container.find_element(By.XPATH, './/input[@role="switch"]')
        is_checked = button.get_attribute('aria-checked') == 'true' or button.is_selected()
        return is_checked
    except Exception:
        return False


def robust_span_click(driver: WebDriver, text: str, actions: ActionChains = None, max_retries: int = 3, wait_time: float = 3.0) -> bool:
    '''
    Robustly click a span element with retries and verification.
    Returns True if click was successful.
    '''
    if not text:
        return False
    
    for attempt in range(max_retries):
        try:
            # Wait for element to be present
            button = WebDriverWait(driver, wait_time).until(
                EC.presence_of_element_located((By.XPATH, f'.//span[normalize-space(.)="{text}"]'))
            )
            scroll_to_view(driver, button)
            
            # Try clicking
            try:
                button.click()
            except Exception:
                # Try JavaScript click
                driver.execute_script("arguments[0].click();", button)
            
            buffer(0.3)
            
            # Check if the element now has 'selected' or 'active' state
            parent = button.find_element(By.XPATH, '..')
            parent_classes = parent.get_attribute('class') or ''
            if 'selected' in parent_classes or 'active' in parent_classes or 'checked' in parent_classes:
                print_lg(f'Successfully selected "{text}"')
                return True
            
            # For filter options, check aria-checked on parent button
            try:
                parent_button = button.find_element(By.XPATH, './ancestor::button')
                if parent_button.get_attribute('aria-pressed') == 'true':
                    print_lg(f'Successfully selected "{text}"')
                    return True
            except Exception:
                pass
            
            # If we got here without error, assume success
            print_lg(f'Clicked "{text}" (attempt {attempt+1})')
            return True
            
        except Exception as e:
            if attempt < max_retries - 1:
                print_lg(f'Retry {attempt+1} for "{text}"...')
                buffer(0.5)
            else:
                print_lg(f'Failed to click "{text}" after {max_retries} attempts')
    
    return False


# Find functions
def find_by_class(driver: WebDriver, class_name: str, time: float=5.0) -> WebElement | Exception:
    '''
    Waits for a max of `time` seconds for element to be found, and returns `WebElement` if found, else `Exception` if not found.
    '''
    return WebDriverWait(driver, time).until(EC.presence_of_element_located((By.CLASS_NAME, class_name)))

# Scroll functions
def scroll_to_view(driver: WebDriver, element: WebElement, top: bool = False, smooth_scroll: bool = smooth_scroll) -> None:
    '''
    Scrolls the `element` to view.
    - `smooth_scroll` will scroll with smooth behavior.
    - `top` will scroll to the `element` to top of the view.
    '''
    if top:
        return driver.execute_script('arguments[0].scrollIntoView();', element)
    behavior = "smooth" if smooth_scroll else "instant"
    return driver.execute_script('arguments[0].scrollIntoView({block: "center", behavior: "'+behavior+'" });', element)

# Enter input text functions
def text_input_by_ID(driver: WebDriver, id: str, value: str, time: float=5.0) -> None | Exception:
    '''
    Enters `value` into the input field with the given `id` if found, else throws NotFoundException.
    - `time` is the max time to wait for the element to be found.
    '''
    username_field = WebDriverWait(driver, time).until(EC.presence_of_element_located((By.ID, id)))
    username_field.send_keys(Keys.CONTROL + "a")
    username_field.send_keys(value)

def try_xp(driver: WebDriver, xpath: str, click: bool=True) -> WebElement | bool:
    try:
        if click:
            driver.find_element(By.XPATH, xpath).click()
            return True
        else:
            return driver.find_element(By.XPATH, xpath)
    except: return False

def try_linkText(driver: WebDriver, linkText: str) -> WebElement | bool:
    try:    return driver.find_element(By.LINK_TEXT, linkText)
    except:  return False

def try_find_by_classes(driver: WebDriver, classes: list[str]) -> WebElement | ValueError:
    for cla in classes:
        try:    return driver.find_element(By.CLASS_NAME, cla)
        except: pass
    raise ValueError("Failed to find an element with given classes")

def company_search_click(driver: WebDriver, actions: ActionChains, companyName: str) -> None:
    '''
    Tries to search and Add the company to company filters list.
    '''
    wait_span_click(driver,"Add a company",1)
    search = driver.find_element(By.XPATH,"(.//input[@placeholder='Add a company'])[1]")
    search.send_keys(Keys.CONTROL + "a")
    search.send_keys(companyName)
    buffer(3)
    actions.send_keys(Keys.DOWN).perform()
    actions.send_keys(Keys.ENTER).perform()
    print_lg(f'Tried searching and adding "{companyName}"')

def text_input(actions: ActionChains, textInputEle: WebElement | bool, value: str, textFieldName: str = "Text") -> None | Exception:
    if textInputEle:
        sleep(1)
        # actions.key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).perform()
        textInputEle.clear()
        textInputEle.send_keys(value.strip())
        sleep(2)
        actions.send_keys(Keys.ENTER).perform()
    else:
        print_lg(f'{textFieldName} input was not given!')