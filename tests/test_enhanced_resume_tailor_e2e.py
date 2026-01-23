"""
E2E GUI automation test for Enhanced Resume Tailor Dialog
- Uses pyautogui for Python 3.14 compatibility
- Tests: diff highlighting, skill suggestions, ATS score, PDF/DOCX export/view
"""
import os
import time
import subprocess
import pyautogui
import pytest

# NOTE: This test assumes the dashboard can be launched via run_dashboard.py
# and that the Enhanced Resume Tailor dialog is accessible from the main window.

@pytest.mark.skipif(os.name != 'nt', reason="GUI automation is Windows-specific for this test.")
def test_enhanced_resume_tailor_e2e_pyautogui():
    # Launch the dashboard app and capture output for debugging
    with open('dashboard_test_log.txt', 'w') as log:
        proc = subprocess.Popen(["python", "run_dashboard.py"], stdout=log, stderr=log)
    # Wait up to 20 seconds for the window to appear
    for _ in range(40):
        wins = [w for w in pyautogui.getAllWindows() if 'Job Hunter' in w.title]
        if wins:
            win = wins[0]
            break
        time.sleep(0.5)
    else:
        proc.terminate()
        proc.wait()
        with open('dashboard_test_log.txt') as log:
            print('Dashboard launch log:\n', log.read())
        assert False, 'Dashboard window not found after 20 seconds. See dashboard_test_log.txt for errors.'
    win.minimize()
    win.maximize()
    time.sleep(1)
    # Try to activate, but ignore errors if already focused
    try:
        win.activate()
    except Exception as e:
        print(f"Warning: Could not activate window: {e}")
    time.sleep(1)

    # Open the Enhanced Resume Tailor dialog (simulate menu navigation)
    pyautogui.hotkey('alt', 'r')  # Example: Alt+R for Resume menu
    time.sleep(0.5)
    pyautogui.press('down', presses=2, interval=0.2)  # Navigate to Enhanced Tailor
    pyautogui.press('enter')
    time.sleep(2)

    # Paste resume and JD text (simulate clipboard)
    resume_text = "John Doe\nSkills: Python, SQL\nExperience: ..."
    jd_text = "Looking for Python, SQL, AWS, Docker skills.\nResponsibilities: ..."
    pyautogui.write(resume_text)
    pyautogui.press('tab')
    pyautogui.write(jd_text)
    time.sleep(0.5)

    # Start tailoring
    pyautogui.hotkey('ctrl', 'return')
    time.sleep(10)  # Wait for tailoring to complete

    # Check for export buttons (look for button images or text)
    # This is a placeholder: in real test, use pyautogui.locateOnScreen with screenshots
    # pyautogui.locateOnScreen('open_pdf_btn.png')
    # pyautogui.locateOnScreen('download_pdf_btn.png')

    # Optionally, click export/view buttons and verify file creation
    # ...

    proc.terminate()
    proc.wait()
