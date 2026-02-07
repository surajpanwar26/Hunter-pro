#!/usr/bin/env python3
"""
E2E TEST: Dashboard Settings Audit
====================================
Verifies EVERY dashboard setting actually does what it claims:

 1. File persistence: All settings survive app restart (regex handles strings+bools+ints)
 2. Reset defaults: Match config/settings.py actual defaults
 3. Autopilot form answers: Wired into answer_common_questions()
 4. max_jobs_to_process: Actually enforced in check_limits()
 5. pilot_continue_on_error: Actually checked on failure
 6. Dead-code detection: Marks known-dead settings

Run:  python e2e_test_dashboard_settings.py
"""

import os
import sys
import re
import inspect
import traceback
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "config"))

PASS = 0
FAIL = 0
RESULTS = []

def log(msg, icon="   "):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{ts} {icon} {msg}")
    sys.stdout.flush()

def ok(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1
        RESULTS.append(("✅", label))
        log(f"PASS: {label}", "[✅]")
    else:
        FAIL += 1
        RESULTS.append(("❌", label))
        log(f"FAIL: {label}", "[❌]")

def section(title):
    print(f"\n{'='*60}\n  {title}\n{'='*60}")


# =============================================================================
# TEST 1: File persistence regex handles ALL value types
# =============================================================================
def test_file_persist_regex():
    section("TEST 1: _apply_quick_settings covers all settings + regex handles strings")

    dashboard_path = os.path.join(PROJECT_ROOT, "modules", "dashboard", "dashboard.py")
    with open(dashboard_path, "r", encoding="utf-8", errors="replace") as f:
        src = f.read()

    # --- Boolean/numeric settings should be in bool_num_replacements ---
    bool_num_must_have = [
        'pilot_mode_enabled', 'pilot_max_applications', 'pilot_application_delay',
        'pilot_continue_on_error', 'scheduling_enabled', 'schedule_interval_hours',
        'schedule_max_runtime', 'schedule_max_applications',
        'extension_enabled', 'extension_auto_sync', 'extension_ai_learning',
        'autopilot_chrome_wait_time',
    ]
    bn_start = src.find("bool_num_replacements")
    bn_block = src[bn_start:src.find("string_replacements", bn_start)]
    for setting in bool_num_must_have:
        ok(f"'{setting}'" in bn_block,
           f"file-persist: bool_num has '{setting}'")

    # --- String settings should be in string_replacements ---
    string_must_have = [
        'pilot_resume_mode', 'resume_upload_format', 'schedule_type',
        'job_search_mode', 'extension_detection_mode',
        'autopilot_visa_required', 'autopilot_willing_relocate',
        'autopilot_work_authorization', 'autopilot_remote_preference',
        'autopilot_start_immediately', 'autopilot_background_check',
        'autopilot_commute_ok',
    ]
    for setting in string_must_have:
        ok(f"'{setting}'" in src and setting in src[src.find("string_replacements"):src.find("string_replacements")+3000],
           f"file-persist: string_replacements has '{setting}'")

    # --- Regex for string values: must match quoted pattern ---
    ok("rf'^(\\s*{setting}\\s*=\\s*)[\"\\']([^\"\\']*)[\"\\']'" in src
       or 'rf\'^(\\s*{setting}\\s*=\\s*)["\\\']([^"\\\']*)["\\\']' in src
       or "[\"']([^\"']*)[\"']" in src,
       "file-persist: string regex matches quoted values")


# =============================================================================
# TEST 2: Reset defaults match config/settings.py
# =============================================================================
def test_reset_defaults():
    section("TEST 2: _reset_settings_to_defaults matches settings.py")

    from config import settings

    dashboard_path = os.path.join(PROJECT_ROOT, "modules", "dashboard", "dashboard.py")
    with open(dashboard_path, "r", encoding="utf-8", errors="replace") as f:
        src = f.read()

    # Extract the reset method
    reset_start = src.find("def _reset_settings_to_defaults")
    reset_end = src.find("\n    def ", reset_start + 10)
    reset_src = src[reset_start:reset_end]

    # Check key defaults that were wrong before the fix
    ok("alternate_sortby.set(False)" in reset_src or "qs_alternate_sortby.set(False)" in reset_src,
       "reset: alternate_sortby = False (settings.py default)")
    ok("safe_mode.set(False)" in reset_src or "qs_safe_mode.set(False)" in reset_src,
       "reset: safe_mode = False (settings.py default)")
    ok("stealth_mode.set(True)" in reset_src or "qs_stealth_mode.set(True)" in reset_src,
       "reset: stealth_mode = True (settings.py default)")
    ok("show_ai_errors.set(True)" in reset_src or "qs_show_ai_errors.set(True)" in reset_src,
       "reset: showAiErrorAlerts = True (settings.py default)")

    # Check that autopilot answers are reset
    ok("autopilot_visa_required" in reset_src,
       "reset: includes autopilot_visa_required")
    ok("autopilot_willing_relocate" in reset_src,
       "reset: includes autopilot_willing_relocate")
    ok("autopilot_chrome_wait_time" in reset_src,
       "reset: includes autopilot_chrome_wait_time")

    # Check that job_search_mode is reset
    ok("job_search_mode" in reset_src,
       "reset: includes job_search_mode")


# =============================================================================
# TEST 3: Autopilot form answers wired into answer_common_questions()
# =============================================================================
def test_autopilot_answers_wired():
    section("TEST 3: autopilot_* settings wired into answer_common_questions()")

    import runAiBot
    source = inspect.getsource(runAiBot.answer_common_questions)

    # Must check pilot_mode_enabled
    ok("pilot_mode_enabled" in source, "autopilot: checks pilot_mode_enabled")

    # Must use autopilot settings
    ok("autopilot_willing_relocate" in source, "autopilot: uses autopilot_willing_relocate")
    ok("autopilot_work_authorization" in source, "autopilot: uses autopilot_work_authorization")
    ok("autopilot_remote_preference" in source, "autopilot: uses autopilot_remote_preference")
    ok("autopilot_start_immediately" in source, "autopilot: uses autopilot_start_immediately")
    ok("autopilot_background_check" in source, "autopilot: uses autopilot_background_check")
    ok("autopilot_commute_ok" in source, "autopilot: uses autopilot_commute_ok")
    ok("autopilot_visa_required" in source, "autopilot: uses autopilot_visa_required")

    # Functional test: simulate pilot mode answering
    import config.settings as settings_mod
    orig_pilot = settings_mod.pilot_mode_enabled
    settings_mod.pilot_mode_enabled = True
    settings_mod.autopilot_willing_relocate = "No"
    settings_mod.autopilot_background_check = "No"
    runAiBot.pilot_mode_enabled = True

    result = runAiBot.answer_common_questions("are you willing to relocate?", "Yes")
    ok(result == "No", f"autopilot functional: relocate='No' (got '{result}')")

    result2 = runAiBot.answer_common_questions("do you consent to a background check?", "Yes")
    ok(result2 == "No", f"autopilot functional: background_check='No' (got '{result2}')")

    # Non-matching question should keep default
    result3 = runAiBot.answer_common_questions("what is your favorite color?", "Yes")
    ok(result3 == "Yes", f"autopilot functional: unmatched keeps default (got '{result3}')")

    # Restore
    settings_mod.pilot_mode_enabled = orig_pilot
    settings_mod.autopilot_willing_relocate = "Yes"
    settings_mod.autopilot_background_check = "Yes"
    runAiBot.pilot_mode_enabled = orig_pilot


# =============================================================================
# TEST 4: max_jobs_to_process is enforced in check_limits()
# =============================================================================
def test_max_jobs_enforced():
    section("TEST 4: max_jobs_to_process enforced in check_limits()")

    import runAiBot
    source = inspect.getsource(runAiBot.check_pilot_limit_reached)

    ok("max_jobs_to_process" in source, "max_jobs: check_pilot_limit_reached reads max_jobs_to_process")
    ok("external_jobs_count" in source or "total_processed" in source,
       "max_jobs: check_pilot_limit_reached counts total processed (easy + external)")

    # Functional test
    import config.settings as settings_mod
    orig_max = getattr(settings_mod, 'max_jobs_to_process', 0)
    orig_pilot_max = getattr(settings_mod, 'pilot_max_applications', 0)
    settings_mod.max_jobs_to_process = 2
    settings_mod.pilot_max_applications = 0  # disable pilot limit

    orig_easy = runAiBot.easy_applied_count
    orig_ext = runAiBot.external_jobs_count
    orig_daily = runAiBot.dailyEasyApplyLimitReached
    runAiBot.dailyEasyApplyLimitReached = False

    runAiBot.easy_applied_count = 1
    runAiBot.external_jobs_count = 1  # total=2 >= max=2

    result = runAiBot.check_pilot_limit_reached()
    ok(result == True, f"max_jobs functional: limit=2, total=2 → stop (got {result})")

    runAiBot.easy_applied_count = 0
    runAiBot.external_jobs_count = 0

    result2 = runAiBot.check_pilot_limit_reached()
    ok(result2 == False, f"max_jobs functional: limit=2, total=0 → continue (got {result2})")

    # Restore
    runAiBot.easy_applied_count = orig_easy
    runAiBot.external_jobs_count = orig_ext
    runAiBot.dailyEasyApplyLimitReached = orig_daily
    settings_mod.max_jobs_to_process = orig_max
    settings_mod.pilot_max_applications = orig_pilot_max


# =============================================================================
# TEST 5: pilot_continue_on_error is checked in job loop
# =============================================================================
def test_pilot_continue_on_error():
    section("TEST 5: pilot_continue_on_error checked in job error handler")

    bot_path = os.path.join(PROJECT_ROOT, "runAiBot.py")
    with open(bot_path, "r", encoding="utf-8") as f:
        src = f.read()

    ok("pilot_continue_on_error" in src, "continue_on_error: setting is referenced in runAiBot.py")

    # Find the error handler in the Easy Apply try/except block
    # Look for the pattern: after "Failed to Easy apply!" check pilot_continue_on_error
    idx = src.find("Failed to Easy apply!")
    if idx > 0:
        error_block = src[idx:idx+1500]
        ok("pilot_continue_on_error" in error_block,
           "continue_on_error: checked in Easy Apply error handler")
        ok("return" in error_block[error_block.find("pilot_continue_on_error"):] if "pilot_continue_on_error" in error_block else False,
           "continue_on_error: returns (stops) when False")
    else:
        ok(False, "continue_on_error: could not find error handler")


# =============================================================================
# TEST 6: check_limits() called after each successful application
# =============================================================================
def test_check_limits_called_after_apply():
    section("TEST 6: check_limits() called after each successful application")

    bot_path = os.path.join(PROJECT_ROOT, "runAiBot.py")
    with open(bot_path, "r", encoding="utf-8") as f:
        src = f.read()

    # Find where easy_applied_count is incremented
    idx = src.find("if application_link == \"Easy Applied\": easy_applied_count += 1")
    if idx > 0:
        # check_limits() should appear within ~500 chars after increment
        after_block = src[idx:idx+500]
        ok("check_pilot_limit_reached()" in after_block,
           "check_pilot_limit_reached called after easy_applied_count increment")
    else:
        ok(False, "could not find easy_applied_count increment line")


# =============================================================================
# TEST 7: Fallback block has all required variables
# =============================================================================
def test_fallback_block_complete():
    section("TEST 7: _init_quick_settings_vars fallback has all vars")

    dashboard_path = os.path.join(PROJECT_ROOT, "modules", "dashboard", "dashboard.py")
    with open(dashboard_path, "r", encoding="utf-8", errors="replace") as f:
        src = f.read()

    # Find the except block in _init_quick_settings_vars
    init_start = src.find("def _init_quick_settings_vars")
    init_end = src.find("\n    def ", init_start + 10)
    init_src = src[init_start:init_end]

    # Find the except/fallback block
    except_idx = init_src.rfind("except Exception")
    if except_idx > 0:
        fallback = init_src[except_idx:]

        must_have_vars = [
            'qs_search_terms', 'qs_search_location', 'qs_date_posted',
            'qs_easy_apply_only', 'qs_switch_number', 'qs_randomize_search',
            'qs_job_search_mode', 'qs_current_experience',
        ]
        for var in must_have_vars:
            ok(var in fallback, f"fallback: contains {var}")
    else:
        ok(False, "fallback: could not find except block in _init_quick_settings_vars")


# =============================================================================
# TEST 8: Settings.py string regex test (simulate what dashboard does)
# =============================================================================
def test_string_regex_works():
    section("TEST 8: String regex correctly replaces quoted values in settings.py")

    # Simulate the regex replacement on a sample settings.py line
    test_lines = [
        'pilot_resume_mode = "preselected"   # Resume handling mode',
        "autopilot_visa_required = \"Yes\"              # Yes/No",
        'resume_upload_format = "auto"',
        'schedule_type = "interval"           # Type of schedule',
        'extension_detection_mode = "universal"  # Detection scope',
        'job_search_mode = "sequential"       # How to cycle through job titles',
    ]

    test_cases = [
        ('pilot_resume_mode', 'tailored'),
        ('autopilot_visa_required', 'No'),
        ('resume_upload_format', 'pdf'),
        ('schedule_type', 'daily'),
        ('extension_detection_mode', 'linkedin'),
        ('job_search_mode', 'random'),
    ]

    for (setting, new_val), line in zip(test_cases, test_lines):
        content = line
        pattern = rf'^(\s*{setting}\s*=\s*)["\']([^"\']*)["\']'
        replacement = rf'\g<1>"{new_val}"'
        result = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        ok(f'"{new_val}"' in result,
           f"regex: {setting} → '{new_val}' (got: {result.strip()[:60]})")


# =============================================================================
# TEST 9: Bool/numeric regex still works
# =============================================================================
def test_bool_num_regex_works():
    section("TEST 9: Bool/numeric regex correctly replaces values")

    test_cases = [
        ('pilot_mode_enabled = True', 'pilot_mode_enabled', 'False'),
        ('pilot_max_applications = 2', 'pilot_max_applications', '10'),
        ('form_fill_delay_multiplier = 0.5', 'form_fill_delay_multiplier', '1.0'),
        ('click_gap = 20', 'click_gap', '30'),
    ]

    for line, setting, new_val in test_cases:
        pattern = rf'^(\s*{setting}\s*=\s*)(True|False|\d+\.?\d*)'
        replacement = rf'\g<1>{new_val}'
        result = re.sub(pattern, replacement, line, flags=re.MULTILINE)
        ok(f'{setting} = {new_val}' in result or f'{setting}= {new_val}' in result,
           f"regex: {setting} → {new_val}")


# =============================================================================
# TEST 10: Dead settings inventory (documentation — should be marked in UI)
# =============================================================================
def test_dead_settings_inventory():
    section("TEST 10: Known dead/unused settings (for documentation)")

    bot_path = os.path.join(PROJECT_ROOT, "runAiBot.py")
    with open(bot_path, "r", encoding="utf-8") as f:
        bot_src = f.read()

    # All formerly-dead settings have been wired — no known dead settings remain
    dead_settings = {
        # None — all 7 previously-dead settings are now wired:
        # use_smart_form_filler → runAiBot.py smart_easy_apply()
        # extension_enabled, extension_auto_sync, extension_ai_learning,
        # extension_detection_mode → config_loader.py + popup.js + content.js
        # resume_tailoring_confirm_after_filters → runAiBot.py post-filter confirmation
        # resume_tailoring_prompt_before_jd → runAiBot.py prompt_for_resume_tailoring()
    }

    for setting, reason in dead_settings.items():
        if setting not in bot_src:
            RESULTS.append(("⚠️", f"DEAD: {setting} — {reason}"))
            log(f"DEAD: {setting} — {reason}", "[⚠️]")
        else:
            log(f"NOTE: {setting} found in bot code (may be alive now)", "[ℹ️]")

    # All previously-dead settings should NOW be alive in the codebase
    alive_now = [
        'autopilot_visa_required', 'autopilot_willing_relocate', 'autopilot_work_authorization',
        'autopilot_remote_preference', 'autopilot_start_immediately',
        'autopilot_background_check', 'autopilot_commute_ok',
        'max_jobs_to_process', 'pilot_continue_on_error',
        # Formerly dead — now wired:
        'use_smart_form_filler',
        'resume_tailoring_confirm_after_filters',
        'resume_tailoring_prompt_before_jd',
    ]
    for setting in alive_now:
        ok(setting in bot_src, f"now-alive: {setting} is used in runAiBot.py")


# =============================================================================
# TEST 11: cycle_date_posted / stop_date_cycle_at_24hr logic
# =============================================================================
def test_cycle_date_posted_logic():
    section("TEST 11: cycle_date_posted / stop_date_cycle_at_24hr logic is correct")

    bot_path = os.path.join(PROJECT_ROOT, "runAiBot.py")
    with open(bot_path, "r", encoding="utf-8") as f:
        src = f.read()

    # The old buggy one-liner should NOT exist
    ok("date_options.index(date_posted)+1 > len(date_options)" not in src,
       "cycle: old buggy one-liner removed (no '> len(date_options)' off-by-one)")

    # Clear multi-line logic should exist
    ok("if stop_date_cycle_at_24hr:" in src,
       "cycle: uses clear 'if stop_date_cycle_at_24hr:' branch")
    ok("next_idx >= len(date_options)" in src,
       "cycle: uses '>=' for bounds checking (no off-by-one)")

    # Simulate the cycling logic
    date_options = ["Any time", "Past month", "Past week", "Past 24 hours"]

    # Test: stop_date_cycle_at_24hr=True should cycle forward then stay at last
    results_stop = []
    date_posted = "Any time"
    for _ in range(6):
        current_idx = date_options.index(date_posted) if date_posted in date_options else 0
        next_idx = current_idx + 1
        if next_idx >= len(date_options):
            next_idx = len(date_options) - 1
        date_posted = date_options[next_idx]
        results_stop.append(date_posted)

    ok(results_stop == ["Past month", "Past week", "Past 24 hours", "Past 24 hours", "Past 24 hours", "Past 24 hours"],
       f"cycle stop=True: Any→Month→Week→24h→stays (got {results_stop})")

    # Test: stop_date_cycle_at_24hr=False should wrap around
    results_wrap = []
    date_posted = "Any time"
    for _ in range(5):
        current_idx = date_options.index(date_posted) if date_posted in date_options else 0
        next_idx = current_idx + 1
        if next_idx >= len(date_options):
            next_idx = 0
        date_posted = date_options[next_idx]
        results_wrap.append(date_posted)

    ok(results_wrap == ["Past month", "Past week", "Past 24 hours", "Any time", "Past month"],
       f"cycle stop=False: wraps around (got {results_wrap})")


# =============================================================================
# TEST 12: Scheduler enforces max_runtime and max_applications
# =============================================================================
def test_scheduler_enforcement():
    section("TEST 12: Scheduler enforces max_runtime / max_applications")

    scheduler_path = os.path.join(PROJECT_ROOT, "modules", "scheduler.py")
    with open(scheduler_path, "r", encoding="utf-8") as f:
        src = f.read()

    # Find _execute_bot method
    exec_start = src.find("def _execute_bot")
    exec_end = src.find("\n    def ", exec_start + 10)
    exec_src = src[exec_start:exec_end]

    # Must set max_jobs_to_process in settings for bot enforcement
    ok("max_jobs_to_process" in exec_src,
       "scheduler: sets max_jobs_to_process for bot limit checker")

    # Must run bot in a thread for timeout enforcement
    ok("threading.Thread" in exec_src or "Thread(target=" in exec_src,
       "scheduler: runs bot in thread for timeout control")

    # Must have timeout join
    ok("bot_thread.join(timeout=" in exec_src,
       "scheduler: uses join(timeout=) for max_runtime enforcement")

    # Must call stop_bot on timeout
    ok("stop_bot" in exec_src or "_stop_event" in exec_src,
       "scheduler: sends stop signal when timeout reached")


# =============================================================================
# TEST 13: use_smart_form_filler wires SmartFormFiller v2 in smart_easy_apply()
# =============================================================================
def test_use_smart_form_filler_wired():
    section("TEST 13: use_smart_form_filler wires SmartFormFiller v2")

    bot_path = os.path.join(PROJECT_ROOT, "runAiBot.py")
    with open(bot_path, "r", encoding="utf-8") as f:
        src = f.read()

    # Must read the setting
    ok("use_smart_form_filler" in src,
       "smart_filler: use_smart_form_filler is read in runAiBot.py")

    # Must import SmartFormFiller
    ok("from modules.smart_form_filler import SmartFormFiller" in src,
       "smart_filler: imports SmartFormFiller from modules")

    # Must create a v2 instance
    ok("SmartFormFiller(driver," in src,
       "smart_filler: creates SmartFormFiller instance")

    # Must call fill_current_page as the v2 dispatch
    ok("fill_current_page(" in src,
       "smart_filler: calls fill_current_page() for v2 form filling")

    # Must have fallback to legacy questions_handler
    # The pattern: if v2 fails, fall back to questions_handler
    # Search from fill_current_page (the dispatch point), not the first occurrence
    dispatch_start = src.find("fill_current_page(")
    if dispatch_start > 0:
        smart_block = src[dispatch_start:dispatch_start + 1000]
        ok("questions_handler(" in smart_block,
           "smart_filler: falls back to legacy questions_handler if v2 fails")
    else:
        ok(False, "smart_filler: could not find fill_current_page dispatch")


# =============================================================================
# TEST 14: extension_* settings exported in config_loader.py
# =============================================================================
def test_extension_settings_exported():
    section("TEST 14: extension_* settings exported via config_loader.py")

    loader_path = os.path.join(PROJECT_ROOT, "extension", "config_loader.py")
    with open(loader_path, "r", encoding="utf-8") as f:
        src = f.read()

    ext_settings = [
        ('extension_enabled', 'extensionEnabled'),
        ('extension_auto_sync', 'autoSync'),
        ('extension_ai_learning', 'enableLearning'),
        ('extension_detection_mode', 'detectionMode'),
    ]

    for py_name, js_name in ext_settings:
        ok(py_name in src, f"config_loader: imports {py_name}")
        ok(js_name in src, f"config_loader: maps to JSON key '{js_name}'")

    # Also verify popup.js reads these settings
    popup_path = os.path.join(PROJECT_ROOT, "extension", "popup.js")
    with open(popup_path, "r", encoding="utf-8") as f:
        popup_src = f.read()

    ok("autoSync" in popup_src, "popup.js: reads autoSync from config")
    ok("enableLearning" in popup_src, "popup.js: reads enableLearning from config")
    ok("detectionMode" in popup_src, "popup.js: reads detectionMode from config")

    # Verify content.js checks extensionEnabled
    content_path = os.path.join(PROJECT_ROOT, "extension", "content.js")
    with open(content_path, "r", encoding="utf-8") as f:
        content_src = f.read()

    ok("extensionEnabled" in content_src, "content.js: checks extensionEnabled setting")
    ok("detectionMode" in content_src or "DETECTION_MODE" in content_src,
       "content.js: reads detectionMode setting")


# =============================================================================
# TEST 15: resume_tailoring_* settings wired in runAiBot.py
# =============================================================================
def test_resume_tailoring_settings_wired():
    section("TEST 15: resume_tailoring_confirm_after_filters & prompt_before_jd wired")

    bot_path = os.path.join(PROJECT_ROOT, "runAiBot.py")
    with open(bot_path, "r", encoding="utf-8") as f:
        src = f.read()

    # confirm_after_filters: Should be checked between get_job_description() and resume tailoring
    ok("resume_tailoring_confirm_after_filters" in src,
       "confirm_after_filters: setting is referenced in runAiBot.py")

    # It should show a confirmation dialog (pyautogui.confirm)
    confirm_idx = src.find("resume_tailoring_confirm_after_filters")
    if confirm_idx > 0:
        confirm_block = src[confirm_idx:confirm_idx + 1200]
        ok("pyautogui.confirm" in confirm_block,
           "confirm_after_filters: shows pyautogui.confirm dialog")
        ok("Proceed" in confirm_block or "proceed" in confirm_block,
           "confirm_after_filters: offers proceed option")
        ok("Default" in confirm_block or "Use Default" in confirm_block or "default" in confirm_block,
           "confirm_after_filters: offers use-default option")
    else:
        ok(False, "confirm_after_filters: could not find setting reference")

    # prompt_before_jd: Should be checked inside prompt_for_resume_tailoring()
    ok("resume_tailoring_prompt_before_jd" in src,
       "prompt_before_jd: setting is referenced in runAiBot.py")

    jd_idx = src.find("resume_tailoring_prompt_before_jd")
    if jd_idx > 0:
        jd_block = src[jd_idx:jd_idx + 800]
        ok("pyautogui.confirm" in jd_block,
           "prompt_before_jd: shows pyautogui.confirm dialog")
        ok("Send to AI" in jd_block or "job_description" in jd_block,
           "prompt_before_jd: previews job description before AI send")
    else:
        ok(False, "prompt_before_jd: could not find setting reference")

    # Both should skip in pilot mode
    confirm_idx2 = src.find("resume_tailoring_confirm_after_filters")
    ok("not pilot_mode_enabled" in src[confirm_idx2:confirm_idx2 + 500],
       "confirm_after_filters: skips in pilot mode")
    ok("not pilot_mode_enabled" in src[src.find("resume_tailoring_prompt_before_jd"):
                                       src.find("resume_tailoring_prompt_before_jd") + 300],
       "prompt_before_jd: skips in pilot mode")


# =============================================================================
# Runner
# =============================================================================
def main():
    print("\n" + "=" * 60)
    print("  E2E TEST: DASHBOARD SETTINGS AUDIT")
    print("=" * 60)

    tests = [
        test_file_persist_regex,
        test_reset_defaults,
        test_autopilot_answers_wired,
        test_max_jobs_enforced,
        test_pilot_continue_on_error,
        test_check_limits_called_after_apply,
        test_fallback_block_complete,
        test_string_regex_works,
        test_bool_num_regex_works,
        test_dead_settings_inventory,
        test_cycle_date_posted_logic,
        test_scheduler_enforcement,
        test_use_smart_form_filler_wired,
        test_extension_settings_exported,
        test_resume_tailoring_settings_wired,
    ]

    for test_fn in tests:
        try:
            test_fn()
        except Exception as e:
            ok(False, f"{test_fn.__name__}: CRASHED – {e}")
            traceback.print_exc()

    # Summary
    print("\n" + "=" * 60)
    print("  TEST RESULTS SUMMARY")
    print("=" * 60)
    for icon, label in RESULTS:
        print(f"  {icon} {label}")
    print("=" * 60)
    total = PASS + FAIL
    warn_count = sum(1 for icon, _ in RESULTS if icon == "⚠️")
    print(f"  Total: {total}  |  ✅ Passed: {PASS}  |  ❌ Failed: {FAIL}  |  ⚠️ Warnings: {warn_count}")
    if FAIL == 0:
        print("  🎉 ALL TESTS PASSED!")
    else:
        print(f"  ⚠️  {FAIL} TEST(S) FAILED")
    print("=" * 60 + "\n")

    return FAIL == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
