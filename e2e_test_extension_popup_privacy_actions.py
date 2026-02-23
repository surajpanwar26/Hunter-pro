import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POPUP_HTML = ROOT / "extension" / "popup.html"
POPUP_JS = ROOT / "extension" / "popup.js"
REPORT = ROOT / "test-results" / "extension_popup_privacy_actions_e2e.json"


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
        html = POPUP_HTML.read_text(encoding="utf-8")
        js = POPUP_JS.read_text(encoding="utf-8")

        report["steps"].append({
            "name": "files_loaded",
            "ok": True,
            "popupHtmlBytes": POPUP_HTML.stat().st_size,
            "popupJsBytes": POPUP_JS.stat().st_size,
        })

        html_ids = [
            "telemetryOptIn",
            "privacyDataSummary",
            "btnExportPersonalData",
            "btnSendDiagnostics",
            "btnClearPersonalData",
            "apiHealthStatus",
            "tailorFailureActions",
            "btnRetryTailorGuided",
            "btnOpenManualEditor",
            "btnDownloadCurrentDraft",
            "btnSendHumanReview",
        ]
        missing_html = [element_id for element_id in html_ids if f'id="{element_id}"' not in html]
        report["steps"].append({
            "name": "popup_html_ids",
            "ok": not missing_html,
            "checked": len(html_ids),
            "missing": missing_html,
        })
        if missing_html:
            raise RuntimeError(f"Missing popup.html IDs: {', '.join(missing_html)}")

        js_checks = {
            "telemetry_toggle_handler": r"elements\.telemetryOptIn\.addEventListener\('change'.*?refreshPrivacySummary\(\)",
            "personal_data_export_handler": r"elements\.btnExportPersonalData\.addEventListener\('click'.*?exportPersonalDataBundle\('personal-data'\)",
            "diagnostics_export_handler": r"elements\.btnSendDiagnostics\.addEventListener\('click'.*?exportPersonalDataBundle\('diagnostics'\)",
            "clear_personal_data_handler": r"elements\.btnClearPersonalData\.addEventListener\('click'.*?clearAllPersonalData\(\)",
            "offline_fallback_builder": r"function\s+buildOfflineTailorFallback\(",
            "failure_actions_toggle_function": r"function\s+setTailorFailureActionsVisible\(visible\)",
            "failure_actions_shown_on_reviewer_fail": r"setTailorFailureActionsVisible\(!result\.reviewerPassed\)",
            "retry_guided_click": r"elements\.btnRetryTailorGuided\.addEventListener\('click'",
            "manual_editor_click": r"elements\.btnOpenManualEditor\.addEventListener\('click'",
            "download_draft_click": r"elements\.btnDownloadCurrentDraft\.addEventListener\('click'",
            "human_review_packet_click": r"elements\.btnSendHumanReview\.addEventListener\('click'",
            "init_hides_failure_actions": r"setTailorFailureActionsVisible\(false\)",
        }

        failed_js_checks = [name for name, pattern in js_checks.items() if not has(pattern, js)]
        report["steps"].append({
            "name": "popup_js_wiring",
            "ok": not failed_js_checks,
            "checked": len(js_checks),
            "failed": failed_js_checks,
        })
        if failed_js_checks:
            raise RuntimeError(f"Missing popup.js wiring checks: {', '.join(failed_js_checks)}")

        report["success"] = True

    except Exception as exc:
        report["errors"].append(str(exc))
        report["success"] = False

    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"success": report["success"], "report": str(REPORT)}, indent=2))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
