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
from typing import Optional

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
from flask import Flask, request, jsonify  # noqa: E402
from flask_cors import CORS  # noqa: E402

app = Flask(__name__)
CORS(app, origins=["chrome-extension://*", "http://localhost:*"])

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

    # Priority order: .txt > .docx > .pdf
    for ext in (".txt", ".docx", ".pdf"):
        for f in os.listdir(folder):
            if f.lower().endswith(ext) and not f.startswith("."):
                return os.path.join(folder, f)
    return None


def _read_resume_text(path: str) -> str:
    """Read resume text from any supported format."""
    from modules.ai.resume_tailoring import _read_resume_text as _reader
    return _reader(path)


def _extract_skills_from_jd(jd_text: str) -> dict:
    """Extract categorized skills from job description text."""
    text_lower = jd_text.lower()

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


@app.route("/api/extract-skills", methods=["POST"])
def extract_skills():
    """Extract skills from a job description."""
    data = request.get_json(silent=True) or {}
    jd_text = data.get("jobDescription", "")

    if not jd_text or len(jd_text) < 50:
        return jsonify({"error": "Job description too short"}), 400

    skills = _extract_skills_from_jd(jd_text)
    return jsonify({"success": True, "skills": skills})


@app.route("/api/score", methods=["POST"])
def score_resume():
    """Calculate ATS match score between resume and JD."""
    data = request.get_json(silent=True) or {}
    resume_text = data.get("resumeText", "")
    jd_text = data.get("jobDescription", "")

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
        source = current_text if iteration == 1 else resume_text
        tailored = tailor_resume_text(
            resume_text=source,
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


@app.route("/api/tailor", methods=["POST"])
def tailor_resume():
    """Tailor a resume to a JD using the project's AI pipeline."""
    data = request.get_json(silent=True) or {}
    jd_text = data.get("jobDescription", "")
    job_title = data.get("jobTitle", "Tailored Resume")
    instructions = data.get("instructions", "")
    provider = data.get("provider", "")
    review_iterations = min(int(data.get("reviewIterations", 2)), 3)

    if not jd_text or len(jd_text) < 50:
        return jsonify({"error": "Job description too short (min 50 chars)"}), 400

    resume_text, err = _resolve_resume_text(data)
    if err:
        return err

    try:
        from modules.ai.resume_tailoring import _score_match, tailor_resume_to_files

        scores_before = _score_match(resume_text, jd_text)

        current_text, review_log = _run_iterative_tailoring(
            resume_text, jd_text, instructions, provider, review_iterations,
        )

        scores_after = _score_match(current_text, jd_text)

        output_dir = os.path.join(
            PROJECT_ROOT, generated_resume_path or "all resumes/", "tailored",
        )
        os.makedirs(output_dir, exist_ok=True)

        result_files = tailor_resume_to_files(
            resume_text=resume_text,
            job_description=jd_text,
            instructions=instructions or resume_tailoring_default_instructions,
            provider=provider or None,
            output_dir=output_dir,
            job_title=job_title,
            enable_preview=False,
        )

        return jsonify({
            "success": True,
            "tailoredText": current_text,
            "masterText": resume_text,
            "scoresBefore": scores_before,
            "scoresAfter": scores_after,
            "reviewLog": review_log,
            "reviewIterations": len(review_log),
            "files": {
                "txt": result_files.get("txt", ""),
                "docx": result_files.get("docx", ""),
                "pdf": result_files.get("pdf", ""),
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
    jd_text = data.get("jobDescription", "")
    feedback = data.get("feedback", "")

    if not tailored_text or not jd_text:
        return jsonify({"error": "tailoredText and jobDescription required"}), 400

    try:
        from modules.ai.resume_tailoring import tailor_resume_text, _score_match

        scores_before = _score_match(tailored_text, jd_text)
        missing = scores_before.get("tech_missing", [])[:5]

        review_instructions = (
            f"REVIEWER AGENT INSTRUCTIONS:\n"
            f"You are reviewing a previously tailored resume. Improve it further.\n"
            f"Missing JD keywords to add: {', '.join(missing) if missing else 'None - looks good!'}\n"
            f"Ensure: no empty sections, all dates preserved, contact info unchanged.\n"
            f"User feedback: {feedback or 'None'}\n"
        )

        improved = tailor_resume_text(
            resume_text=master_text or tailored_text,
            job_description=jd_text,
            instructions=review_instructions,
            inject_keywords=True,
            validate_quality=True,
            max_retries=0,
        )

        if improved and not improved.startswith("["):
            scores_after = _score_match(improved, jd_text)
            return jsonify({
                "success": True,
                "improvedText": improved,
                "scoresBefore": scores_before,
                "scoresAfter": scores_after,
            })
        else:
            return jsonify({
                "success": False,
                "error": improved[:200] if improved else "Empty AI response",
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
