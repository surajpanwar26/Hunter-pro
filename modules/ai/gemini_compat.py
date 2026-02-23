"""
Gemini SDK Migration Compatibility Layer
==========================================
google.generativeai (legacy) → google.genai (new unified SDK)

The ``google.generativeai`` package is deprecated and will stop receiving
updates.  The replacement is ``google.genai`` (part of google-genai).

This module provides a **thin adapter** so the rest of the codebase can
import from here and work with *either* SDK — whichever is installed.

Migration Plan
--------------
Phase 1 (NOW):   Add this shim.  ``geminiConnections.py`` still imports
                 the legacy SDK directly but the shim is available for
                 new code.
Phase 2 (NEXT):  Switch ``geminiConnections.py`` to import from this
                 module instead of ``google.generativeai``.
Phase 3 (FINAL): Remove legacy ``google.generativeai`` from
                 requirements.txt and delete the fallback path below.

Install the new SDK:
    pip install google-genai

Reference:
    https://ai.google.dev/gemini-api/docs/migrate
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Try new SDK first, fall back to legacy
# ---------------------------------------------------------------------------

_USE_NEW_SDK = False
genai: Any = None

try:
    from google import genai as _new_genai  # type: ignore[import]
    genai = _new_genai
    _USE_NEW_SDK = True
    logger.info("Using NEW google.genai SDK (google-genai)")
except ImportError:
    try:
        import google.generativeai as _legacy_genai  # type: ignore[import]
        genai = _legacy_genai
        _USE_NEW_SDK = False
        logger.info("Using LEGACY google.generativeai SDK (will be deprecated)")
    except ImportError:
        logger.warning("Neither google-genai nor google-generativeai is installed")
        genai = None


def is_new_sdk() -> bool:
    """Return True if the new google.genai SDK is active."""
    return _USE_NEW_SDK


def configure(api_key: str) -> None:
    """Configure the active SDK with an API key."""
    if genai is None:
        raise ImportError("No Gemini SDK installed. Run: pip install google-genai")
    if _USE_NEW_SDK:
        # New SDK uses client-based approach
        pass  # Client is created per-call in new SDK
    else:
        genai.configure(api_key=api_key)


def list_models() -> list[str]:
    """List available model names."""
    if genai is None:
        return []
    if _USE_NEW_SDK:
        client = genai.Client()
        return [m.name for m in client.models.list()]
    else:
        return [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]


def create_model(model_name: str, api_key: str | None = None):
    """Return a model handle compatible with generate_content()."""
    if genai is None:
        raise ImportError("No Gemini SDK installed")
    if _USE_NEW_SDK:
        # New SDK: return a client + model_name tuple (adapter pattern)
        return _NewSdkModelAdapter(model_name, api_key)
    else:
        return genai.GenerativeModel(model_name)


class _NewSdkModelAdapter:
    """Wraps the new google.genai Client to match the legacy GenerativeModel interface."""

    def __init__(self, model_name: str, api_key: str | None = None):
        self._model = model_name
        self._client = genai.Client(api_key=api_key) if api_key else genai.Client()

    def generate_content(self, prompt: str, safety_settings=None, **kwargs):
        """Mimic legacy GenerativeModel.generate_content()."""
        config = {}
        if safety_settings:
            config["safety_settings"] = safety_settings
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=config if config else None,
        )
        return response
