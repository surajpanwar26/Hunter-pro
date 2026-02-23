import json
import tempfile
import time
from pathlib import Path

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

APPLY_URL = "https://careers.adobe.com/us/en/apply?jobSeqNo=ADOBUSR164985EXTERNALENUS&step=1&stepname=personalInformation"
API_BASE = "http://127.0.0.1:5001"
OUT = Path("test-results/adobe_apply_step_validation.json")


def _pick_resume_file_path() -> Path:
    health = requests.get(f"{API_BASE}/api/health", timeout=10)
    health.raise_for_status()

    mr = requests.get(f"{API_BASE}/api/master-resume", timeout=20)
    mr.raise_for_status()
    mr_json = mr.json()
    path = Path(str(mr_json.get("path") or "").strip())
    filename = str(mr_json.get("filename") or "master_resume.docx")

    if path.exists() and path.is_file() and path.suffix.lower() in {".pdf", ".docx"}:
        return path

    if not str(path):
        raise RuntimeError("master-resume path is missing from API response")

    f_resp = requests.get(f"{API_BASE}/api/resume-file", params={"path": str(path)}, timeout=45)
    f_resp.raise_for_status()

    suffix = Path(filename).suffix.lower() if Path(filename).suffix else ".docx"
    if suffix not in {".pdf", ".docx"}:
        suffix = ".docx"

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="adobe_apply_resume_")
    tmp.write(f_resp.content)
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


def _set_if_present(driver, selectors, value):
    for by, sel in selectors:
        try:
            el = driver.find_element(by, sel)
            if not el.is_displayed():
                continue
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            el.clear()
            el.send_keys(value)
            return True
        except Exception:
            continue
    return False


def run() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "url": APPLY_URL,
        "steps": [],
        "success": False,
        "errors": [],
    }

    try:
        resume_path = _pick_resume_file_path()
        report["steps"].append({
            "name": "resume_source",
            "ok": True,
            "path": str(resume_path),
            "suffix": resume_path.suffix.lower(),
            "bytes": resume_path.stat().st_size if resume_path.exists() else 0,
        })

        options = Options()
        options.page_load_strategy = "eager"
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1440,2200")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=options)
        try:
            wait = WebDriverWait(driver, 40)
            driver.get(APPLY_URL)
            wait.until(lambda d: d.execute_script("return document.readyState") in {"interactive", "complete"})
            time.sleep(3)

            file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
            report["steps"].append({"name": "file_inputs_found", "ok": len(file_inputs) > 0, "count": len(file_inputs)})

            upload_buttons = driver.find_elements(By.XPATH, "//*[self::button or self::a or self::span][contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'upload')]")
            report["steps"].append({"name": "upload_buttons_found", "ok": len(upload_buttons) > 0, "count": len(upload_buttons)})

            if not file_inputs:
                raise RuntimeError("No file input found on Adobe apply page")

            target_input = file_inputs[0]
            try:
                driver.execute_script(
                    "arguments[0].style.display='block'; arguments[0].style.visibility='visible'; arguments[0].style.opacity='1';",
                    target_input,
                )
            except Exception:
                pass

            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", target_input)
            target_input.send_keys(str(resume_path.resolve()))
            time.sleep(1)

            file_value = target_input.get_attribute("value") or ""
            uploaded_ok = bool(file_value.strip())
            report["steps"].append({"name": "resume_upload", "ok": uploaded_ok, "value": file_value[-120:]})
            if not uploaded_ok:
                raise RuntimeError("Failed to set resume file input value")

            first_ok = _set_if_present(driver, [
                (By.CSS_SELECTOR, "input[name*='first' i]"),
                (By.CSS_SELECTOR, "input[id*='first' i]"),
                (By.CSS_SELECTOR, "input[autocomplete='given-name']"),
            ], "Suraj")
            last_ok = _set_if_present(driver, [
                (By.CSS_SELECTOR, "input[name*='last' i]"),
                (By.CSS_SELECTOR, "input[id*='last' i]"),
                (By.CSS_SELECTOR, "input[autocomplete='family-name']"),
            ], "Panwar")
            email_ok = _set_if_present(driver, [
                (By.CSS_SELECTOR, "input[type='email']"),
                (By.CSS_SELECTOR, "input[name*='email' i]"),
                (By.CSS_SELECTOR, "input[id*='email' i]"),
                (By.CSS_SELECTOR, "input[autocomplete='email']"),
            ], "suraj.panwar@example.com")

            report["steps"].append({
                "name": "basic_fields_fillable",
                "ok": first_ok or last_ok or email_ok,
                "firstName": first_ok,
                "lastName": last_ok,
                "email": email_ok,
            })

            if not email_ok:
                report["errors"].append("Email field could not be filled via standard selectors on apply step")

        finally:
            driver.quit()

        report["success"] = all(step.get("ok") for step in report["steps"] if step.get("name") != "upload_buttons_found")
    except Exception as exc:
        report["success"] = False
        report["errors"].append(str(exc))

    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"success": report["success"], "report": str(OUT)}))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(run())
