"""
Classified Retry Policy
========================
Provides structured, bounded-exponential-backoff retries with error classification.

Error Categories
----------------
TRANSIENT   – network blips, rate limits, server 5xx → retry with backoff
DETERMINISTIC – bad input, auth failure, form validation → do NOT retry
RESOURCE    – Chrome crash, OOM, file lock → limited retry then abort

Usage
-----
    from modules.retry_policy import retry, classify_error, RetryExhausted

    @retry(max_attempts=3, categories={"transient"})
    def call_api():
        ...

    # Or manual classification:
    cat = classify_error(some_exception)
    if cat == "transient":
        ...
"""

from __future__ import annotations

import functools
import logging
import random
import time
from typing import Callable, Iterable, Set

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Error classification
# ---------------------------------------------------------------------------

_TRANSIENT_MARKERS = frozenset([
    "ConnectionError", "ConnectionRefusedError", "NewConnectionError",
    "TimeoutError", "ReadTimeout", "ConnectTimeoutError",
    "HTTPError", "503", "502", "429", "RESOURCE_EXHAUSTED",
    "rate limit", "rate_limit", "quota", "temporarily unavailable",
    "SSLError", "ConnectionResetError", "BrokenPipeError",
    "RemoteDisconnected",
    "StaleElementReferenceException", "ElementNotInteractableException",
])

_DETERMINISTIC_MARKERS = frozenset([
    "ValueError", "KeyError", "TypeError", "AttributeError",
    "InvalidArgument", "400", "401", "403", "404",
    "INVALID_ARGUMENT", "PERMISSION_DENIED", "NOT_FOUND",
    "FieldSizeLimitError", "UnicodeDecodeError",
])

_RESOURCE_MARKERS = frozenset([
    "NoSuchWindowException", "WebDriverException", "SessionNotCreated",
    "chrome not reachable", "invalid session id", "MemoryError",
    "PermissionError", "OSError", "FileNotFoundError",
])


def classify_error(exc: BaseException) -> str:
    """Classify an exception as 'transient', 'deterministic', or 'resource'.

    Falls back to 'transient' for unknown errors (safe default for retries).
    """
    exc_text = f"{type(exc).__name__}: {exc}"

    for marker in _DETERMINISTIC_MARKERS:
        if marker.lower() in exc_text.lower():
            return "deterministic"

    for marker in _RESOURCE_MARKERS:
        if marker.lower() in exc_text.lower():
            return "resource"

    for marker in _TRANSIENT_MARKERS:
        if marker.lower() in exc_text.lower():
            return "transient"

    # Unknown errors — default to transient so callers can retry once
    return "transient"


# ---------------------------------------------------------------------------
# Retry decorator
# ---------------------------------------------------------------------------

class RetryExhausted(Exception):
    """Raised when all retry attempts have been exhausted."""

    def __init__(self, last_exception: BaseException, attempts: int):
        self.last_exception = last_exception
        self.attempts = attempts
        super().__init__(f"Retry exhausted after {attempts} attempts: {last_exception}")


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: float = 0.3,
    categories: Set[str] | None = None,
    on_retry: Callable | None = None,
):
    """Decorator: retry with bounded exponential backoff and error classification.

    Parameters
    ----------
    max_attempts : int
        Total try count (1 = no retry).
    base_delay : float
        Seconds before first retry.
    max_delay : float
        Upper bound on delay between retries.
    jitter : float
        Fraction of delay to randomise (0..1).
    categories : set[str] | None
        Which error categories to retry on.  Default: {"transient"}.
    on_retry : callable | None
        Optional ``fn(attempt, delay, exc)`` hook for logging / metrics.
    """
    if categories is None:
        categories = {"transient"}

    def decorator(fn: Callable):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    cat = classify_error(exc)

                    if cat not in categories:
                        # Not retryable — re-raise immediately
                        raise

                    if attempt >= max_attempts:
                        break

                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    if jitter > 0:
                        delay += delay * jitter * random.random()

                    if on_retry:
                        try:
                            on_retry(attempt, delay, exc)
                        except Exception:
                            pass

                    logger.warning(
                        "[retry %d/%d] %s (cat=%s) — waiting %.1fs",
                        attempt, max_attempts, exc, cat, delay,
                    )
                    time.sleep(delay)

            raise RetryExhausted(last_exc, max_attempts)
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Convenience: retryable wrapper for AI API calls
# ---------------------------------------------------------------------------

def retryable_ai_call(fn: Callable, *args, max_attempts: int = 3, **kwargs):
    """Call ``fn(*args, **kwargs)`` with classified retry.

    Returns the function result or raises RetryExhausted.
    """
    @retry(max_attempts=max_attempts, categories={"transient", "resource"})
    def _inner():
        return fn(*args, **kwargs)
    return _inner()
