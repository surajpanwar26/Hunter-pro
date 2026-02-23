"""
Bot Session Context
====================
Per-session runtime object that replaces bare global mutable flags in runAiBot.

Usage
-----
    from modules.bot_session import current_session, new_session

    ctx = new_session()          # creates a fresh context (returns BotSessionContext)
    ctx = current_session()      # returns the active context (or a default one)

The old global-variable approach stays wired for backward compatibility:
runAiBot module-level globals still exist and are referenced by hundreds of
lines.  This module provides a migration bridge — new code can read/write
through the context object, and `sync_to_globals(runAiBot)` copies the
context values onto the module's namespace so legacy code keeps working.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class BotSessionContext:
    """Immutable-id, mutable-counters runtime context for one bot session."""

    # ---- identity (set once) ----
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # ---- counters ----
    easy_applied_count: int = 0
    external_jobs_count: int = 0
    failed_count: int = 0
    skip_count: int = 0
    tabs_count: int = 1

    # ---- flags ----
    pause_before_submit: bool = False
    pause_at_failed_question: bool = False
    use_new_resume: bool = True
    easy_apply_active: bool = False
    daily_limit_reached: bool = False
    run_non_stop: bool = False

    # ---- stop / pause (thread-safe) ----
    _stop_event: Optional[threading.Event] = field(default=None, repr=False)
    _pause_flag: bool = False
    _skip_current: bool = False

    # ---- randomly answered questions ----
    randomly_answered_questions: set = field(default_factory=set)

    def should_stop(self) -> bool:
        return self._stop_event is not None and self._stop_event.is_set()

    def reset_counters(self) -> None:
        """Reset mutable counters for a fresh run inside the same session."""
        self.easy_applied_count = 0
        self.external_jobs_count = 0
        self.failed_count = 0
        self.skip_count = 0
        self.tabs_count = 1
        self.daily_limit_reached = False
        self.randomly_answered_questions = set()

    def sync_to_globals(self, module) -> None:
        """Copy session values onto a module's namespace (backward compat)."""
        module.easy_applied_count = self.easy_applied_count
        module.external_jobs_count = self.external_jobs_count
        module.failed_count = self.failed_count
        module.skip_count = self.skip_count
        module.tabs_count = self.tabs_count
        module.pause_before_submit = self.pause_before_submit
        module.pause_at_failed_question = self.pause_at_failed_question
        module.useNewResume = self.use_new_resume
        module.easy_apply_active = self.easy_apply_active
        module.dailyEasyApplyLimitReached = self.daily_limit_reached
        module.randomly_answered_questions = self.randomly_answered_questions

    def sync_from_globals(self, module) -> None:
        """Pull current global values back into the context (after a run)."""
        self.easy_applied_count = getattr(module, "easy_applied_count", 0)
        self.external_jobs_count = getattr(module, "external_jobs_count", 0)
        self.failed_count = getattr(module, "failed_count", 0)
        self.skip_count = getattr(module, "skip_count", 0)
        self.tabs_count = getattr(module, "tabs_count", 1)
        self.daily_limit_reached = getattr(module, "dailyEasyApplyLimitReached", False)
        self.randomly_answered_questions = getattr(module, "randomly_answered_questions", set())


# ---- module-level singleton ----

_current: Optional[BotSessionContext] = None
_lock = threading.Lock()


def new_session(**overrides) -> BotSessionContext:
    """Create and activate a new session context."""
    global _current
    with _lock:
        _current = BotSessionContext(**overrides)
        return _current


def current_session() -> BotSessionContext:
    """Return the active session context (creates a default if none exists)."""
    global _current
    if _current is None:
        with _lock:
            if _current is None:
                _current = BotSessionContext()
    return _current


def get_session_id() -> str:
    """Convenience: return the current session's correlation ID."""
    return current_session().session_id
