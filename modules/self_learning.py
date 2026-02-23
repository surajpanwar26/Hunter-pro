"""
Self-Learning Answer Store for LinkedIn Auto Job Applier.

This module provides a persistent, evolving answer database that:
1. Stores answers the bot discovers or the user corrects
2. Loads them on startup so the bot improves over time
3. Prioritises learned answers over defaults
4. Supports all question types: text, select, radio, textarea, checkbox

File: config/learned_answers.json
"""

import json
import os
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
    
    Args:
        label: The question label (case-insensitive lookup)
        question_type: One of 'text', 'select', 'radio', 'textarea', 'checkbox', 'dropdown_mappings'
    
    Returns:
        The saved answer string, or None if not found.
    """
    data = load()
    label_lower = label.strip().lower()
    
    # Determine which bucket to search
    type_map = {
        "text": "text_answers",
        "select": "select_answers",
        "radio": "radio_answers",
        "textarea": "textarea_answers",
        "checkbox": "checkbox_answers",
        "dropdown": "dropdown_mappings",
        "dropdown_mappings": "dropdown_mappings",
    }
    bucket_key = type_map.get(question_type, "text_answers")
    bucket = data.get(bucket_key, {})
    
    # Try exact match first, then case-insensitive
    if label in bucket:
        return bucket[label]
    for key, value in bucket.items():
        if key.strip().lower() == label_lower:
            return value
    
    return None


def learn(label: str, answer: str, question_type: str = "text", overwrite: bool = True):
    """Store a new answer for future use.
    
    Args:
        label: The question label
        answer: The answer to store
        question_type: One of 'text', 'select', 'radio', 'textarea', 'checkbox', 'dropdown_mappings'
        overwrite: If True, overwrite existing answers
    """
    global _dirty
    data = load()
    
    type_map = {
        "text": "text_answers",
        "select": "select_answers",
        "radio": "radio_answers",
        "textarea": "textarea_answers",
        "checkbox": "checkbox_answers",
        "dropdown": "dropdown_mappings",
        "dropdown_mappings": "dropdown_mappings",
    }
    bucket_key = type_map.get(question_type, "text_answers")
    
    if bucket_key not in data:
        data[bucket_key] = {}
    
    # Only write if overwrite=True or answer doesn't exist yet
    if overwrite or label not in data[bucket_key]:
        with _lock:
            data[bucket_key][label] = answer
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
