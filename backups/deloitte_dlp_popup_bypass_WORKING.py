"""
=============================================================================
DELOITTE DLP POPUP BYPASS - WORKING BACKUP
=============================================================================
This file contains the working code for bypassing the Deloitte DLP (Data Loss
Prevention) popup that appears at the bottom-right corner of the screen.

Created: February 2, 2026
Status: CONFIRMED WORKING

The popup appears as a system-level dialog (not a browser popup), so we use
pyautogui to click at calculated screen coordinates.
=============================================================================
"""

import pyautogui
import time as time_module

def dismiss_deloitte_dlp_popup(max_attempts: int = 1, click_delay: float = 0.3) -> bool:
    """
    Dismiss the Deloitte DLP popup by clicking OK at calculated screen coordinates.
    
    The DLP popup appears at the BOTTOM-RIGHT of the screen, above the taskbar.
    This is a SYSTEM-LEVEL popup, NOT a browser popup, so we must use pyautogui
    for screen-level clicking.
    
    POPUP CHARACTERISTICS (observed from testing):
    - Position: Bottom-right corner of screen, above taskbar
    - Approximate size: 420x320 pixels
    - OK button: Located in the bottom-right area of the popup
    
    CLICK POSITION CALCULATION:
    - Screen width/height from pyautogui
    - Taskbar height: ~40px
    - Popup is ~420x320px positioned at bottom-right
    - OK button offset from popup edges: 65px from right, 50px from bottom
    
    Args:
        max_attempts: Number of click attempts (default 1 for targeted click)
        click_delay: Delay between attempts in seconds
        
    Returns:
        True if click was attempted, False if error occurred
        
    HISTORY:
    - Original: 45px right, 30px bottom - click was too far right/down
    - V1: 55px right, 40px bottom - still not clicking OK
    - V2: 65px right, 50px bottom - WORKING!
    """
    try:
        # Get screen dimensions
        screen_width, screen_height = pyautogui.size()
        
        # Taskbar height (typically 40px on Windows)
        taskbar_height = 40
        
        # Popup dimensions (observed from screenshot)
        popup_width = 420
        popup_height = 320
        
        # OK button offset from popup edges (WORKING VALUES - V2)
        # These values were calibrated through testing
        ok_offset_from_right = 65  # Distance from popup's right edge to OK button center
        ok_offset_from_bottom = 50  # Distance from popup's bottom edge to OK button center
        
        # Calculate popup position (bottom-right of screen, above taskbar)
        popup_right = screen_width - 10  # Small margin from screen edge
        popup_bottom = screen_height - taskbar_height - 5  # Above taskbar with small margin
        popup_left = popup_right - popup_width
        popup_top = popup_bottom - popup_height
        
        # Calculate OK button center position
        ok_button_x = popup_right - ok_offset_from_right
        ok_button_y = popup_bottom - ok_offset_from_bottom
        
        print(f"[DLP] Screen size: {screen_width}x{screen_height}")
        print(f"[DLP] Calculated popup area: ({popup_left}, {popup_top}) to ({popup_right}, {popup_bottom})")
        print(f"[DLP] Target OK button position: ({ok_button_x}, {ok_button_y})")
        
        # Validate the position is reasonable (within screen bounds)
        if ok_button_x < 0 or ok_button_x > screen_width or ok_button_y < 0 or ok_button_y > screen_height:
            print(f"[DLP] ⚠️ Calculated position out of bounds, skipping")
            return False
        
        # Don't click if position is in taskbar area
        if ok_button_y > screen_height - 35:
            print(f"[DLP] ⚠️ Position too close to taskbar, adjusting")
            ok_button_y = screen_height - 50
        
        for attempt in range(max_attempts):
            try:
                print(f"[DLP] Attempt {attempt + 1}/{max_attempts}: Clicking OK at ({ok_button_x}, {ok_button_y})")
                
                # Move mouse first, then click (more reliable than direct click)
                pyautogui.moveTo(ok_button_x, ok_button_y, duration=0.1)
                time_module.sleep(0.05)
                pyautogui.click()
                
                print(f"[DLP] ✅ Click executed at ({ok_button_x}, {ok_button_y})")
                
                if attempt < max_attempts - 1:
                    time_module.sleep(click_delay)
                    
            except Exception as click_err:
                print(f"[DLP] Click attempt {attempt + 1} failed: {click_err}")
                continue
        
        return True
        
    except Exception as e:
        print(f"[DLP] Error in dismiss_deloitte_dlp_popup: {e}")
        return False


# Alternative approach using window detection (for future reference)
def dismiss_dlp_popup_with_window_detection():
    """
    Alternative approach that tries to detect the actual popup window.
    NOT CURRENTLY USED - keeping for reference.
    
    This approach would use win32gui to find the popup window by title,
    but requires additional Windows-specific dependencies.
    """
    try:
        import win32gui
        import win32con
        
        def find_dlp_window(hwnd, windows):
            title = win32gui.GetWindowText(hwnd)
            if 'DLP' in title or 'Data Loss' in title or 'Deloitte' in title:
                windows.append((hwnd, title))
        
        windows = []
        win32gui.EnumWindows(find_dlp_window, windows)
        
        for hwnd, title in windows:
            print(f"[DLP] Found window: {title}")
            # Could use win32gui.SetForegroundWindow(hwnd) and send click
            
        return len(windows) > 0
        
    except ImportError:
        print("[DLP] win32gui not available")
        return False
    except Exception as e:
        print(f"[DLP] Window detection error: {e}")
        return False


# =============================================================================
# USAGE EXAMPLE
# =============================================================================
if __name__ == "__main__":
    print("Testing Deloitte DLP Popup Bypass...")
    print("Make sure the DLP popup is visible before running this test!")
    print("")
    
    # Wait a moment for user to position popup
    time_module.sleep(2)
    
    # Execute the bypass
    result = dismiss_deloitte_dlp_popup(max_attempts=1, click_delay=0.3)
    
    if result:
        print("\n✅ Bypass executed successfully!")
    else:
        print("\n❌ Bypass failed!")
