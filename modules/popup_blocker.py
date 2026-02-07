"""
Popup Blocker Module for LinkedIn Job Hunter Pro
Author: Suraj Panwar

This module handles dismissing various popups that appear during LinkedIn automation,
including Deloitte's custom popup and other common interruptions.
"""

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException, 
    TimeoutException, 
    ElementClickInterceptedException,
    StaleElementReferenceException
)

def _is_easy_apply_open(driver) -> bool:
    """Return True if any Easy Apply modal is currently open."""
    try:
        selectors = [
            ".jobs-easy-apply-modal",
            ".jobs-easy-apply-modal__content",
            ".jobs-easy-apply-content",
            "[data-test-easy-apply-modal]",
            "[class*='jobs-easy-apply']",
        ]
        for selector in selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if any(el.is_displayed() for el in elements):
                    return True
            except Exception:
                continue
    except Exception:
        return False
    return False


class PopupBlocker:
    """Class to manage and dismiss various popups during LinkedIn automation."""
    
    def __init__(self, driver):
        """Initialize the popup blocker with a Selenium WebDriver instance."""
        self.driver = driver
        self.blocked_count = 0
        
        # Common popup selectors to dismiss
        # CRITICAL: Do NOT include selectors that match Easy Apply modal's X/dismiss button!
        # "button.artdeco-modal__dismiss" and "button[aria-label='Dismiss']" are REMOVED
        # because they match the Easy Apply modal's close button.
        self.popup_selectors = [
            # LinkedIn messaging overlays (safe to dismiss)
            "button.msg-overlay-bubble-header__control--close",
            "button.mercado-match__dismiss",
            
            # Toast/notification dismissals (safe)
            ".artdeco-toast-item__dismiss",
            
            # Cookie consent and notifications (safe)
            "button[action-type='DENY']",
            "button.cookie-consent-dismiss",
        ]
        
        # Text-based button selectors for dismissal
        # CRITICAL: "Dismiss" is REMOVED because it can match the Easy Apply
        # modal's dismiss button. Only use safe, non-modal text patterns.
        self.dismiss_texts = [
            "Not now",
            "No thanks",
            "Maybe later",
            "Got it",
        ]
        
        # Track recently clicked elements to avoid clicking same thing multiple times
        self._recently_clicked_elements = set()
        self._click_cooldown = {}  # Element hash -> timestamp
    
    def block_all(self) -> int:
        """Attempt to close all detected popups. Returns count of popups closed.
        
        CRITICAL: Avoids clicking buttons inside Easy Apply modal to prevent
        accidentally closing the application form.
        """
        popups_closed = 0
        current_time = time.time()
        
        # SAFETY CHECK: Don't dismiss popups if Easy Apply modal is open
        try:
            if _is_easy_apply_open(self.driver):
                # Easy Apply is open - only dismiss NON-modal popups (toasts, notifications)
                safe_selectors = [
                    ".artdeco-toast-item__dismiss",
                    ".msg-overlay-bubble-header__control--close",
                ]
                for selector in safe_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            if element.is_displayed():
                                element.click()
                                popups_closed += 1
                                time.sleep(0.1)
                    except Exception:
                        pass
                return popups_closed
        except Exception:
            pass
        
        # Try selector-based dismissal (only if NOT in Easy Apply modal)
        for selector in self.popup_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    try:
                        if element.is_displayed():
                            # Get element identifier to check cooldown
                            elem_id = f"{selector}_{element.location}"
                            last_click = self._click_cooldown.get(elem_id, 0)
                            
                            # Skip if clicked within last 5 seconds
                            if current_time - last_click < 5.0:
                                continue
                            
                            element.click()
                            self._click_cooldown[elem_id] = current_time
                            popups_closed += 1
                            time.sleep(0.2)
                    except (ElementClickInterceptedException, StaleElementReferenceException):
                        pass
            except NoSuchElementException:
                pass
        
        # Try text-based dismissal
        for text in self.dismiss_texts:
            try:
                xpath = f"//button[contains(text(), '{text}')] | //span[contains(text(), '{text}')]/ancestor::button"
                elements = self.driver.find_elements(By.XPATH, xpath)
                for element in elements:
                    try:
                        if element.is_displayed():
                            elem_id = f"{text}_{element.location}"
                            last_click = self._click_cooldown.get(elem_id, 0)
                            
                            # Skip if clicked within last 5 seconds
                            if current_time - last_click < 5.0:
                                continue
                            
                            element.click()
                            self._click_cooldown[elem_id] = current_time
                            popups_closed += 1
                            time.sleep(0.2)
                    except (ElementClickInterceptedException, StaleElementReferenceException):
                        pass
            except NoSuchElementException:
                pass
        
        self.blocked_count += popups_closed
        return popups_closed
    
    def dismiss_overlay(self) -> bool:
        """Dismiss any modal overlay covering the page.
        
        SAFETY: Only dismisses overlays that are NOT the Easy Apply modal.
        """
        try:
            # SAFETY: Do NOT dismiss overlays if Easy Apply modal is open
            if _is_easy_apply_open(self.driver):
                return False
            
            # Try to find and close modal overlays
            overlays = self.driver.find_elements(By.CSS_SELECTOR, ".artdeco-modal-overlay")
            for _overlay in overlays:
                try:
                    # Find close button within the overlay's modal
                    close_btn = self.driver.find_element(By.CSS_SELECTOR, 
                        ".artdeco-modal button.artdeco-modal__dismiss")
                    if close_btn.is_displayed():
                        close_btn.click()
                        return True
                except Exception:
                    pass
            return False
        except Exception:
            return False
    
    def get_stats(self) -> dict:
        """Return statistics about blocked popups."""
        return {
            'total_blocked': self.blocked_count
        }


def dismiss_deloitte_popup(driver, max_attempts: int = 3) -> bool:
    """
    Specifically dismiss Deloitte's custom popup that appears during job applications.
    
    IMPORTANT: Deloitte popups typically have an "OK" button at the bottom right,
    not a cross/X button. This function specifically targets these patterns.
    
    Enhanced to handle:
    - Deloitte cookie consent popups (with OK button)
    - Third-party widget notifications
    - LinkedIn overlay dialogs (NOT Easy Apply modal)
    - Session timeout warnings
    
    Args:
        driver: Selenium WebDriver instance
        max_attempts: Maximum number of attempts to dismiss the popup
        
    Returns:
        bool: True if popup was dismissed, False otherwise
    """
    # CRITICAL: Check if Easy Apply modal is open - DON'T dismiss anything that might close it
    try:
        if _is_easy_apply_open(driver):
            # Easy Apply is open - only dismiss clearly external popups
            # (cookies, GDPR consent, etc. - NOT anything inside the modal)
            external_only_selectors = [
                "#onetrust-accept-btn-handler",  # Cookie consent
                ".onetrust-close-btn-handler",
                "[id*='truste'] button",
                "[class*='cookie-banner'] button",
                "[class*='gdpr'] button",
            ]
            for selector in external_only_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            element.click()
                            return True
                except Exception:
                    continue
            return False  # Don't try other strategies if Easy Apply is open
    except Exception:
        pass
    
    # Deloitte-specific selectors (expanded for 2025 patterns)
    # ORDERED BY PRIORITY - Most specific first
    deloitte_selectors = [
        # Deloitte's custom "OK" button (typically at bottom right)
        "div[class*='deloitte'] button:last-child",
        "div[class*='Deloitte'] button:last-child",
        "div[class*='popup'] button[class*='ok']",
        "div[class*='popup'] button[class*='accept']",
        "div[class*='popup'] button[class*='confirm']",
        
        # Deloitte-specific patterns (third-party popup)
        "div[class*='deloitte'] button",
        "div[class*='Deloitte'] button",
        "[class*='cookie'] button",
        "[class*='consent'] button",
        "[id*='cookie'] button",
        "[id*='consent'] button",
        "div[class*='popup'] button[class*='close']",
        "div[class*='popup'] button[class*='ok']",
        "div[class*='popup'] button[class*='accept']",
        "[class*='toast'] button",
        "[class*='banner'] button[class*='close']",
        "[class*='banner'] button[class*='accept']",
        
        # GDPR / Cookie consent (common on Deloitte sites)
        "#onetrust-accept-btn-handler",
        ".onetrust-close-btn-handler",
        "[class*='onetrust'] button",
        "[id*='truste'] button",
        "[class*='privacy'] button[class*='accept']",
        
        # Generic fallbacks (ONLY clearly third-party / non-modal patterns)
        "button.popup-close",
        "button.notification-close",
        
        # iframe popup buttons
        "iframe[class*='cookie']",
    ]
    
    # Text patterns that indicate dismiss buttons
    # CRITICAL: Removed 'Dismiss', 'Close', 'Skip' as they can match Easy Apply modal buttons
    dismiss_texts = ['OK', 'Got it', 'Accept', 'Okay', 
                     'Accept All', 'Accept Cookies', 'I Accept', 'Agree', 'Allow', 'Allow All']
    
    for attempt in range(max_attempts):
        
        # Strategy 1: Try CSS selectors
        for selector in deloitte_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    try:
                        if element.is_displayed():
                            # Try regular click first
                            try:
                                element.click()
                            except ElementClickInterceptedException:
                                # Fallback to JavaScript click
                                driver.execute_script("arguments[0].click();", element)
                            
                            time.sleep(0.3)
                            return True
                    except StaleElementReferenceException:
                        continue
            except NoSuchElementException:
                continue
        
        # Strategy 2: Try text-based buttons
        for text in dismiss_texts:
            try:
                xpath = f"//button[contains(text(), '{text}')] | //button[.//span[contains(text(), '{text}')]]"
                elements = driver.find_elements(By.XPATH, xpath)
                for element in elements:
                    try:
                        if element.is_displayed():
                            try:
                                element.click()
                            except Exception:
                                driver.execute_script("arguments[0].click();", element)
                            time.sleep(0.3)
                            return True
                    except Exception:
                        continue
            except Exception:
                continue
        
        # Strategy 3: JavaScript aggressive popup dismissal
        try:
            dismissed = driver.execute_script("""
                let dismissed = false;
                
                // Find any visible popup-like elements
                const popupPatterns = [
                    '[class*="popup"]',
                    '[class*="modal"]',
                    '[class*="overlay"]',
                    '[class*="toast"]',
                    '[class*="notification"]',
                    '[class*="alert"]',
                    '[style*="fixed"]',
                    '[style*="z-index"]'
                ];
                
                popupPatterns.forEach(pattern => {
                    document.querySelectorAll(pattern).forEach(popup => {
                        if (popup.offsetParent !== null) {  // Check if visible
                            // Look for close/dismiss buttons inside
                            const buttons = popup.querySelectorAll('button, [role="button"], [class*="close"], [class*="dismiss"]');
                            buttons.forEach(btn => {
                                if (btn.offsetParent !== null) {
                                    btn.click();
                                    dismissed = true;
                                }
                            });
                        }
                    });
                });
                
                // Also try clicking any floating buttons at bottom-right
                document.querySelectorAll('div[style*="position: fixed"], div[style*="position:fixed"]').forEach(el => {
                    const rect = el.getBoundingClientRect();
                    // Check if it's in bottom-right area
                    if (rect.bottom > window.innerHeight - 200 && rect.right > window.innerWidth - 300) {
                        const btns = el.querySelectorAll('button');
                        btns.forEach(btn => {
                            if (btn.offsetParent !== null) {
                                btn.click();
                                dismissed = true;
                            }
                        });
                    }
                });
                
                return dismissed;
            """)
            if dismissed:
                return True
        except Exception:
            pass
        
        # Strategy 4: Press Escape key - ONLY if NOT inside Easy Apply modal
        # IMPORTANT: Pressing ESC inside Easy Apply modal will CLOSE the modal!
        try:
            # Check if Easy Apply modal is open - if so, DON'T press ESC
            easy_apply_modal = driver.find_elements(By.CLASS_NAME, "jobs-easy-apply-modal")
            if not easy_apply_modal or len(easy_apply_modal) == 0:
                from selenium.webdriver.common.keys import Keys
                from selenium.webdriver.common.action_chains import ActionChains
                actions = ActionChains(driver)
                actions.send_keys(Keys.ESCAPE).perform()
                time.sleep(0.2)
        except Exception:
            pass
        
        # Brief wait before next attempt
        if attempt < max_attempts - 1:
            time.sleep(0.5)
    
    return False


def setup_popup_blocker_for_session(driver) -> PopupBlocker:
    """
    Initialize and return a PopupBlocker instance for the session.
    
    Args:
        driver: Selenium WebDriver instance
        
    Returns:
        PopupBlocker: Configured popup blocker instance
    """
    blocker = PopupBlocker(driver)
    
    # Initial popup sweep
    blocker.block_all()
    
    # Inject aggressive popup blocker script
    inject_popup_blocker_script(driver)
    
    return blocker


def inject_popup_blocker_script(driver) -> bool:
    """
    Inject JavaScript to automatically dismiss popups including third-party ones like Deloitte.
    This uses MutationObserver to catch popups as soon as they appear.
    
    CRITICAL: This script is SMART about Easy Apply modals - it won't click buttons inside them.
    """
    try:
        popup_blocker_script = """
        (function() {
            // Skip if already injected
            if (window.__popupBlockerInjected) return;
            window.__popupBlockerInjected = true;
            
            console.log('[PopupBlocker] Injecting SAFE popup blocker...');
            
            // Track clicked elements to avoid repeated clicks
            const clickedElements = new Set();
            const CLICK_COOLDOWN = 10000; // 10 seconds cooldown
            
            function getElementKey(el) {
                return el.tagName + '_' + el.className + '_' + el.textContent.substring(0, 20);
            }
            
            // SAFETY CHECK: Is Easy Apply modal open?
            function isEasyApplyOpen() {
                return document.querySelector('.jobs-easy-apply-modal') !== null ||
                       document.querySelector('[data-test-modal-id="easy-apply-modal"]') !== null;
            }
            
            // Check if element is inside Easy Apply modal
            function isInsideEasyApply(el) {
                return el.closest('.jobs-easy-apply-modal') !== null ||
                       el.closest('[class*="easy-apply"]') !== null ||
                       el.closest('[class*="jobs-apply"]') !== null;
            }
            
            // Function to dismiss popups
            function dismissPopups() {
                // If Easy Apply is open, only dismiss external cookie/GDPR popups
                const easyApplyOpen = isEasyApplyOpen();
                
                // External popup selectors (safe to click even during Easy Apply)
                const externalSelectors = [
                    '#onetrust-accept-btn-handler',
                    '.onetrust-close-btn-handler',
                    '[class*="cookie-banner"] button',
                    '[class*="gdpr"] button',
                    '.artdeco-toast-item__dismiss',
                    '.msg-overlay-bubble-header__control--close',
                ];
                
                // Internal modal dismiss selectors (ONLY when Easy Apply is NOT open)
                const internalSelectors = [
                    'button[aria-label="Dismiss"]',
                    'button.artdeco-modal__dismiss',
                    '[data-test="close-button"]',
                    '[data-test-modal-close-btn]',
                ];
                
                let dismissed = 0;
                
                // Always try external selectors
                externalSelectors.forEach(selector => {
                    try {
                        document.querySelectorAll(selector).forEach(el => {
                            if (el.offsetParent !== null) {
                                const key = getElementKey(el);
                                if (!clickedElements.has(key)) {
                                    el.click();
                                    clickedElements.add(key);
                                    setTimeout(() => clickedElements.delete(key), CLICK_COOLDOWN);
                                    dismissed++;
                                    console.log('[PopupBlocker] Dismissed external popup:', selector);
                                }
                            }
                        });
                    } catch(e) {}
                });
                
                // Only try internal selectors if Easy Apply is NOT open
                if (!easyApplyOpen) {
                    internalSelectors.forEach(selector => {
                        try {
                            document.querySelectorAll(selector).forEach(el => {
                                if (el.offsetParent !== null && !isInsideEasyApply(el)) {
                                    const key = getElementKey(el);
                                    if (!clickedElements.has(key)) {
                                        el.click();
                                        clickedElements.add(key);
                                        setTimeout(() => clickedElements.delete(key), CLICK_COOLDOWN);
                                        dismissed++;
                                        console.log('[PopupBlocker] Dismissed internal popup:', selector);
                                    }
                                }
                            });
                        } catch(e) {}
                    });
                    
                    // Deloitte OK button handling (only when Easy Apply NOT open)
                    ['OK', 'Got it', 'Accept', 'Continue'].forEach(text => {
                        document.querySelectorAll('button').forEach(el => {
                            if (el.offsetParent !== null && 
                                el.textContent.trim() === text && 
                                !isInsideEasyApply(el)) {
                                const key = getElementKey(el);
                                if (!clickedElements.has(key)) {
                                    el.click();
                                    clickedElements.add(key);
                                    setTimeout(() => clickedElements.delete(key), CLICK_COOLDOWN);
                                    dismissed++;
                                    console.log('[PopupBlocker] Dismissed via text:', text);
                                }
                            }
                        });
                    });
                }
                
                return dismissed;
            }
            
            // Set up MutationObserver to watch for new popups
            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.addedNodes.length) {
                        // Slight delay to let the popup fully render
                        setTimeout(dismissPopups, 200);
                    }
                });
            });
            
            // Start observing
            observer.observe(document.body, { 
                childList: true, 
                subtree: true 
            });
            
            // Initial sweep after page load
            setTimeout(dismissPopups, 1000);
            
            // Periodic sweep every 5 seconds (reduced frequency to avoid issues)
            setInterval(dismissPopups, 5000);
            
            console.log('[PopupBlocker] SAFE popup blocker active - respects Easy Apply modal');
        })();
        """
        driver.execute_script(popup_blocker_script)
        return True
    except Exception as e:
        print(f"Failed to inject popup blocker script: {e}")
        return False


def block_messaging_overlay(driver) -> bool:
    """
    Specifically block the LinkedIn messaging overlay popup.
    
    Args:
        driver: Selenium WebDriver instance
        
    Returns:
        bool: True if messaging overlay was closed, False otherwise
    """
    try:
        # Close messaging overlay
        close_selectors = [
            "button.msg-overlay-bubble-header__control--close",
            "[data-control-name='overlay.close_msg_overlay']",
            ".msg-overlay-bubble-header button[type='button']",
        ]
        
        for selector in close_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed():
                        element.click()
                        return True
            except Exception:
                continue
        
        return False
    except Exception:
        return False


def aggressive_popup_sweep(driver, max_attempts: int = 5) -> int:
    """
    Aggressively sweep and dismiss all visible popups.
    Uses multiple strategies including JavaScript execution.
    
    Args:
        driver: Selenium WebDriver instance
        max_attempts: Maximum number of sweep attempts
        
    Returns:
        int: Number of popups dismissed
    """
    total_dismissed = 0
    
    for attempt in range(max_attempts):
        dismissed = 0  # Initialize before try block to avoid UnboundLocalError
        # Strategy 1: Use JavaScript to find and click all dismiss buttons
        try:
            dismissed = driver.execute_script("""
                let count = 0;
                const dismissSelectors = [
                    'button[aria-label="Dismiss"]',
                    'button[aria-label="Close"]',
                    'button.artdeco-modal__dismiss',
                    '[data-test="close-button"]',
                ];
                
                dismissSelectors.forEach(selector => {
                    try {
                        document.querySelectorAll(selector).forEach(el => {
                            if (el.offsetParent !== null) {
                                el.click();
                                count++;
                            }
                        });
                    } catch(e) {}
                });
                
                // Also try clicking any button with common dismiss texts
                ['OK', 'Got it', 'Dismiss', 'Close', 'Skip'].forEach(text => {
                    document.querySelectorAll('button').forEach(btn => {
                        if (btn.offsetParent !== null && btn.textContent.trim() === text) {
                            btn.click();
                            count++;
                        }
                    });
                });
                
                return count;
            """)
            total_dismissed += dismissed or 0
        except Exception:
            pass
        
        # Strategy 2: Press Escape key to dismiss modals - ONLY if NOT inside Easy Apply modal
        # IMPORTANT: This would close the Easy Apply modal if it's open!
        try:
            easy_apply_modal = driver.find_elements(By.CLASS_NAME, "jobs-easy-apply-modal")
            if not easy_apply_modal or len(easy_apply_modal) == 0:
                from selenium.webdriver.common.keys import Keys
                driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        except Exception:
            pass
        
        # Brief pause between attempts
        time.sleep(0.2)
        
        if dismissed == 0 and attempt > 1:
            break  # No more popups found
    
    return total_dismissed


def handle_premium_popup(driver) -> bool:
    """
    Handle LinkedIn Premium promotion popups.
    
    Args:
        driver: Selenium WebDriver instance
        
    Returns:
        bool: True if premium popup was dismissed, False otherwise
    """
    try:
        dismiss_selectors = [
            "button[aria-label='Dismiss'][data-test-modal-close-btn]",
            ".premium-promo-modal button.artdeco-modal__dismiss",
            "[data-test='premium-upsell-modal-close']",
        ]
        
        dismiss_texts = ["Not now", "Maybe later", "No thanks"]
        
        # Try selectors
        for selector in dismiss_selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                if element.is_displayed():
                    element.click()
                    return True
            except Exception:
                continue
        
        # Try text-based buttons
        for text in dismiss_texts:
            try:
                xpath = f"//button[contains(text(), '{text}')]"
                element = driver.find_element(By.XPATH, xpath)
                if element.is_displayed():
                    element.click()
                    return True
            except Exception:
                continue
        
        return False
    except Exception:
        return False

# ============================================================================
# SYSTEM-LEVEL POPUP HANDLER (For Deloitte DLP and other OS-level popups)
# ============================================================================

def dismiss_system_popup_with_pyautogui(target_text: str = "OK", max_wait_seconds: float = 2.0) -> bool:
    """
    Dismiss system-level popups (like Deloitte DLP) that appear OUTSIDE the browser.
    These popups cannot be handled by Selenium - we need pyautogui for screen interaction.
    
    This function looks for buttons with specific text (like "OK") and clicks them.
    
    Args:
        target_text: The button text to look for (default "OK")
        max_wait_seconds: Maximum time to search for the button
        
    Returns:
        bool: True if popup was likely dismissed, False otherwise
    """
    try:
        import pyautogui
        import time as time_module
        
        # Get screen size
        screen_width, screen_height = pyautogui.size()
        
        # Deloitte DLP popup typically appears in bottom-right corner
        # Based on the screenshot: The "OK" button is in the bottom-right of the popup
        # The popup itself is in the bottom-right of the screen
        
        # Search region: Focus on bottom-right quadrant of screen
        search_region = (
            int(screen_width * 0.5),    # Left boundary (right half of screen)
            int(screen_height * 0.3),   # Top boundary (bottom 70% of screen)
            int(screen_width * 0.5),    # Width
            int(screen_height * 0.7)    # Height
        )
        
        start_time = time_module.time()
        
        while time_module.time() - start_time < max_wait_seconds:
            try:
                # Try to locate "OK" button image if available
                # First, try to find by locating the button on screen
                
                # Strategy 1: Look for the OK button using image recognition
                # (This requires an OK button image file - fallback to other methods if not available)
                try:
                    ok_button = pyautogui.locateOnScreen(
                        'modules/images/ok_button.png',  # You can add this image
                        confidence=0.7,
                        region=search_region
                    )
                    if ok_button:
                        # Click center of the button
                        pyautogui.click(pyautogui.center(ok_button))
                        print("[SystemPopup] ✅ Clicked OK button via image recognition")
                        return True
                except Exception:
                    pass  # Image not found or pyautogui.locateOnScreen failed
                
                # Strategy 2: Try locating any button-like element
                # Check if there's a Deloitte popup window visible
                # The popup has characteristic colors (green Deloitte logo, grey background)
                
                # Strategy 3: Click at known position (bottom-right of a typical popup)
                # Based on your screenshot, the OK button is at approximately:
                # - Bottom right area of screen
                # - The popup is roughly 400x300 pixels
                # - OK button is in the bottom-right of the popup
                
                # Calculate approximate position based on typical Deloitte popup
                # Popup appears to be centered-right with OK button at bottom-right
                popup_right_edge = screen_width - 50  # 50px from right edge
                popup_bottom_edge = screen_height - 80  # 80px from bottom
                
                # OK button approximate position (within popup)
                ok_button_x = popup_right_edge - 60  # OK button is ~60px from right edge of popup
                ok_button_y = popup_bottom_edge - 30  # OK button is ~30px from bottom of popup
                
                # Don't click blindly - only click if we can verify the popup exists
                # We'll use a small region check first
                break  # Exit after one iteration if no image recognition
                
            except Exception as e:
                print(f"[SystemPopup] Search error: {e}")
                break
        
        return False
        
    except ImportError:
        print("[SystemPopup] pyautogui not available for system popup handling")
        return False
    except Exception as e:
        print(f"[SystemPopup] Error: {e}")
        return False


_dlp_last_dismissed_time = 0
_dlp_cooldown_seconds = 3


def dismiss_deloitte_dlp_popup(max_attempts: int = 3, click_delay: float = 0.3) -> bool:
    """
    Specifically handle Deloitte DLP (Data Loss Prevention) system popup.
    
    This popup appears when:
    - Uploading files on LinkedIn (resume, etc.)
    - The popup says "Action blocked" with "Upload blocked per APR 208"
    - Has an "OK" button at bottom-right corner of the popup
    - The popup itself appears at bottom-right of the screen
    - Auto-closes after ~38-45 seconds
    
    CRITICAL: This function ONLY clicks the OK button position.
    It does NOT:
    - Click multiple random positions (causes browser minimization)
    - Press Enter/Space keys (affects LinkedIn modal)
    - Click anywhere outside the popup area
    
    Based on observed popup:
    - Popup is approximately 420x320 pixels
    - OK button is at bottom-right corner of popup (~50x25 pixels)
    - Popup appears at screen bottom-right, above taskbar
    
    Args:
        max_attempts: Number of attempts to find and click the button
        click_delay: Delay between attempts
        
    Returns:
        bool: True if popup was likely dismissed, False otherwise
    """
    global _dlp_last_dismissed_time
    try:
        import pyautogui
        import time as time_module
        
        # COOLDOWN CHECK: Prevent repeated clicks after successful dismissal
        current_time = time_module.time()
        if current_time - _dlp_last_dismissed_time < _dlp_cooldown_seconds:
            return False
        
        # Keep pyautogui failsafe on for safety
        pyautogui.FAILSAFE = True
        
        screen_width, screen_height = pyautogui.size()
        print(f"[DLP] Screen size: {screen_width}x{screen_height}")
        
        # ========== CALCULATE OK BUTTON POSITION ==========
        # Based on the screenshot analysis:
        # - Popup width: ~420px, height: ~320px
        # - Popup is positioned at bottom-right of screen (above taskbar ~40px)
        # - OK button is at bottom-right of popup
        # - OK button is small: ~50x25 pixels
        # ADJUSTED: Click slightly more upwards and towards left as per user feedback
        
        # Taskbar height (typically 40px on Windows)
        taskbar_height = 40
        
        # Popup dimensions (observed from screenshot)
        popup_width = 420
        popup_height = 320
        
        # OK button offset from popup edges (ADJUSTED - DOUBLED distance)
        # Originally: 45px from right, 30px from bottom
        # V1: 55px from right, 40px from bottom (10px shift)
        # V2: 65px from right, 50px from bottom (20px shift - DOUBLED)
        ok_offset_from_right = 65  # Doubled distance - much more LEFT
        ok_offset_from_bottom = 50  # Doubled distance - much more UP
        
        # Calculate popup position (bottom-right of screen, above taskbar)
        popup_right = screen_width - 10  # Small margin from screen edge
        popup_bottom = screen_height - taskbar_height - 5  # Above taskbar with small margin
        popup_left = popup_right - popup_width
        popup_top = popup_bottom - popup_height
        
        # Calculate OK button center position
        ok_button_x = popup_right - ok_offset_from_right
        ok_button_y = popup_bottom - ok_offset_from_bottom
        
        print(f"[DLP] Calculated popup area: ({popup_left}, {popup_top}) to ({popup_right}, {popup_bottom})")
        print(f"[DLP] Target OK button position: ({ok_button_x}, {ok_button_y})")
        
        # Validate the position is reasonable (within screen bounds and not in dangerous areas)
        if ok_button_x < 0 or ok_button_x > screen_width or ok_button_y < 0 or ok_button_y > screen_height:
            print("[DLP] \u26a0\ufe0f Calculated position out of bounds, skipping")
            return False
        
        # Don't click if position is in taskbar area
        if ok_button_y > screen_height - 35:
            print("[DLP] \u26a0\ufe0f Position too close to taskbar, adjusting")
            ok_button_y = screen_height - 50
        
        for attempt in range(max_attempts):
            try:
                # ========== SINGLE TARGETED CLICK ==========
                # Click ONLY at the calculated OK button position
                print(f"[DLP] Attempt {attempt + 1}/{max_attempts}: Clicking OK at ({ok_button_x}, {ok_button_y})")
                
                # Move mouse first, then click (more reliable than direct click)
                pyautogui.moveTo(ok_button_x, ok_button_y, duration=0.1)
                time_module.sleep(0.05)
                pyautogui.click()
                
                print("[DLP] \u2705 Clicked OK button")
                _dlp_last_dismissed_time = current_time
                
                # Brief delay to let popup close
                time_module.sleep(click_delay)
                
                # Only one click per attempt - don't spam clicks
                return True
                
            except Exception as e:
                print(f"[DLP] Click attempt {attempt + 1} error: {e}")
                time_module.sleep(click_delay)
        
        return False
        
    except ImportError:
        print("[DLP] pyautogui not available")
        return False
    except Exception as e:
        print(f"[DLP] Error handling Deloitte popup: {e}")
        return False


def create_ok_button_image():
    """
    Create a simple OK button reference image for image recognition.
    This should be run once to generate the reference image.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        import os
        
        # Create images directory if it doesn't exist
        os.makedirs('modules/images', exist_ok=True)
        
        # Create a simple OK button image (grey background, black text)
        img = Image.new('RGB', (60, 30), color=(240, 240, 240))
        draw = ImageDraw.Draw(img)
        
        # Try to use a system font, fallback to default
        try:
            font = ImageFont.truetype("arial.ttf", 14)
        except Exception:
            font = ImageFont.load_default()
        
        # Draw "OK" text
        draw.text((20, 5), "OK", fill=(0, 0, 0), font=font)
        
        # Draw button border
        draw.rectangle([(0, 0), (59, 29)], outline=(128, 128, 128))
        
        # Save the image
        img.save('modules/images/ok_button.png')
        print("[DLP] Created OK button reference image")
        return True
        
    except Exception as e:
        print(f"[DLP] Could not create reference image: {e}")
        return False


def monitor_and_dismiss_dlp_popup(duration_seconds: float = 5.0, check_interval: float = 0.5):
    """
    Monitor for and dismiss DLP popups for a specified duration.
    Useful to run in a background thread during file upload operations.
    
    Args:
        duration_seconds: How long to monitor for popups
        check_interval: Time between checks
    """
    import time as time_module
    start_time = time_module.time()
    
    while time_module.time() - start_time < duration_seconds:
        if dismiss_deloitte_dlp_popup(max_attempts=1, click_delay=0.1):
            print("[DLP] ✅ Popup dismissed during monitoring")
            return True
        time_module.sleep(check_interval)
    
    return False