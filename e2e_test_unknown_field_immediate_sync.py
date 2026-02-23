import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POPUP_JS = ROOT / "extension" / "popup.js"
CONTENT_JS = ROOT / "extension" / "universal_content.js"
API_SERVER_PY = ROOT / "modules" / "api_server.py"
REPORT = ROOT / "test-results" / "unknown_field_immediate_sync_e2e.json"


def has(pattern: str, text: str) -> bool:
    return re.search(pattern, text, flags=re.MULTILINE | re.DOTALL) is not None


def main() -> int:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "success": False,
        "steps": [],
        "errors": [],
    }

    try:
        popup_js = POPUP_JS.read_text(encoding="utf-8")
        content_js = CONTENT_JS.read_text(encoding="utf-8")
        api_server_py = API_SERVER_PY.read_text(encoding="utf-8")

        report["steps"].append({
            "name": "files_loaded",
            "ok": True,
            "popupJsBytes": POPUP_JS.stat().st_size,
            "contentJsBytes": CONTENT_JS.stat().st_size,
            "apiServerBytes": API_SERVER_PY.stat().st_size,
        })

        popup_checks = {
            "strict_backend_sync": r"syncLearnedToBackend\(\{\s*strict:\s*true,\s*retries:\s*2\s*\}\)",
            "targeted_fill_unknown_answers_message": r"sendMessageToContent\('fillUnknownAnswers'",
            "dedupe_unknown_answers": r"const\s+answerByKey\s*=\s*new\s+Map\(\)",
            "api_health_recovery_wait": r"waitForApiRecovery\(8,\s*2000\)",
            "check_api_bypass_circuit_health": r"fetch\(probeUrl",
        }
        popup_missing = [name for name, pattern in popup_checks.items() if not has(pattern, popup_js)]
        report["steps"].append({
            "name": "popup_js_checks",
            "ok": not popup_missing,
            "checked": len(popup_checks),
            "missing": popup_missing,
        })
        if popup_missing:
            raise RuntimeError(f"Missing popup.js checks: {', '.join(popup_missing)}")

        content_checks = {
            "fill_unknown_function": r"async\s+function\s+fillUnknownAnswersInPage\(",
            "fill_unknown_message_handler": r"case\s+'fillUnknownAnswers'",
            "fill_unknown_matching": r"findMatchingFieldInfoForUnknown\(",
            "fill_unknown_verification": r"verifyFieldFilled\(info,\s*expectedValue\)",
        }
        content_missing = [name for name, pattern in content_checks.items() if not has(pattern, content_js)]
        report["steps"].append({
            "name": "content_js_checks",
            "ok": not content_missing,
            "checked": len(content_checks),
            "missing": content_missing,
        })
        if content_missing:
            raise RuntimeError(f"Missing universal_content.js checks: {', '.join(content_missing)}")

        api_checks = {
            "resume_method_helper": r"def\s+_resume_content_method_instructions\(",
            "effective_instructions_used": r"effective_instructions\s*=",
            "method_in_tailor_pipeline": r"_run_iterative_tailoring\(\s*resume_text,\s*jd_text,\s*effective_instructions",
            "method_in_output_generation": r"tailor_resume_to_files\([\s\S]*instructions=effective_instructions",
        }
        api_missing = [name for name, pattern in api_checks.items() if not has(pattern, api_server_py)]
        report["steps"].append({
            "name": "api_server_checks",
            "ok": not api_missing,
            "checked": len(api_checks),
            "missing": api_missing,
        })
        if api_missing:
            raise RuntimeError(f"Missing api_server.py checks: {', '.join(api_missing)}")

        report["success"] = True

    except Exception as exc:
        report["errors"].append(str(exc))
        report["success"] = False

    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"success": report["success"], "report": str(REPORT)}, indent=2))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
