import contextlib
import json
import os
import socket
import threading
import time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SITE_ROOT = PROJECT_ROOT / "tests" / "autopilot_site"
REPORT_PATH = PROJECT_ROOT / "test-results" / "autopilot_local_site_e2e.json"
API_BASE = "http://127.0.0.1:5001"

JD_TEXT = """Our Company\nWe are testing Auto Pilot on a local multi-step workflow.\n\nThe Opportunity\nBuild and deploy backend services using Java/Scala, REST, and distributed systems.\nCollaborate with product teams, mentor engineers, and maintain high code quality.\n\nRequirements\n- 5+ years software engineering\n- Java and/or Scala\n- Strong communication\n- Experience with APIs and microservices\n"""


class SiteHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE_ROOT), **kwargs)

    def log_message(self, format, *args):
        return


@contextlib.contextmanager
def run_local_site_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as test_sock:
        test_sock.bind(("127.0.0.1", 0))
        host, port = test_sock.getsockname()

    server = ThreadingHTTPServer(("127.0.0.1", port), SiteHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}/index.html"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def ensure_api_up():
    response = requests.get(f"{API_BASE}/api/health", timeout=10)
    response.raise_for_status()


def fetch_master_resume_text():
    response = requests.get(f"{API_BASE}/api/master-resume", timeout=20)
    response.raise_for_status()
    payload = response.json()
    text = str(payload.get("text") or "").strip()
    if len(text) < 120:
        raise RuntimeError("Master resume text too short for tailoring test")
    return text


def create_tailored_resume_file():
    master_text = fetch_master_resume_text()
    tailor_payload = {
        "resumeText": master_text,
        "jobDescription": JD_TEXT,
        "jobTitle": "Autopilot Local Site Test",
        "instructions": "Tailor for backend role while preserving factual accuracy.",
        "reviewIterations": 2,
    }

    response = requests.post(f"{API_BASE}/api/tailor", json=tailor_payload, timeout=240)
    if response.status_code >= 400:
        raise RuntimeError(f"Tailor API failed: {response.status_code} {response.text[:300]}")

    payload = response.json()
    if not payload.get("success"):
        raise RuntimeError(f"Tailor API unsuccessful: {str(payload)[:300]}")

    files = payload.get("files") or {}
    chosen = files.get("pdf") or files.get("docx")
    if not chosen:
        raise RuntimeError("Tailor response missing PDF/DOCX output path")

    chosen_path = Path(chosen)
    if not chosen_path.exists():
        raise RuntimeError(f"Tailored resume file missing: {chosen_path}")

    return chosen_path


def run_browser_flow(base_url: str, tailored_resume_path: Path):
    options = Options()
    options.page_load_strategy = "eager"
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1440,2000")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 25)

    try:
        driver.get(base_url)
        wait.until(EC.element_to_be_clickable((By.ID, "applyButton"))).click()

        wait.until(EC.presence_of_element_located((By.ID, "resumeUpload"))).send_keys(str(tailored_resume_path))
        driver.find_element(By.ID, "firstName").send_keys("Suraj")
        driver.find_element(By.ID, "lastName").send_keys("Panwar")
        driver.find_element(By.ID, "email").send_keys("surajpanwar26@gmail.com")
        driver.find_element(By.ID, "phone").send_keys("8108609815")
        driver.find_element(By.ID, "city").send_keys("Mumbai")
        driver.find_element(By.ID, "country").send_keys("India")
        driver.find_element(By.ID, "nextButtonStep1").click()

        wait.until(EC.presence_of_element_located((By.ID, "currentCompany"))).send_keys("Adobe")
        driver.find_element(By.ID, "currentTitle").send_keys("Software Engineer")
        driver.find_element(By.ID, "yearsExperience").send_keys("5")
        driver.find_element(By.ID, "workAuthorization").send_keys("Yes")
        driver.find_element(By.ID, "priorAdobeNo").click()
        driver.find_element(By.ID, "sponsorshipNo").click()
        driver.find_element(By.ID, "nextButtonStep2").click()

        wait.until(EC.element_to_be_clickable((By.ID, "submitButton"))).click()
        wait.until(EC.visibility_of_element_located((By.ID, "resultCard")))

        summary = driver.find_element(By.ID, "submittedSummary").text.strip()
        review_dump = driver.find_element(By.ID, "reviewData").text.strip()
        if "resume_upload" not in review_dump:
            raise RuntimeError("Uploaded resume field missing from final review data")

        return {
            "submittedSummary": summary,
            "reviewDataChars": len(review_dump),
            "tailoredResumePath": str(tailored_resume_path),
        }
    finally:
        driver.quit()


def main() -> int:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "success": False,
        "steps": [],
        "errors": [],
    }

    try:
        ensure_api_up()
        report["steps"].append({"name": "api_health", "ok": True})

        tailored_resume_path = create_tailored_resume_file()
        report["steps"].append({
            "name": "tailored_resume_generated",
            "ok": True,
            "path": str(tailored_resume_path),
            "ext": tailored_resume_path.suffix.lower(),
            "bytes": os.path.getsize(tailored_resume_path),
        })

        with run_local_site_server() as local_url:
            report["steps"].append({"name": "local_site_started", "ok": True, "url": local_url})
            browser_result = run_browser_flow(local_url, tailored_resume_path)
            report["steps"].append({"name": "browser_flow", "ok": True, **browser_result})

        report["success"] = True
    except Exception as exc:
        report["errors"].append(str(exc))
        report["success"] = False

    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"success": report["success"], "report": str(REPORT_PATH)}, indent=2))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
