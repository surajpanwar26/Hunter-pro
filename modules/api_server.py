"""
Local API Server for Chrome Extension ↔ Python Backend Bridge.

Provides REST endpoints so the extension can:
- Read the master resume
- Tailor resumes using the project's AI pipeline
- Get ATS scores and keyword analysis
- Run AI reviewer agent for iterative improvement

Run:  python -m modules.api_server
"""
from __future__ import annotations

import os
import sys
import threading
import re
import json
import html
import tempfile
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Optional, Any

# Ensure project root is on path before config imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.settings import (  # noqa: E402
    master_resume_folder,
    generated_resume_path,
    resume_tailoring_default_instructions,
)
from config.secrets import ai_provider  # noqa: E402
from flask import Flask, request, jsonify, send_file  # noqa: E402
from flask_cors import CORS  # noqa: E402

app = Flask(__name__)
# CORS: Allow localhost for development and Chrome extension origins.
# For production, replace the extension wildcard with your specific extension ID:
# e.g., "chrome-extension://your-extension-id-here"
CORS(app, origins=["http://127.0.0.1:5001", "http://localhost:5001", "chrome-extension://*"])

EXTENSION_LEARNING_FILE = os.path.join(PROJECT_ROOT, "config", "extension_learning_sync.json")
LEARNED_ANSWERS_FILE = os.path.join(PROJECT_ROOT, "config", "learned_answers.json")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_master_resume() -> Optional[str]:
    """Find the master resume file in the configured folder."""
    folder = master_resume_folder or "all resumes/master resume/"
    if not os.path.isabs(folder):
        folder = os.path.join(PROJECT_ROOT, folder)

    if not os.path.isdir(folder):
        return None

    # Priority order: .pdf > .docx > .txt
    for ext in (".pdf", ".docx", ".txt"):
        for f in os.listdir(folder):
            if f.lower().endswith(ext) and not f.startswith("."):
                return os.path.join(folder, f)
    return None


def _read_resume_text(path: str) -> str:
    """Read resume text from any supported format."""
    from modules.ai.resume_tailoring import _read_resume_text as _reader
    return _reader(path)


def _safe_resume_path(raw_path: str) -> Optional[str]:
    """Validate that a requested file path is an allowed local resume artifact."""
    if not raw_path:
        return None

    abs_path = os.path.abspath(raw_path)
    if not os.path.exists(abs_path) or not os.path.isfile(abs_path):
        return None

    ext = os.path.splitext(abs_path)[1].lower()
    if ext not in {".txt", ".docx", ".pdf"}:
        return None

    allowed_roots = []

    master_folder = master_resume_folder or "all resumes/master resume/"
    if not os.path.isabs(master_folder):
        master_folder = os.path.join(PROJECT_ROOT, master_folder)
    allowed_roots.append(os.path.abspath(master_folder))

    generated_root = generated_resume_path or "all resumes/"
    if not os.path.isabs(generated_root):
        generated_root = os.path.join(PROJECT_ROOT, generated_root)
    allowed_roots.append(os.path.abspath(generated_root))

    project_root_abs = os.path.abspath(PROJECT_ROOT)
    try:
        normalized = os.path.normcase(abs_path)
        for root in allowed_roots:
            root_norm = os.path.normcase(os.path.abspath(root))
            if normalized.startswith(root_norm + os.sep) or normalized == root_norm:
                return abs_path
        # Explicitly allow files under project "all resumes" even if config paths differ
        all_resumes_root = os.path.normcase(os.path.join(project_root_abs, "all resumes"))
        if normalized.startswith(all_resumes_root + os.sep) or normalized == all_resumes_root:
            return abs_path
    except Exception:
        return None

    return None


def _resolve_existing_file_path(raw_path: str) -> str:
    """Resolve a generated file path to an existing absolute path, else empty string."""
    if not raw_path:
        return ""
    candidate = str(raw_path).strip()
    if not os.path.isabs(candidate):
        candidate = os.path.join(PROJECT_ROOT, candidate)
    candidate = os.path.abspath(candidate)
    return candidate if os.path.isfile(candidate) else ""


def _extract_skills_from_jd(jd_text: str) -> dict:
    """Extract categorized skills from job description text."""
    text_lower = _sanitize_jd_text(jd_text).lower()

    tech_keywords = {
        "python", "java", "javascript", "typescript", "react", "angular", "vue",
        "node.js", "nodejs", "sql", "nosql", "mongodb", "postgresql", "mysql",
        "redis", "elasticsearch", "aws", "azure", "gcp", "docker", "kubernetes",
        "jenkins", "ci/cd", "terraform", "api", "rest", "graphql", "microservices",
        "agile", "scrum", "git", "linux", "machine learning", "ml", "ai",
        "data science", "html", "css", "spring", "django", "flask", "c++", "c#",
        "golang", "rust", "scala", "kotlin", "swift", "ruby", "php", ".net",
        "kafka", "rabbitmq", "spark", "hadoop", "tableau", "power bi",
        "spring boot", "express", "fastapi", "next.js", "webpack", "sass",
    }

    soft_keywords = {
        "leadership", "communication", "teamwork", "collaboration",
        "problem solving", "analytical", "critical thinking",
        "time management", "project management", "stakeholder",
        "mentoring", "cross functional", "presentation", "negotiation",
    }

    found_tech = sorted([kw for kw in tech_keywords if kw in text_lower])
    found_soft = sorted([kw for kw in soft_keywords if kw in text_lower])

    return {"technical": found_tech, "soft": found_soft, "all": found_tech + found_soft}


def _sanitize_jd_text(value: str) -> str:
    text = str(value or "").replace("\r", "\n")
    for _ in range(2):
        had_markup = bool(re.search(r"<[^>]+>|&lt;/?[a-z][^&]*&gt;", text, flags=re.IGNORECASE))
        text = html.unescape(text)
        text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", text)
        text = re.sub(r"(?is)<br\s*/?>", "\n", text)
        text = re.sub(r"(?is)</p\s*>", "\n", text)
        text = re.sub(r"(?is)<[^>]+>", " ", text)
        if not had_markup:
            break

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _merge_timestamped_maps(base_map: dict, incoming_map: dict) -> dict:
    merged = dict(base_map or {})
    for key, value in (incoming_map or {}).items():
        current = merged.get(key)
        current_ts = float((current or {}).get("updatedAt", 0) or 0)
        next_ts = float((value or {}).get("updatedAt", 0) or 0)
        if not current or next_ts >= current_ts:
            merged[key] = value
    return merged


def _load_extension_learning() -> dict:
    default_payload = {
        "learnedFields": {},
        "customAnswers": {},
        "updatedAt": "",
    }
    try:
        if not os.path.exists(EXTENSION_LEARNING_FILE):
            return default_payload
        with open(EXTENSION_LEARNING_FILE, "r", encoding="utf-8") as file_obj:
            parsed = json.load(file_obj)
        return {
            "learnedFields": parsed.get("learnedFields", {}) or {},
            "customAnswers": parsed.get("customAnswers", {}) or {},
            "updatedAt": parsed.get("updatedAt", "") or "",
        }
    except Exception:
        return default_payload


def _save_extension_learning(learned_fields: dict, custom_answers: dict) -> None:
    payload = {
        "learnedFields": learned_fields or {},
        "customAnswers": custom_answers or {},
        "updatedAt": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    os.makedirs(os.path.dirname(EXTENSION_LEARNING_FILE), exist_ok=True)
    with open(EXTENSION_LEARNING_FILE, "w", encoding="utf-8") as file_obj:
        json.dump(payload, file_obj, indent=2, ensure_ascii=False)


def _default_learned_answers_payload() -> dict:
    return {
        "_description": "Auto-saved answers from user interventions and bot learning. Edit manually if needed.",
        "_last_updated": "",
        "text_answers": {},
        "select_answers": {},
        "radio_answers": {},
        "textarea_answers": {},
        "checkbox_answers": {},
        "education": {},
        "dropdown_mappings": {},
    }


def _bucket_for_input_type(input_type: str) -> str:
    value = str(input_type or "").strip().lower()
    if value in {"select", "customdropdown", "dropdown"}:
        return "select_answers"
    if value in {"radio", "radiocustom"}:
        return "radio_answers"
    if value in {"textarea"}:
        return "textarea_answers"
    if value in {"checkbox", "toggle", "switch"}:
        return "checkbox_answers"
    return "text_answers"


def _load_learned_answers_file() -> dict:
    defaults = _default_learned_answers_payload()
    try:
        if not os.path.exists(LEARNED_ANSWERS_FILE):
            return defaults
        with open(LEARNED_ANSWERS_FILE, "r", encoding="utf-8") as file_obj:
            parsed = json.load(file_obj)
        if not isinstance(parsed, dict):
            return defaults
        for key, value in defaults.items():
            if key not in parsed:
                parsed[key] = value
        return parsed
    except Exception:
        return defaults


def _save_learned_answers_file(payload: dict) -> None:
    os.makedirs(os.path.dirname(LEARNED_ANSWERS_FILE), exist_ok=True)
    with open(LEARNED_ANSWERS_FILE, "w", encoding="utf-8") as file_obj:
        json.dump(payload, file_obj, indent=4, ensure_ascii=False)


def _sync_extension_answers_to_learned_answers(custom_answers: dict) -> None:
    if not isinstance(custom_answers, dict) or not custom_answers:
        return

    learned_payload = _load_learned_answers_file()
    changed = False

    def _canonical_label(value: str) -> str:
        text = str(value or "").strip().lower()
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return ""

        stopwords = {
            "a", "an", "the", "to", "in", "on", "for", "of", "and", "or", "is", "are", "you", "your", "do", "does",
            "can", "will", "would", "should", "be", "legally",
        }

        def _stem(token: str) -> str:
            out = token
            for suffix in ("ization", "isation", "ation", "ized", "ised", "ing", "ed", "es", "s"):
                if out.endswith(suffix) and len(out) > len(suffix) + 2:
                    out = out[: -len(suffix)]
                    break
            return out

        parts = [_stem(tok) for tok in text.split(" ") if tok and tok not in stopwords]
        return " ".join(parts).strip()

    def _upsert_bucket_entry(bucket: dict, label: str, normalized_label: str, text_value: str) -> bool:
        if not isinstance(bucket, dict):
            return False

        canonical = _canonical_label(normalized_label or label)
        if not canonical:
            return False

        def _token_set(value: str) -> set[str]:
            return {token for token in _canonical_label(value).split(" ") if token}

        def _similar_enough(left: str, right: str) -> bool:
            left_set = _token_set(left)
            right_set = _token_set(right)
            if not left_set or not right_set:
                return False
            intersection = len(left_set.intersection(right_set))
            union = len(left_set.union(right_set)) or 1
            jaccard = intersection / union
            # consider "work authorization" and "are you legally authorized to work..." duplicates
            return jaccard >= 0.65 or left_set.issubset(right_set) or right_set.issubset(left_set)

        keys_to_remove = []
        for existing_key in list(bucket.keys()):
            existing_canonical = _canonical_label(existing_key)
            same_key = existing_canonical == canonical
            close_match = _similar_enough(existing_canonical, canonical)
            if (same_key or close_match) and existing_key != canonical:
                keys_to_remove.append(existing_key)

        local_changed = False
        for old_key in keys_to_remove:
            if bucket.get(old_key) != text_value:
                local_changed = True
            bucket.pop(old_key, None)

        if bucket.get(canonical) != text_value:
            bucket[canonical] = text_value
            local_changed = True

        return local_changed

    for key, raw in custom_answers.items():
        if str(key).startswith("@norm:"):
            continue

        if isinstance(raw, dict):
            label = str(raw.get("label") or key or "").strip()
            value = raw.get("value")
            input_type = str(raw.get("inputType") or "text")
            normalized_label = str(raw.get("normalizedLabel") or "").strip().lower()
        else:
            label = str(key or "").strip()
            value = raw
            input_type = "text"
            normalized_label = ""

        text_value = str(value or "").strip()
        if not label or not text_value:
            continue

        bucket_key = _bucket_for_input_type(input_type)
        bucket = learned_payload.get(bucket_key)
        if not isinstance(bucket, dict):
            bucket = {}
            learned_payload[bucket_key] = bucket

        if _upsert_bucket_entry(bucket, label, normalized_label, text_value):
            changed = True

        if bucket_key in {"select_answers", "radio_answers"}:
            dropdown_map = learned_payload.get("dropdown_mappings")
            if not isinstance(dropdown_map, dict):
                dropdown_map = {}
                learned_payload["dropdown_mappings"] = dropdown_map

            if _upsert_bucket_entry(dropdown_map, label, normalized_label, text_value):
                changed = True

    if changed:
        learned_payload["_last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _save_learned_answers_file(learned_payload)


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.route("/api/health", methods=["GET"])
def health():
    """Health check."""
    return jsonify({"status": "ok", "provider": ai_provider or "ollama", "version": "1.0.0"})


@app.route("/api/master-resume", methods=["GET"])
def get_master_resume():
    """Return the master resume text content."""
    path = _find_master_resume()
    if not path:
        return jsonify({"error": "No master resume found", "searchPath": master_resume_folder}), 404

    try:
        text = _read_resume_text(path)
        return jsonify({
            "success": True,
            "text": text,
            "filename": os.path.basename(path),
            "path": path,
            "format": os.path.splitext(path)[1].lstrip("."),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/resume-file", methods=["GET"])
def get_resume_file():
    """Return a resume artifact file (txt/docx/pdf) for extension download/upload."""
    req_path = request.args.get("path", "")
    safe_path = _safe_resume_path(req_path)
    if not safe_path:
        return jsonify({"error": "Invalid or unauthorized file path"}), 400

    try:
        ext = os.path.splitext(safe_path)[1].lower()
        mimetype = "application/octet-stream"
        if ext == ".pdf":
            mimetype = "application/pdf"
        elif ext == ".docx":
            mimetype = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif ext == ".txt":
            mimetype = "text/plain"

        return send_file(
            safe_path,
            as_attachment=True,
            download_name=os.path.basename(safe_path),
            mimetype=mimetype,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/extract-resume-text", methods=["POST"])
def extract_resume_text():
    """Extract plain text from uploaded resume bytes (txt/docx/pdf)."""
    data = request.get_json(silent=True) or {}
    file_name = str(data.get("fileName", "resume.docx") or "resume.docx")
    ext = os.path.splitext(file_name)[1].lower()
    if ext not in {".txt", ".docx", ".pdf"}:
        return jsonify({"error": "Unsupported resume type. Use TXT, DOCX, or PDF."}), 400

    raw_bytes = data.get("fileBytes", [])
    file_base64 = data.get("fileBase64", "")

    # Accept base64-encoded data (preferred) or legacy list-of-ints
    if isinstance(file_base64, str) and file_base64:
        import base64 as _b64
        try:
            blob = _b64.b64decode(file_base64)
        except Exception:
            return jsonify({"error": "Invalid fileBase64 format"}), 400
    elif isinstance(raw_bytes, list) and raw_bytes:
        try:
            blob = bytes(int(b) & 0xFF for b in raw_bytes)
        except Exception:
            return jsonify({"error": "Invalid fileBytes format"}), 400
    else:
        return jsonify({"error": "fileBase64 or fileBytes payload is missing"}), 400

    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
            temp_file.write(blob)
            temp_path = temp_file.name

        text = _read_resume_text(temp_path)
        return jsonify({
            "success": True,
            "text": text,
            "chars": len(text or ""),
            "filename": file_name,
        })
    except Exception as e:
        return jsonify({"error": f"Failed to extract resume text: {e}"}), 500
    finally:
        if temp_path:
            try:
                os.remove(temp_path)
            except Exception:
                pass


@app.route("/api/extract-skills", methods=["POST"])
def extract_skills():
    """Extract skills from a job description."""
    data = request.get_json(silent=True) or {}
    jd_text = _sanitize_jd_text(data.get("jobDescription", ""))

    if not jd_text or len(jd_text) < 50:
        return jsonify({"error": "Job description too short"}), 400

    skills = _extract_skills_from_jd(jd_text)
    return jsonify({"success": True, "skills": skills})


@app.route("/api/score", methods=["POST"])
def score_resume():
    """Calculate ATS match score between resume and JD."""
    data = request.get_json(silent=True) or {}
    resume_text = data.get("resumeText", "")
    jd_text = _sanitize_jd_text(data.get("jobDescription", ""))

    if not resume_text or not jd_text:
        return jsonify({"error": "Both resumeText and jobDescription required"}), 400

    from modules.ai.resume_tailoring import _score_match
    scores = _score_match(resume_text, jd_text)

    return jsonify({"success": True, "scores": scores})


def _resolve_resume_text(data: dict) -> tuple[str, Optional[tuple]]:
    """Resolve resume text from request data or master resume.

    Returns (resume_text, error_response) where error_response is None on success.
    """
    resume_text = data.get("resumeText", "")
    if resume_text:
        return resume_text, None

    path = _find_master_resume()
    if not path:
        return "", (jsonify({"error": "No master resume found and no resumeText provided"}), 404)
    try:
        return _read_resume_text(path), None
    except Exception as e:
        return "", (jsonify({"error": f"Failed to read master resume: {e}"}), 500)


def _build_review_instructions(
    base_instructions: str,
    iteration: int,
    current_text: str,
    jd_text: str,
) -> str:
    """Build instructions for a tailoring iteration, adding review feedback if needed."""
    result = base_instructions or resume_tailoring_default_instructions
    if iteration <= 1:
        return result

    from modules.ai.resume_tailoring import _score_match

    prev_scores = _score_match(current_text, jd_text)
    missing = prev_scores.get("tech_missing", [])[:5]
    if missing:
        result += (
            f"\n\nREVIEW FEEDBACK (Iteration {iteration}): "
            f"Missing JD keywords: {', '.join(missing)}. "
            f"Weave them naturally. Ensure no empty sections."
        )
    return result


def _resume_content_method_instructions() -> str:
    return """=== RESUME CONTENT IMPROVEMENT METHOD (MANDATORY) ===

1) IMPACT BULLETS PER ROLE
- Add 3 to 5 quantified impact bullets for each recent role (%, $, latency, scale where factual).

2) JD LANGUAGE MIRRORING
- Mirror exact JD nouns/phrases in Core Skills and Experience bullets naturally.
- Avoid keyword stuffing.

3) BULLET SHAPE
- Start each bullet with action + result, then tooling/context.

4) ONE-PAGE HIERARCHY
- Keep one-page structure tight: Summary, Core Skills, Experience, Projects, Education.
"""


def _run_iterative_tailoring(
    resume_text: str,
    jd_text: str,
    instructions: str,
    provider: str,
    review_iterations: int,
) -> tuple[str, list]:
    """Run iterative AI tailoring with review feedback."""
    from modules.ai.resume_tailoring import tailor_resume_text, _score_match

    current_text = resume_text
    review_log: list[dict] = []

    for iteration in range(1, review_iterations + 1):
        iter_instructions = _build_review_instructions(
            instructions, iteration, current_text, jd_text,
        )
        tailored = tailor_resume_text(
            resume_text=current_text,
            job_description=jd_text,
            instructions=iter_instructions,
            provider=provider or None,
            inject_keywords=True,
            validate_quality=(iteration == review_iterations),
            max_retries=0,
        )

        if not tailored or tailored.startswith("["):
            review_log.append({
                "iteration": iteration,
                "error": tailored[:200] if tailored else "Empty response",
            })
            break

        iter_scores = _score_match(tailored, jd_text)
        review_log.append({
            "iteration": iteration,
            "atsScore": iter_scores.get("ats", 0),
            "matchScore": iter_scores.get("match", 0),
            "matched": iter_scores.get("matched", 0),
            "total": iter_scores.get("total", 0),
        })
        current_text = tailored

    return current_text, review_log


def _assess_resume_quality(master_text: str, tailored_text: str, jd_text: str) -> dict:
    if not tailored_text or not tailored_text.strip():
        return {"passed": False, "reason": "AI returned empty resume text"}

    placeholder_patterns = [
        r"lorem ipsum",
        r"\[insert",
        r"\b(tbd|todo|placeholder|sample resume)\b",
        r"\b(n/?a|null|none)\b",
    ]
    lowered = tailored_text.lower()
    if any(re.search(p, lowered) for p in placeholder_patterns):
        return {"passed": False, "reason": "AI output contains placeholder/random text"}

    if len(tailored_text.split()) < 140:
        return {"passed": False, "reason": "Tailored resume is too short"}

    similarity = SequenceMatcher(None, master_text or "", tailored_text).ratio()
    if similarity > 0.995:
        return {"passed": False, "reason": "Tailored resume is unchanged from source"}

    try:
        from modules.ai.resume_validator import validate_tailored_resume

        quality_report = validate_tailored_resume(
            original_resume=master_text,
            tailored_resume=tailored_text,
            job_description=jd_text,
        )
        grade = str(quality_report.overall_grade or "").upper()
        no_blockers = not bool(quality_report.critical_issues)
        ats_ok = float(quality_report.weighted_ats_score) >= 60.0
        advisory_only = bool(grade in {"A", "B", "C", "D"} or ats_ok or no_blockers)
        return {
            "passed": advisory_only,
            "reason": "Quality checks completed" if advisory_only else "Quality checks completed with advisory warnings",
            "grade": quality_report.overall_grade,
            "weightedAts": round(float(quality_report.weighted_ats_score), 2),
            "criticalIssues": quality_report.critical_issues[:3],
            "warnings": quality_report.warnings[:3],
        }
    except Exception:
        return {"passed": True, "reason": "Quality checks partially applied"}


def _reviewer_passed(overall_score: float, critical_issues: int) -> bool:
    score = float(overall_score or 0)
    critical = int(critical_issues or 0)
    if score >= 85.0 and critical == 0:
        return True
    # Some reviewer runs keep a single advisory "critical" flag despite very high overall quality.
    # Treat that as pass to prevent infinite correction loops.
    if score >= 92.0 and critical <= 1:
        return True
    return False


def _build_reviewer_feedback(report: Any) -> str:
    findings = list(getattr(report, "findings", []) or [])
    top = []
    for f in findings[:8]:
        severity = getattr(getattr(f, "severity", None), "value", "issue")
        issue = str(getattr(f, "issue", "")).strip()
        if issue:
            top.append(f"[{severity}] {issue}")

    summary = [
        f"Overall score: {round(float(getattr(report, 'overall_score', 0.0)), 2)}",
        f"Critical issues: {int(getattr(report, 'critical_issues', 0) or 0)}",
        f"Total issues: {int(getattr(report, 'total_issues', 0) or 0)}",
    ]
    if top:
        summary.append("Top findings:")
        summary.extend(top)
    return "\n".join(summary).strip()


def _run_reviewer_ai_loop(
    resume_text: str,
    jd_text: str,
    job_title: str,
    instructions: str,
    provider: str,
    max_passes: int,
) -> tuple[str, list, bool, dict]:
    from modules.ai.resume_tailoring import tailor_resume_text
    from modules.ai.reviewer_agent import review_tailored_resume

    current_text = resume_text
    review_pass_log: list[dict] = []
    reviewer_payload: dict = {}
    passed = False

    for reviewer_pass in range(1, max_passes + 1):
        improved_text, report = review_tailored_resume(
            tailored_resume=current_text,
            original_resume=resume_text,
            job_description=jd_text,
            job_title=job_title,
            auto_correct=True,
        )

        current_text = improved_text or current_text
        overall_score = float(getattr(report, "overall_score", 0.0) or 0.0)
        critical_issues = int(getattr(report, "critical_issues", 0) or 0)
        auto_fixed_count = int(getattr(report, "auto_fixed_count", 0) or 0)
        passed = _reviewer_passed(overall_score, critical_issues)

        review_pass_log.append({
            "pass": reviewer_pass,
            "overallScore": round(overall_score, 2),
            "criticalIssues": critical_issues,
            "autoFixed": auto_fixed_count,
            "reviewerPassed": passed,
        })

        reviewer_payload = {
            "overallScore": round(overall_score, 2),
            "criticalIssues": critical_issues,
            "issues": int(getattr(report, "total_issues", 0) or 0),
            "fixed": auto_fixed_count,
            "summary": list(getattr(report, "improvements_made", []) or [])[:6],
        }

        if passed:
            break

        feedback = _build_reviewer_feedback(report)
        next_instructions = (
            (instructions or resume_tailoring_default_instructions)
            + "\n\nREVIEWER MANDATORY FIX PASS:\n"
            + feedback
            + "\n\nApply all fixes exactly, preserve factual details, keep one-page resume, and return clean resume text only."
        )
        regenerated = tailor_resume_text(
            resume_text=current_text,
            job_description=jd_text,
            instructions=next_instructions,
            provider=provider or None,
            inject_keywords=True,
            validate_quality=False,
            max_retries=0,
        )

        if regenerated and not str(regenerated).startswith("["):
            current_text = regenerated

    return current_text, review_pass_log, passed, reviewer_payload


def _get_reviewer_instruction_defaults() -> str:
    return """=== REVIEWER AGENT INSTRUCTIONS ===

1) PRIMARY GOAL
- Review the tailored resume for ATS quality, grammar, keyword alignment, and structure.
- Fix critical/high issues first.

2) FORMAT & INTEGRITY RULES
- Keep the resume one page.
- Preserve original section order and overall formatting.
- Do not alter factual details (dates, titles, companies) unless correcting an obvious typo.

3) CONTENT RULES
- Improve weak phrasing using strong action verbs.
- Increase clarity and JD-keyword alignment naturally (no stuffing).
- Never invent projects, skills, tools, metrics, or responsibilities.

4) PASS CRITERIA FOR UNLOCK
- No critical issues.
- Reviewer overall score should meet submission quality.

5) OUTPUT RULE
- Return clean, submission-ready resume content.

6) METHOD ENFORCEMENT
- Enforce: 3-5 quantified impact bullets for each recent role where factual.
- Enforce: JD nouns/phrases mirrored naturally in skills + experience.
- Enforce: each bullet follows action + result + tooling/context shape.
- Enforce one-page hierarchy: Summary, Core Skills, Experience, Projects, Education."""


@app.route("/api/default-instructions", methods=["GET"])
def get_default_instructions():
    return jsonify({
        "success": True,
        "instructions": resume_tailoring_default_instructions,
        "tailoringInstructions": resume_tailoring_default_instructions,
        "reviewerInstructions": _get_reviewer_instruction_defaults(),
    })


@app.route("/api/extension-learning", methods=["GET", "POST"])
def extension_learning_sync():
    """Sync learned fields/custom answers between extension and local backend."""
    if request.method == "GET":
        payload = _load_extension_learning()
        return jsonify({"success": True, **payload})

    try:
        data = request.get_json(silent=True) or {}
        incoming_fields = data.get("learnedFields", {}) or {}
        incoming_answers = data.get("customAnswers", {}) or {}

        if not isinstance(incoming_fields, dict):
            incoming_fields = {}
        if not isinstance(incoming_answers, dict):
            incoming_answers = {}

        current = _load_extension_learning()
        merged_fields = _merge_timestamped_maps(current.get("learnedFields", {}), incoming_fields)
        merged_answers = _merge_timestamped_maps(current.get("customAnswers", {}), incoming_answers)

        sync_warning = ""
        _save_extension_learning(merged_fields, merged_answers)
        try:
            _sync_extension_answers_to_learned_answers(merged_answers)
        except Exception as sync_err:
            sync_warning = f"learned_answers_sync_failed: {sync_err}"

        saved = _load_extension_learning()
        response = {"success": True, **saved}
        if sync_warning:
            response["warning"] = sync_warning
        return jsonify(response)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"extension-learning sync failed: {e}",
            "learnedFields": {},
            "customAnswers": {},
            "updatedAt": "",
        }), 200


@app.route("/api/tailor", methods=["POST"])
def tailor_resume():
    """Tailor a resume to a JD using the project's AI pipeline."""
    data = request.get_json(silent=True) or {}
    jd_text = _sanitize_jd_text(data.get("jobDescription", ""))
    job_title = data.get("jobTitle", "Tailored Resume")
    instructions = data.get("instructions", "")
    provider = data.get("provider", "")
    review_iterations = min(int(data.get("reviewIterations", 2)), 3)
    reviewer_max_passes = max(1, min(int(data.get("reviewerMaxPasses", 5)), 10))

    if not jd_text or len(jd_text) < 50:
        return jsonify({"error": "Job description too short (min 50 chars)"}), 400

    method_instructions = _resume_content_method_instructions()
    effective_instructions = (
        (str(instructions or "").strip() or str(resume_tailoring_default_instructions or "").strip())
        + "\n\n"
        + method_instructions
    ).strip()

    resume_text, err = _resolve_resume_text(data)
    if err:
        return err

    try:
        from modules.ai.resume_tailoring import _score_match, tailor_resume_to_files, _write_docx, _write_pdf, _save_text

        scores_before = _score_match(resume_text, jd_text)

        current_text, review_log = _run_iterative_tailoring(
            resume_text, jd_text, effective_instructions, provider, review_iterations,
        )

        quality = _assess_resume_quality(resume_text, current_text, jd_text)
        if not quality.get("passed"):
            return jsonify({
                "error": quality.get("reason", "Tailored resume failed quality checks"),
                "quality": quality,
            }), 422

        reviewed_text, review_pass_log, reviewer_passed, reviewer = _run_reviewer_ai_loop(
            resume_text=current_text,
            jd_text=jd_text,
            job_title=job_title,
            instructions=effective_instructions,
            provider=provider,
            max_passes=reviewer_max_passes,
        )

        if not reviewer_passed:
            return jsonify({
                "error": "Reviewer did not pass resume after max auto-fix loops",
                "reviewPassLog": review_pass_log,
                "reviewer": reviewer,
            }), 422

        current_text = reviewed_text
        scores_after = _score_match(current_text, jd_text)

        output_dir = os.path.join(
            PROJECT_ROOT, generated_resume_path or "all resumes/", "tailored",
        )
        os.makedirs(output_dir, exist_ok=True)

        result_files = tailor_resume_to_files(
            resume_text=resume_text,
            job_description=jd_text,
            instructions=effective_instructions,
            provider=provider or None,
            output_dir=output_dir,
            job_title=job_title,
            enable_preview=False,
        )

        txt_path = _resolve_existing_file_path(result_files.get("txt", ""))
        docx_path = _resolve_existing_file_path(result_files.get("docx", ""))
        pdf_path = _resolve_existing_file_path(result_files.get("pdf", ""))

        base_slug = re.sub(r"[^a-zA-Z0-9_\- ]+", "", str(job_title or "Tailored Resume")).strip().replace(" ", "_")
        base_name = f"tailored_{base_slug}" if base_slug else "tailored_resume"

        if not txt_path:
            try:
                txt_path = _resolve_existing_file_path(_save_text(current_text, output_dir, base_name=base_name))
            except Exception:
                txt_path = ""

        if not docx_path:
            try:
                docx_path = _resolve_existing_file_path(_write_docx(current_text, output_dir, base_name=base_name))
            except Exception:
                docx_path = ""

        if not pdf_path:
            try:
                pdf_path = _resolve_existing_file_path(_write_pdf(current_text, output_dir, base_name=base_name))
            except Exception:
                pdf_path = ""

        return jsonify({
            "success": True,
            "tailoredText": current_text,
            "masterText": resume_text,
            "scoresBefore": scores_before,
            "scoresAfter": scores_after,
            "reviewLog": review_log,
            "reviewIterations": len(review_log),
            "reviewPassLog": review_pass_log,
            "reviewerPassed": reviewer_passed,
            "reviewer": reviewer,
            "quality": quality,
            "files": {
                "txt": txt_path,
                "docx": docx_path,
                "pdf": pdf_path,
            },
            "skills": _extract_skills_from_jd(jd_text),
        })

    except Exception as e:
        import traceback
        traceback.print_exc()  # Log to server console only
        return jsonify({
            "error": "An internal error occurred during resume tailoring",
        }), 500


@app.route("/api/review", methods=["POST"])
def review_resume():
    """
    Run an additional AI review pass on an already-tailored resume.

    Accepts:
        tailoredText (str): Current tailored resume
        masterText (str): Original master resume
        jobDescription (str): Job description
        feedback (str): Optional user feedback for this review round

    Returns:
        Improved resume text and updated scores.
    """
    data = request.get_json(silent=True) or {}
    tailored_text = data.get("tailoredText", "")
    master_text = data.get("masterText", "")
    jd_text = _sanitize_jd_text(data.get("jobDescription", ""))
    feedback = data.get("feedback", "")
    max_iterations = max(1, min(int(data.get("maxIterations", 5)), 10))

    if not tailored_text or not jd_text:
        return jsonify({"error": "tailoredText and jobDescription required"}), 400

    try:
        from modules.ai.resume_tailoring import _score_match
        from modules.ai.reviewer_agent import get_reviewer_agent

        scores_before = _score_match(tailored_text, jd_text)
        agent = get_reviewer_agent()

        jd_for_review = jd_text
        if feedback:
            jd_for_review = f"{jd_text}\n\nUSER REVIEW FEEDBACK:\n{feedback}".strip()

        report = agent.review_and_fix_iteratively(
            tailored_resume=tailored_text,
            original_resume=master_text or tailored_text,
            job_description=jd_for_review,
            max_iterations=max_iterations,
        )
        improved_text = report.corrected_resume

        if improved_text and not improved_text.startswith("["):
            scores_after = _score_match(improved_text, jd_text)
            reviewer_passed = _reviewer_passed(float(report.overall_score), int(report.critical_issues))
            return jsonify({
                "success": True,
                "improvedText": improved_text,
                "scoresBefore": scores_before,
                "scoresAfter": scores_after,
                "reviewerPassed": reviewer_passed,
                "reviewer": {
                    "overallScore": round(float(report.overall_score), 2),
                    "criticalIssues": int(report.critical_issues),
                    "issues": int(report.total_issues),
                    "fixed": int(report.auto_fixed_count),
                    "summary": list(report.improvements_made[:6]),
                }
            })

        return jsonify({
            "success": False,
            "error": "Empty AI response from reviewer loop",
            "scoresBefore": scores_before,
        })

    except Exception as e:
        import traceback
        traceback.print_exc()  # Log to server console only
        return jsonify({"error": "An internal error occurred during resume review"}), 500


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
def start_api_server(port: int = 5001, debug: bool = False):
    """Start the API server (non-blocking for dashboard integration)."""
    print(f"🚀 Extension API server starting on http://localhost:{port}")
    print(f"   AI Provider: {ai_provider or 'ollama'}")
    print(f"   Master Resume: {_find_master_resume() or 'NOT FOUND'}")
    app.run(host="127.0.0.1", port=port, debug=debug, use_reloader=False)


def start_api_server_thread(port: int = 5001) -> threading.Thread:
    """Start API server in a background thread (for dashboard integration)."""
    t = threading.Thread(
        target=start_api_server,
        kwargs={"port": port, "debug": False},
        daemon=True,
        name="ExtensionAPIServer",
    )
    t.start()
    print(f"✅ Extension API server running in background on port {port}")
    return t


if __name__ == "__main__":
    start_api_server(port=5001, debug=True)
