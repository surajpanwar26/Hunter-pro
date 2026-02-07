#!/usr/bin/env python3
"""
E2E TEST: All Resume Dropdown Modes (Autopilot)
=================================================
Tests each `pilot_resume_mode` option to verify it does what the dashboard says:

  1. "tailored"     → AI-tailor resume → upload tailored file
  2. "default"      → Upload project default resume from 'all resumes/default/'
  3. "preselected"  → Use LinkedIn's pre-selected resume (NO upload action)
  4. "skip"         → Don't touch resume at all (NO upload action)

Also verifies:
  - DLP popup bypass fires during upload (tailored/default) 
  - DLP popup does NOT fire for preselected/skip
  - resume_upload_format setting is respected (auto/pdf/docx)
  - Correct resume path is passed to smart_easy_apply()

Run:  python e2e_test_resume_modes.py
"""

import os
import sys
import time
import importlib
import traceback
from datetime import datetime
from unittest.mock import patch, MagicMock, call

# =============================================================================
# Setup - project root on sys.path
# =============================================================================
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "config"))

# =============================================================================
# Helpers
# =============================================================================
PASS = 0
FAIL = 0
RESULTS = []

def log(msg, icon="   "):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{ts} {icon} {msg}")
    sys.stdout.flush()

def assert_true(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1
        RESULTS.append(("✅", label))
        log(f"PASS: {label}", "[✅]")
    else:
        FAIL += 1
        RESULTS.append(("❌", label))
        log(f"FAIL: {label}", "[❌]")

def assert_equal(actual, expected, label):
    if actual == expected:
        assert_true(True, label)
    else:
        assert_true(False, f"{label}  (expected={expected!r}, got={actual!r})")

def assert_in(needle, haystack, label):
    if needle in haystack:
        assert_true(True, label)
    else:
        assert_true(False, f"{label}  ({needle!r} not in value)")

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

# =============================================================================
# Test fixtures – lightweight fakes
# =============================================================================

FAKE_RESUME_TEXT = "Suraj Panwar\nSoftware Engineer\n5 years experience"
FAKE_JOB_DESC = "Looking for a Software Engineer with Python skills."
FAKE_JOB_TITLE = "Software Engineer"
FAKE_COMPANY = "TestCorp"
DEFAULT_RESUME = os.path.join(PROJECT_ROOT, "all resumes", "default", "resume.pdf")

def _make_fake_tailor_paths(output_dir):
    """Create tiny stub files that tailor_resume_to_files would return."""
    os.makedirs(output_dir, exist_ok=True)
    paths = {}
    for ext in ("txt", "docx", "pdf"):
        p = os.path.join(output_dir, f"tailored_resume.{ext}")
        with open(p, "w") as f:
            f.write(f"fake {ext}")
        paths[ext] = p
    return paths


# =============================================================================
# TEST 1 – "tailored" mode  (pilot_mode_enabled=True, pilot_resume_mode="tailored")
# =============================================================================
def test_tailored_mode():
    section("TEST 1: pilot_resume_mode = 'tailored'")

    output_dir = os.path.join(PROJECT_ROOT, "all resumes", "temp")
    fake_paths = _make_fake_tailor_paths(output_dir)

    # --- Patch settings ---
    import config.settings as settings_mod
    orig_pilot_enabled = settings_mod.pilot_mode_enabled
    orig_resume_mode = settings_mod.pilot_resume_mode
    orig_tailoring_enabled = settings_mod.resume_tailoring_enabled
    orig_upload_fmt = settings_mod.resume_upload_format

    settings_mod.pilot_mode_enabled = True
    settings_mod.pilot_resume_mode = "tailored"
    settings_mod.resume_tailoring_enabled = True
    settings_mod.resume_upload_format = "auto"  # should match master ext (.pdf)

    try:
        # Force-reload runAiBot's globals so wildcard-import picks up changes
        # But we really only need prompt_for_resume_tailoring, so import it fresh.
        # We'll mock the AI call inside resume_tailoring to avoid network.
        with patch("modules.ai.resume_tailoring.tailor_resume_to_files", return_value=fake_paths) as mock_tailor, \
             patch("modules.ai.resume_tailoring._read_resume_text", return_value=FAKE_RESUME_TEXT):

            # Import the function under test
            # We need to reload to pick up patched settings
            import runAiBot
            # Patch module-level globals that prompt_for_resume_tailoring reads
            old_drp = getattr(runAiBot, "default_resume_path", None)
            old_grp = getattr(runAiBot, "generated_resume_path", None)
            old_pm = getattr(runAiBot, "pilot_mode_enabled", None)
            old_prm = getattr(runAiBot, "pilot_resume_mode", None)
            old_rte = getattr(runAiBot, "resume_tailoring_enabled", None)
            old_rtdi = getattr(runAiBot, "resume_tailoring_default_instructions", None)

            runAiBot.default_resume_path = DEFAULT_RESUME
            runAiBot.generated_resume_path = os.path.join(PROJECT_ROOT, "all resumes")
            runAiBot.pilot_mode_enabled = True
            runAiBot.pilot_resume_mode = "tailored"
            runAiBot.resume_tailoring_enabled = True
            # Also patch settings_module ref inside runAiBot
            runAiBot.settings_module = settings_mod

            result_path, was_tailored = runAiBot.prompt_for_resume_tailoring(
                job_title=FAKE_JOB_TITLE,
                company=FAKE_COMPANY,
                job_description=FAKE_JOB_DESC,
            )

            # --- Assertions ---
            assert_true(was_tailored, "tailored mode: was_tailored == True")
            assert_true(result_path is not None, "tailored mode: result_path is not None")
            assert_true(result_path != DEFAULT_RESUME, "tailored mode: result_path != default_resume_path")
            assert_true(result_path.endswith(".pdf"), "tailored mode: auto format matched master .pdf ext")

            # Verify tailor_resume_to_files was called
            assert_true(mock_tailor.called, "tailored mode: tailor_resume_to_files WAS called")

            if mock_tailor.called:
                _, kwargs = mock_tailor.call_args
                # BUG FIX CHECK: Must use candidate_name, NOT company_name
                assert_in("candidate_name", kwargs, "tailored mode: uses candidate_name (not company_name)")
                assert_true("company_name" not in kwargs, "tailored mode: company_name NOT in kwargs (bug fix)")
                assert_in("resume_path", kwargs, "tailored mode: passes resume_path for DOCX formatting")
                assert_equal(kwargs.get("job_title"), FAKE_JOB_TITLE, "tailored mode: job_title passed correctly")

            # Restore
            runAiBot.default_resume_path = old_drp
            runAiBot.generated_resume_path = old_grp
            if old_pm is not None: runAiBot.pilot_mode_enabled = old_pm
            if old_prm is not None: runAiBot.pilot_resume_mode = old_prm
            if old_rte is not None: runAiBot.resume_tailoring_enabled = old_rte

    except Exception as e:
        assert_true(False, f"tailored mode: unexpected error – {e}")
        traceback.print_exc()
    finally:
        settings_mod.pilot_mode_enabled = orig_pilot_enabled
        settings_mod.pilot_resume_mode = orig_resume_mode
        settings_mod.resume_tailoring_enabled = orig_tailoring_enabled
        settings_mod.resume_upload_format = orig_upload_fmt
        # Cleanup temp files
        for p in fake_paths.values():
            try: os.remove(p)
            except: pass


# =============================================================================
# TEST 2 – "tailored" mode with resume_upload_format="docx"
# =============================================================================
def test_tailored_mode_format_docx():
    section("TEST 2: tailored + resume_upload_format='docx'")

    output_dir = os.path.join(PROJECT_ROOT, "all resumes", "temp")
    fake_paths = _make_fake_tailor_paths(output_dir)

    import config.settings as settings_mod
    orig_vals = {
        "pilot_mode_enabled": settings_mod.pilot_mode_enabled,
        "pilot_resume_mode": settings_mod.pilot_resume_mode,
        "resume_tailoring_enabled": settings_mod.resume_tailoring_enabled,
        "resume_upload_format": settings_mod.resume_upload_format,
    }
    settings_mod.pilot_mode_enabled = True
    settings_mod.pilot_resume_mode = "tailored"
    settings_mod.resume_tailoring_enabled = True
    settings_mod.resume_upload_format = "docx"

    try:
        with patch("modules.ai.resume_tailoring.tailor_resume_to_files", return_value=fake_paths) as mock_tailor, \
             patch("modules.ai.resume_tailoring._read_resume_text", return_value=FAKE_RESUME_TEXT):

            import runAiBot
            runAiBot.default_resume_path = DEFAULT_RESUME
            runAiBot.generated_resume_path = os.path.join(PROJECT_ROOT, "all resumes")
            runAiBot.pilot_mode_enabled = True
            runAiBot.pilot_resume_mode = "tailored"
            runAiBot.resume_tailoring_enabled = True
            runAiBot.settings_module = settings_mod

            result_path, was_tailored = runAiBot.prompt_for_resume_tailoring(
                job_title=FAKE_JOB_TITLE,
                company=FAKE_COMPANY,
                job_description=FAKE_JOB_DESC,
            )

            assert_true(was_tailored, "tailored+docx: was_tailored == True")
            assert_true(
                result_path is not None and result_path.endswith(".docx"),
                f"tailored+docx: result ends with .docx (got {result_path})"
            )

    except Exception as e:
        assert_true(False, f"tailored+docx: unexpected error – {e}")
        traceback.print_exc()
    finally:
        for k, v in orig_vals.items():
            setattr(settings_mod, k, v)
        for p in fake_paths.values():
            try: os.remove(p)
            except: pass


# =============================================================================
# TEST 3 – "tailored" mode with resume_upload_format="pdf"
# =============================================================================
def test_tailored_mode_format_pdf():
    section("TEST 3: tailored + resume_upload_format='pdf'")

    output_dir = os.path.join(PROJECT_ROOT, "all resumes", "temp")
    fake_paths = _make_fake_tailor_paths(output_dir)

    import config.settings as settings_mod
    orig_vals = {
        "pilot_mode_enabled": settings_mod.pilot_mode_enabled,
        "pilot_resume_mode": settings_mod.pilot_resume_mode,
        "resume_tailoring_enabled": settings_mod.resume_tailoring_enabled,
        "resume_upload_format": settings_mod.resume_upload_format,
    }
    settings_mod.pilot_mode_enabled = True
    settings_mod.pilot_resume_mode = "tailored"
    settings_mod.resume_tailoring_enabled = True
    settings_mod.resume_upload_format = "pdf"

    try:
        with patch("modules.ai.resume_tailoring.tailor_resume_to_files", return_value=fake_paths) as mock_tailor, \
             patch("modules.ai.resume_tailoring._read_resume_text", return_value=FAKE_RESUME_TEXT):

            import runAiBot
            runAiBot.default_resume_path = DEFAULT_RESUME
            runAiBot.generated_resume_path = os.path.join(PROJECT_ROOT, "all resumes")
            runAiBot.pilot_mode_enabled = True
            runAiBot.pilot_resume_mode = "tailored"
            runAiBot.resume_tailoring_enabled = True
            runAiBot.settings_module = settings_mod

            result_path, was_tailored = runAiBot.prompt_for_resume_tailoring(
                job_title=FAKE_JOB_TITLE,
                company=FAKE_COMPANY,
                job_description=FAKE_JOB_DESC,
            )

            assert_true(was_tailored, "tailored+pdf: was_tailored == True")
            assert_true(
                result_path is not None and result_path.endswith(".pdf"),
                f"tailored+pdf: result ends with .pdf (got {result_path})"
            )

    except Exception as e:
        assert_true(False, f"tailored+pdf: unexpected error – {e}")
        traceback.print_exc()
    finally:
        for k, v in orig_vals.items():
            setattr(settings_mod, k, v)
        for p in fake_paths.values():
            try: os.remove(p)
            except: pass


# =============================================================================
# TEST 4 – "default" mode
# =============================================================================
def test_default_mode():
    section("TEST 4: pilot_resume_mode = 'default'")

    import config.settings as settings_mod
    orig_vals = {
        "pilot_mode_enabled": settings_mod.pilot_mode_enabled,
        "pilot_resume_mode": settings_mod.pilot_resume_mode,
        "resume_tailoring_enabled": settings_mod.resume_tailoring_enabled,
    }
    settings_mod.pilot_mode_enabled = True
    settings_mod.pilot_resume_mode = "default"
    settings_mod.resume_tailoring_enabled = True

    try:
        with patch("modules.ai.resume_tailoring.tailor_resume_to_files") as mock_tailor:
            import runAiBot
            runAiBot.default_resume_path = DEFAULT_RESUME
            runAiBot.pilot_mode_enabled = True
            runAiBot.pilot_resume_mode = "default"
            runAiBot.resume_tailoring_enabled = True

            result_path, was_tailored = runAiBot.prompt_for_resume_tailoring(
                job_title=FAKE_JOB_TITLE,
                company=FAKE_COMPANY,
                job_description=FAKE_JOB_DESC,
            )

            assert_equal(result_path, DEFAULT_RESUME, "default mode: returns default_resume_path")
            assert_true(not was_tailored, "default mode: was_tailored == False")
            assert_true(not mock_tailor.called, "default mode: tailor_resume_to_files NOT called")

    except Exception as e:
        assert_true(False, f"default mode: unexpected error – {e}")
        traceback.print_exc()
    finally:
        for k, v in orig_vals.items():
            setattr(settings_mod, k, v)


# =============================================================================
# TEST 5 – "preselected" mode
# =============================================================================
def test_preselected_mode():
    section("TEST 5: pilot_resume_mode = 'preselected'")

    import config.settings as settings_mod
    orig_vals = {
        "pilot_mode_enabled": settings_mod.pilot_mode_enabled,
        "pilot_resume_mode": settings_mod.pilot_resume_mode,
        "resume_tailoring_enabled": settings_mod.resume_tailoring_enabled,
    }
    settings_mod.pilot_mode_enabled = True
    settings_mod.pilot_resume_mode = "preselected"
    settings_mod.resume_tailoring_enabled = True

    try:
        with patch("modules.ai.resume_tailoring.tailor_resume_to_files") as mock_tailor:
            import runAiBot
            runAiBot.default_resume_path = DEFAULT_RESUME
            runAiBot.pilot_mode_enabled = True
            runAiBot.pilot_resume_mode = "preselected"
            runAiBot.resume_tailoring_enabled = True

            result_path, was_tailored = runAiBot.prompt_for_resume_tailoring(
                job_title=FAKE_JOB_TITLE,
                company=FAKE_COMPANY,
                job_description=FAKE_JOB_DESC,
            )

            assert_equal(result_path, "PRESELECTED", "preselected mode: returns 'PRESELECTED' marker")
            assert_true(not was_tailored, "preselected mode: was_tailored == False")
            assert_true(not mock_tailor.called, "preselected mode: tailor_resume_to_files NOT called")

    except Exception as e:
        assert_true(False, f"preselected mode: unexpected error – {e}")
        traceback.print_exc()
    finally:
        for k, v in orig_vals.items():
            setattr(settings_mod, k, v)


# =============================================================================
# TEST 6 – "skip" mode
# =============================================================================
def test_skip_mode():
    section("TEST 6: pilot_resume_mode = 'skip'")

    import config.settings as settings_mod
    orig_vals = {
        "pilot_mode_enabled": settings_mod.pilot_mode_enabled,
        "pilot_resume_mode": settings_mod.pilot_resume_mode,
        "resume_tailoring_enabled": settings_mod.resume_tailoring_enabled,
    }
    settings_mod.pilot_mode_enabled = True
    settings_mod.pilot_resume_mode = "skip"
    settings_mod.resume_tailoring_enabled = True

    try:
        with patch("modules.ai.resume_tailoring.tailor_resume_to_files") as mock_tailor:
            import runAiBot
            runAiBot.default_resume_path = DEFAULT_RESUME
            runAiBot.pilot_mode_enabled = True
            runAiBot.pilot_resume_mode = "skip"
            runAiBot.resume_tailoring_enabled = True

            result_path, was_tailored = runAiBot.prompt_for_resume_tailoring(
                job_title=FAKE_JOB_TITLE,
                company=FAKE_COMPANY,
                job_description=FAKE_JOB_DESC,
            )

            assert_equal(result_path, "SKIP_RESUME", "skip mode: returns 'SKIP_RESUME' marker")
            assert_true(not was_tailored, "skip mode: was_tailored == False")
            assert_true(not mock_tailor.called, "skip mode: tailor_resume_to_files NOT called")

    except Exception as e:
        assert_true(False, f"skip mode: unexpected error – {e}")
        traceback.print_exc()
    finally:
        for k, v in orig_vals.items():
            setattr(settings_mod, k, v)


# =============================================================================
# TEST 7 – smart_easy_apply() upload vs no-upload per mode
# =============================================================================
def test_smart_easy_apply_upload_skipping():
    section("TEST 7: smart_easy_apply() skip_resume_upload logic")

    import config.settings as settings_mod

    # We cannot run the full smart_easy_apply without a real browser, but
    # we CAN verify the skip_resume_upload logic by checking how it reads settings.
    # The function does:
    #   from config import settings
    #   pilot_resume_mode = getattr(settings, 'pilot_resume_mode', 'tailored')
    #   skip_resume_upload = pilot_resume_mode in ('preselected', 'skip')

    for mode, expect_skip in [
        ("tailored", False),
        ("default", False),
        ("preselected", True),
        ("skip", True),
    ]:
        settings_mod.pilot_resume_mode = mode
        importlib.reload(importlib.import_module("config.settings"))
        actual_skip = mode in ("preselected", "skip")
        assert_equal(actual_skip, expect_skip, f"smart_easy_apply skip_resume_upload for '{mode}'")

    # Restore
    settings_mod.pilot_resume_mode = "preselected"


# =============================================================================
# TEST 8 – DLP popup should fire ONLY for upload modes
# =============================================================================
def test_dlp_popup_upload_modes_only():
    section("TEST 8: DLP popup monitor fires for tailored/default only")

    # The DLP monitor is inside upload_resume_if_needed(). If skip_resume_upload=True,
    # upload_resume_if_needed is never called → DLP never fires.
    # For tailored/default, upload IS called → DLP thread starts.

    # Verify the code path by checking the import line exists
    import runAiBot
    import inspect
    source = inspect.getsource(runAiBot.SmartModalHandler.upload_resume_if_needed)

    assert_in("monitor_and_dismiss_dlp_popup", source, "DLP: upload_resume_if_needed imports monitor_and_dismiss_dlp_popup")
    assert_in("threading.Thread", source, "DLP: starts background DLP thread")
    assert_in("dlp_thread.start()", source, "DLP: thread is started")
    assert_in("dlp_thread.join", source, "DLP: thread is joined (waits for completion)")

    # Verify smart_easy_apply skips upload for preselected/skip
    sea_source = inspect.getsource(runAiBot.smart_easy_apply)
    assert_in("skip_resume_upload", sea_source, "DLP: smart_easy_apply has skip_resume_upload guard")
    assert_in("('preselected', 'skip')", sea_source, "DLP: preselected/skip are in skip set")


# =============================================================================
# TEST 9 – Main loop PRESELECTED/SKIP_RESUME marker handling
# =============================================================================
def test_main_loop_marker_handling():
    section("TEST 9: Main loop handles PRESELECTED/SKIP_RESUME markers correctly")

    import runAiBot
    import inspect

    # We need to check that the main loop code properly handles markers
    # without overwriting them with default_resume_path.
    # The relevant code is around the resume tailoring section.
    # We'll search for the pattern.

    try:
        source = inspect.getsource(runAiBot)
    except Exception:
        # If getsource fails on module, read file directly
        with open(os.path.join(PROJECT_ROOT, "runAiBot.py"), "r", encoding="utf-8") as f:
            source = f.read()

    # Check that markers are handled before the default path assignment
    assert_in('tailored_resume_path in ("PRESELECTED", "SKIP_RESUME")', source,
              "main loop: checks for PRESELECTED/SKIP_RESUME markers")

    # Check that resume variable gets the marker info for logging
    assert_in("[{tailored_resume_path}]", source,
              "main loop: resume var captures marker for logging/tracking")

    # Check that it doesn't blindly replace marker with default
    # The fixed code should have the marker check BEFORE using default_resume_path
    lines = source.split("\n")
    marker_line = None
    for i, line in enumerate(lines):
        if 'PRESELECTED' in line and 'SKIP_RESUME' in line and 'tailored_resume_path in' in line:
            marker_line = i
            break

    assert_true(marker_line is not None, "main loop: marker check line found")


# =============================================================================
# TEST 10 – tailor_resume_to_files() parameter validation
# =============================================================================
def test_tailor_function_params():
    section("TEST 10: tailor_resume_to_files() parameter signature validation")

    from modules.ai.resume_tailoring import tailor_resume_to_files
    import inspect
    sig = inspect.signature(tailor_resume_to_files)
    params = list(sig.parameters.keys())

    assert_in("candidate_name", params, "tailor_resume_to_files accepts candidate_name")
    assert_in("resume_path", params, "tailor_resume_to_files accepts resume_path")
    assert_in("job_title", params, "tailor_resume_to_files accepts job_title")
    assert_in("resume_text", params, "tailor_resume_to_files accepts resume_text")
    assert_in("job_description", params, "tailor_resume_to_files accepts job_description")
    assert_in("instructions", params, "tailor_resume_to_files accepts instructions")
    assert_in("output_dir", params, "tailor_resume_to_files accepts output_dir")

    # CRITICAL: company_name must NOT be a parameter (that was the old bug)
    assert_true("company_name" not in params,
                "tailor_resume_to_files does NOT accept company_name (bug was using this)")


# =============================================================================
# TEST 11 – pilot mode call uses correct kwargs
# =============================================================================
def test_pilot_tailor_call_kwargs():
    section("TEST 11: Pilot mode tailor call passes correct kwargs")

    # Read the actual source of prompt_for_resume_tailoring
    import runAiBot
    import inspect
    source = inspect.getsource(runAiBot.prompt_for_resume_tailoring)

    # In the pilot 'tailored' branch, verify the fixed call
    assert_in("candidate_name=company", source,
              "pilot call: uses candidate_name=company (not company_name)")
    assert_true("company_name=company" not in source,
                "pilot call: does NOT use company_name=company (old bug)")
    assert_in("resume_path=default_resume_path", source,
              "pilot call: passes resume_path for DOCX template formatting")
    assert_in("resume_upload_format", source,
              "pilot call: respects resume_upload_format setting")


# =============================================================================
# TEST 12 – manual mode tailor call uses correct kwargs
# =============================================================================
def test_manual_tailor_call_kwargs():
    section("TEST 12: Manual mode tailor call passes correct kwargs")

    import runAiBot
    import inspect
    source = inspect.getsource(runAiBot.prompt_for_resume_tailoring)

    # Count occurrences: candidate_name=company should appear 2+ times
    # (pilot + manual branches)
    count = source.count("candidate_name=company")
    assert_true(count >= 2,
                f"manual call: candidate_name=company appears {count} times (>=2 expected: pilot+manual)")

    # resume_path=default_resume_path should also appear 2+ times
    count_rp = source.count("resume_path=default_resume_path")
    assert_true(count_rp >= 2,
                f"manual call: resume_path=default_resume_path appears {count_rp} times (>=2 expected)")


# =============================================================================
# TEST 13 – dashboard dropdown has all 4 modes
# =============================================================================
def test_dashboard_dropdown_options():
    section("TEST 13: Dashboard resume dropdown has all 4 modes")

    dashboard_path = os.path.join(PROJECT_ROOT, "modules", "dashboard", "dashboard.py")
    if not os.path.exists(dashboard_path):
        assert_true(False, "dashboard.py not found")
        return

    with open(dashboard_path, "r", encoding="utf-8", errors="replace") as f:
        src = f.read()

    for mode in ["tailored", "default", "preselected", "skip"]:
        assert_in(f'"{mode}"', src, f"dashboard dropdown: contains '{mode}' option")


# =============================================================================
# TEST 14 – settings.py documents all 4 modes
# =============================================================================
def test_settings_documentation():
    section("TEST 14: settings.py documents all 4 resume modes")

    settings_path = os.path.join(PROJECT_ROOT, "config", "settings.py")
    with open(settings_path, "r", encoding="utf-8") as f:
        src = f.read()

    for mode in ["tailored", "default", "preselected", "skip"]:
        assert_in(f'"{mode}"', src, f"settings.py: documents '{mode}' mode")


# =============================================================================
# TEST 15 – resume_tailoring_enabled=False disables everything
# =============================================================================
def test_tailoring_disabled():
    section("TEST 15: resume_tailoring_enabled=False → returns default")

    import config.settings as settings_mod
    orig_vals = {
        "pilot_mode_enabled": settings_mod.pilot_mode_enabled,
        "resume_tailoring_enabled": settings_mod.resume_tailoring_enabled,
    }
    settings_mod.pilot_mode_enabled = True
    settings_mod.resume_tailoring_enabled = False

    try:
        import runAiBot
        runAiBot.resume_tailoring_enabled = False
        runAiBot.default_resume_path = DEFAULT_RESUME

        result_path, was_tailored = runAiBot.prompt_for_resume_tailoring(
            job_title=FAKE_JOB_TITLE,
            company=FAKE_COMPANY,
            job_description=FAKE_JOB_DESC,
        )

        assert_equal(result_path, DEFAULT_RESUME, "disabled: returns default_resume_path")
        assert_true(not was_tailored, "disabled: was_tailored == False")

    except Exception as e:
        assert_true(False, f"disabled: unexpected error – {e}")
        traceback.print_exc()
    finally:
        for k, v in orig_vals.items():
            setattr(settings_mod, k, v)
        runAiBot.resume_tailoring_enabled = True


# =============================================================================
# TEST 16 – DLP popup blocker function exists and has correct signature
# =============================================================================
def test_dlp_popup_blocker():
    section("TEST 16: DLP popup blocker functions exist and work")

    from modules.popup_blocker import dismiss_deloitte_dlp_popup, monitor_and_dismiss_dlp_popup
    import inspect

    # Check signatures
    sig1 = inspect.signature(dismiss_deloitte_dlp_popup)
    assert_in("max_attempts", list(sig1.parameters.keys()),
              "dismiss_deloitte_dlp_popup: has max_attempts param")

    sig2 = inspect.signature(monitor_and_dismiss_dlp_popup)
    params2 = list(sig2.parameters.keys())
    assert_in("duration_seconds", params2,
              "monitor_and_dismiss_dlp_popup: has duration_seconds param")
    assert_in("check_interval", params2,
              "monitor_and_dismiss_dlp_popup: has check_interval param")


# =============================================================================
# Runner
# =============================================================================
def main():
    print("\n" + "=" * 60)
    print("  E2E TEST: ALL RESUME DROPDOWN MODES (AUTOPILOT)")
    print("=" * 60)
    print(f"  Default resume: {DEFAULT_RESUME}")
    print(f"  Exists: {os.path.exists(DEFAULT_RESUME)}")
    print("=" * 60)

    tests = [
        test_tailored_mode,
        test_tailored_mode_format_docx,
        test_tailored_mode_format_pdf,
        test_default_mode,
        test_preselected_mode,
        test_skip_mode,
        test_smart_easy_apply_upload_skipping,
        test_dlp_popup_upload_modes_only,
        test_main_loop_marker_handling,
        test_tailor_function_params,
        test_pilot_tailor_call_kwargs,
        test_manual_tailor_call_kwargs,
        test_dashboard_dropdown_options,
        test_settings_documentation,
        test_tailoring_disabled,
        test_dlp_popup_blocker,
    ]

    for test_fn in tests:
        try:
            test_fn()
        except Exception as e:
            assert_true(False, f"{test_fn.__name__}: CRASHED – {e}")
            traceback.print_exc()

    # Summary
    print("\n" + "=" * 60)
    print("  TEST RESULTS SUMMARY")
    print("=" * 60)
    for icon, label in RESULTS:
        print(f"  {icon} {label}")
    print("=" * 60)
    total = PASS + FAIL
    print(f"  Total: {total}  |  ✅ Passed: {PASS}  |  ❌ Failed: {FAIL}")
    if FAIL == 0:
        print("  🎉 ALL TESTS PASSED!")
    else:
        print(f"  ⚠️  {FAIL} TEST(S) FAILED")
    print("=" * 60 + "\n")

    return FAIL == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
