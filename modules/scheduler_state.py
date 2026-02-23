"""
Centralized Scheduler State Manager
====================================
Single writer/reader for logs/scheduler_state.json.

Both run_scheduler.py and modules/scheduler.py MUST use this module
instead of touching the file directly, preventing schema drift and
race-condition overwrites.
"""

from __future__ import annotations

import json
import os
import threading
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_STATE_FILE = Path("logs/scheduler_state.json")


def _ensure_dir() -> None:
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_state() -> dict:
    """Read the current scheduler state (thread-safe)."""
    with _lock:
        try:
            if _STATE_FILE.exists():
                with open(_STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading scheduler state: {e}")
        return {}


def _write(state: dict) -> None:
    """Internal: atomically write state dict."""
    _ensure_dir()
    tmp = _STATE_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, default=str)
    # Atomic rename on POSIX; on Windows, replace is the closest
    try:
        tmp.replace(_STATE_FILE)
    except OSError:
        # Fallback for locked files on Windows
        import shutil
        shutil.move(str(tmp), str(_STATE_FILE))


def save_scheduler_tick(
    applications_today: int,
    last_run_date: Optional[str],
    next_scheduled_run: Optional[str],
) -> None:
    """Called by JobScheduler._save_state() on every scheduling tick."""
    with _lock:
        state = {}
        try:
            if _STATE_FILE.exists():
                with open(_STATE_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
        except Exception:
            state = {}

        state["applications_today"] = applications_today
        state["last_run_date"] = last_run_date
        state["last_run_time"] = datetime.now().isoformat()
        if next_scheduled_run is not None:
            state["next_scheduled_run"] = next_scheduled_run
        _write(state)


def save_session_report(
    session_start: datetime,
    session_end: datetime,
    successful: int,
    failed: int,
    exit_reason: str,
    errors: list[str] | None = None,
    session_id: str | None = None,
) -> None:
    """Called by run_scheduler._write_session_report() at session end."""
    with _lock:
        state = {}
        try:
            if _STATE_FILE.exists():
                with open(_STATE_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
        except Exception:
            state = {}

        duration = (session_end - session_start).total_seconds() / 60
        state["last_run"] = session_start.isoformat()
        state["last_run_end"] = session_end.isoformat()
        state["last_duration_minutes"] = round(duration, 1)
        state["last_successful"] = successful
        state["last_failed"] = failed
        state["last_exit_reason"] = exit_reason
        state["total_applications"] = state.get("total_applications", 0) + successful
        state["session_count"] = state.get("session_count", 0) + 1
        state["last_errors"] = (errors or [])[:5]
        if session_id:
            state["last_session_id"] = session_id
        _write(state)
        logger.info(f"State saved to {_STATE_FILE}")
