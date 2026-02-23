"""Shared runtime overrides for scheduled bot sessions."""

from __future__ import annotations

from typing import Any


def apply_scheduled_runtime_overrides(settings: Any, run_ai_bot: Any, max_jobs: int, schedule_resume_mode: str | None = None) -> None:
    """Apply consistent scheduler-safe runtime overrides for unattended runs."""
    settings.pilot_mode_enabled = True
    run_ai_bot.pilot_mode_enabled = True
    run_ai_bot.pause_before_submit = False
    run_ai_bot.pause_at_failed_question = False

    settings.pilot_max_applications = 0
    settings.run_non_stop = False
    run_ai_bot.run_non_stop = False

    if max_jobs > 0:
        settings.schedule_max_applications = max_jobs
        current_max = getattr(settings, "max_jobs_to_process", 0)
        if current_max == 0 or max_jobs < current_max:
            settings.max_jobs_to_process = max_jobs

    if schedule_resume_mode is not None:
        settings.pilot_resume_mode = schedule_resume_mode
