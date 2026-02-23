"""
Self-Learning Answer Store for LinkedIn Auto Job Applier.

This module provides a persistent, evolving answer database that:
1. Stores answers the bot discovers or the user corrects
2. Loads them on startup so the bot improves over time
3. Prioritises learned answers over defaults
4. Supports all question types: text, select, radio, textarea, checkbox
5. De-duplicates labels via canonical normalization so the file doesn't bloat

File: config/learned_answers.json
"""

import json
import os
import re
import threading
from datetime import datetime

# Path to the learned answers file
LEARNED_ANSWERS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config", "learned_answers.json"
)

# In-memory cache
_cache: dict = {}
_lock = threading.Lock()
_dirty = False  # Track unsaved changes

# ---------------------------------------------------------------------------
# Label normalisation helpers — prevents near-duplicate entries
# ---------------------------------------------------------------------------
_STOPWORDS = frozenset({
    "a", "an", "the", "to", "in", "on", "for", "of", "and", "or",
    "is", "are", "you", "your", "do", "does", "can", "will", "would",
    "should", "be", "legally", "please", "provide", "enter", "what",
    "how", "many", "this", "that", "with",
})

_SUFFIX_RE = re.compile(
    r"(ization|isation|ation|ized|ised|ing|ed|es|s)$", re.IGNORECASE
)

# Words that should NEVER be stemmed because stripping suffixes
# creates false collisions or destroys meaning
_STEM_PROTECTED = frozenset({
    "authorized", "authorised", "address", "glasses", "business",
    "process", "success", "access", "unless", "express", "status",
    "campus", "bonus", "series", "species", "basis", "analysis",
    "thesis", "crisis", "diabetes", "previous", "various",
    "serious", "religious", "services", "resources", "experiences",
    "languages", "references", "ages", "wages", "stages", "changes",
    "charges", "ranges", "manages", "technologies", "companies",
})


def _normalize_label(label: str) -> str:
    """Return a canonical form of *label* for storage & lookup.

    Steps:
    1. Strip, lowercase.
    2. Remove trailing punctuation (?, *, :, .).
    3. Remove content inside square brackets (option lists).
    4. Collapse whitespace.
    5. Drop stopwords and light-stem remaining tokens.
       Protected words are NOT stemmed to avoid false collisions.

    This matches the dedup logic in api_server.py so bot-learned and
    extension-synced entries converge on the same key.
    """
    text = label.strip().lower()
    # Remove trailing punctuation
    text = text.rstrip("?*:. ")
    # Remove content in square brackets like "[ option1, option2 ]"
    text = re.sub(r"\[.*?\]", "", text).strip()
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Tokenize, drop stopwords, light-stem (with protection)
    tokens = []
    for tok in text.split():
        if tok in _STOPWORDS:
            continue
        # Only stem if NOT in protected set and long enough
        if tok not in _STEM_PROTECTED and len(tok) > 4:
            stemmed = _SUFFIX_RE.sub("", tok)
        else:
            stemmed = tok
        if stemmed:
            tokens.append(stemmed)
    return " ".join(tokens).strip() if tokens else text


def _find_existing_key(bucket: dict, canonical: str) -> str | None:
    """Find an existing key in *bucket* whose canonical form matches.

    Returns the raw key string if found, else None.
    """
    for existing_key in bucket:
        if _normalize_label(existing_key) == canonical:
            return existing_key
    return None


# Bucket name mapping (shared by get_answer / learn)
_TYPE_MAP = {
    "text": "text_answers",
    "select": "select_answers",
    "radio": "radio_answers",
    "textarea": "textarea_answers",
    "checkbox": "checkbox_answers",
    "dropdown": "dropdown_mappings",
    "dropdown_mappings": "dropdown_mappings",
}


def _default_structure() -> dict:
    """Return the default empty structure for learned answers."""
    return {
        "_description": "Auto-saved answers from user interventions and bot learning. Edit manually if needed.",
        "_last_updated": "",
        "text_answers": {},       # label -> answer
        "select_answers": {},     # label -> selected option text
        "radio_answers": {},      # label -> selected option text
        "textarea_answers": {},   # label -> answer
        "checkbox_answers": {},   # label -> "checked" or "unchecked"
        "education": {},          # Pre-filled from config, updated by bot
        "dropdown_mappings": {},  # label -> option text (for tricky dropdowns like email, country code)
    }


def load() -> dict:
    """Load learned answers from disk into memory cache.

    Returns the full learned answers dict. Safe to call multiple times.
    """
    global _cache
    with _lock:
        if _cache:
            return _cache

        if os.path.exists(LEARNED_ANSWERS_FILE):
            try:
                with open(LEARNED_ANSWERS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # Ensure all keys exist (forward-compatible)
                defaults = _default_structure()
                for key in defaults:
                    if key not in data:
                        data[key] = defaults[key]
                _cache = data
            except (json.JSONDecodeError, OSError) as e:
                print(f"[SelfLearning] ⚠️ Could not load {LEARNED_ANSWERS_FILE}: {e}")
                _cache = _default_structure()
        else:
            _cache = _default_structure()

        return _cache


def save():
    """Persist the current cache to disk."""
    global _dirty
    with _lock:
        if not _cache:
            return
        _cache["_last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            os.makedirs(os.path.dirname(LEARNED_ANSWERS_FILE), exist_ok=True)
            with open(LEARNED_ANSWERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(_cache, f, indent=4, ensure_ascii=False)
            _dirty = False
        except OSError as e:
            print(f"[SelfLearning] ⚠️ Could not save {LEARNED_ANSWERS_FILE}: {e}")


def get_answer(label: str, question_type: str = "text") -> str | None:
    """Look up a previously learned answer.

    Performs canonical-normalised lookup so that minor wording differences
    (case, punctuation, stopwords) still find a match.

    Args:
        label: The question label (case-insensitive lookup)
        question_type: One of 'text', 'select', 'radio', 'textarea', 'checkbox', 'dropdown_mappings'

    Returns:
        The saved answer string, or None if not found.
    """
    data = load()
    bucket_key = _TYPE_MAP.get(question_type, "text_answers")
    bucket = data.get(bucket_key, {})

    # 1. Try exact match (fast path)
    if label in bucket:
        return bucket[label]

    # 2. Try canonical match (handles case, punctuation, stopword diffs)
    canonical = _normalize_label(label)
    if canonical:
        existing = _find_existing_key(bucket, canonical)
        if existing is not None:
            return bucket[existing]

    return None


def learn(label: str, answer: str, question_type: str = "text", overwrite: bool = True):
    """Store a new answer for future use.

    De-duplicates: if an existing key normalises to the same canonical form,
    it is updated (or skipped if overwrite=False) rather than creating a new entry.

    Args:
        label: The question label
        answer: The answer to store
        question_type: One of 'text', 'select', 'radio', 'textarea', 'checkbox', 'dropdown_mappings'
        overwrite: If True, overwrite existing answers
    """
    global _dirty
    if not label or not answer:
        return

    data = load()
    bucket_key = _TYPE_MAP.get(question_type, "text_answers")

    with _lock:
        if bucket_key not in data:
            data[bucket_key] = {}
        bucket = data[bucket_key]

        canonical = _normalize_label(label)
        existing_key = _find_existing_key(bucket, canonical) if canonical else None

        if existing_key is not None:
            # Key already exists (possibly different case/wording)
            if overwrite:
                # Remove old key variant, store under canonical label
                if existing_key != label:
                    bucket.pop(existing_key, None)
                bucket[label] = answer
                _dirty = True
            # else: skip — answer already present
        else:
            # Brand new entry
            bucket[label] = answer
            _dirty = True


def learn_dropdown(label: str, selected_option: str):
    """Shortcut: learn a dropdown/select answer specifically."""
    learn(label, selected_option, question_type="dropdown_mappings")


def get_dropdown(label: str) -> str | None:
    """Shortcut: look up a learned dropdown answer."""
    return get_answer(label, question_type="dropdown_mappings")


def get_education() -> dict:
    """Get education details from learned answers, falling back to config."""
    data = load()
    edu = data.get("education", {})

    # If education not yet stored, pull from config
    if not edu:
        try:
            from config.personals import (
                university, degree, field_of_study, gpa, gpa_scale,
                education_start_date, education_end_date
            )
            edu = {
                "university": university,
                "degree": degree,
                "field_of_study": field_of_study,
                "gpa": gpa,
                "gpa_scale": gpa_scale,
                "start_date": education_start_date,
                "end_date": education_end_date,
            }
            # Store it for future use
            with _lock:
                data["education"] = edu
                global _dirty
                _dirty = True
        except ImportError:
            pass

    return edu


def flush():
    """Force-save if there are unsaved changes. Call at end of session."""
    with _lock:
        needs_save = _dirty
    if needs_save:
        save()


def get_all_learned() -> dict:
    """Return the full learned answers dict (for V2 filler integration)."""
    return load()


def stats() -> dict:
    """Return stats about what we've learned."""
    data = load()
    return {
        "text": len(data.get("text_answers", {})),
        "select": len(data.get("select_answers", {})),
        "radio": len(data.get("radio_answers", {})),
        "textarea": len(data.get("textarea_answers", {})),
        "checkbox": len(data.get("checkbox_answers", {})),
        "dropdowns": len(data.get("dropdown_mappings", {})),
        "has_education": bool(data.get("education", {})),
    }


def compact():
    """One-time migration: de-duplicate existing entries in all buckets.

    Call once after upgrading to the normalised storage scheme.
    Removes entries whose canonical form duplicates another entry,
    keeping the most recently written (last) variant.
    """
    data = load()
    total_removed = 0

    with _lock:
        for bucket_key in ("text_answers", "select_answers", "radio_answers",
                           "textarea_answers", "checkbox_answers", "dropdown_mappings"):
            bucket = data.get(bucket_key, {})
            if not bucket:
                continue
            seen: dict[str, str] = {}  # canonical -> raw key
            keys_to_remove: list[str] = []
            for raw_key in list(bucket.keys()):
                canonical = _normalize_label(raw_key)
                if canonical in seen:
                    # Duplicate — remove the older entry
                    keys_to_remove.append(seen[canonical])
                    seen[canonical] = raw_key
                else:
                    seen[canonical] = raw_key
            for old_key in keys_to_remove:
                bucket.pop(old_key, None)
                total_removed += 1

    if total_removed > 0:
        global _dirty
        _dirty = True
        save()
        print(f"[SelfLearning] 🧹 Compacted: removed {total_removed} duplicate entries")
    return total_removed
