"""Prompt safety helpers for AI inputs."""
from __future__ import annotations

import re
from typing import Optional


def sanitize_prompt_input(text: Optional[str], max_len: int = 6000) -> str:
    """Normalize and limit text before sending to AI models."""
    if text is None:
        return ""
    value = str(text)
    # Remove null bytes and control chars (except newline/tab)
    value = value.replace("\x00", "")
    value = "".join(ch for ch in value if ch.isprintable() or ch in "\n\t")
    # Strip excessive whitespace
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    value = value.strip()
    # Limit length
    if len(value) > max_len:
        value = value[: max_len - 1] + "…"
    return value


def wrap_delimited(label: str, text: str) -> str:
    """Wrap text in explicit delimiters to reduce prompt injection risk."""
    safe_label = re.sub(r"[^A-Z0-9_]+", "_", label.upper()).strip("_") or "INPUT"
    return f"<<{safe_label}>>\n{text}\n<<END_{safe_label}>>"
