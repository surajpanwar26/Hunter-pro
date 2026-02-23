import json
import time
from pathlib import Path
from difflib import SequenceMatcher

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

ADOBE_URL = "https://careers.adobe.com/us/en/job/R164985/Senior-Software-Development-Engineer"
API_BASE = "http://127.0.0.1:5001"
OUT = Path("test-results/adobe_live_validation.json")

JS_EXTRACT = r"""
return (() => {
  const clean = (v) => String(v || '').replace(/\s+/g, ' ').trim();
  const trimCore = (input) => {
    let source = String(input || '').trim();
    if (!source) return '';
    const startMatch = source.match(/\b(job\s+description|our\s+company|the\s+opportunity|what\s+you\s+(?:will\s+)?do)\b/i);
    if (startMatch && typeof startMatch.index === 'number') source = source.slice(startMatch.index).trim();
    const endMatch = source.match(/\b(similar\s+jobs|share\s+this\s+opportunity|get\s+notified\s+for\s+similar\s+jobs|join\s+our\s+talent\s+community|see\s+more)\b/i);
    if (endMatch && typeof endMatch.index === 'number' && endMatch.index > 300) source = source.slice(0, endMatch.index).trim();
    return clean(source);
  };
  const selectors = [
    '[data-automation-id="jobPostingDescription"]',
    '[data-automation-id="job-description"]',
    '.jobs-description-content__text',
    '.jobs-description',
    '.job-description',
    '.jobDescriptionContent',
    '[class*="jobDescription"]',
    '[class*="job-description"]',
    '[id*="jobDescription"]',
    'article',
    'main'
  ];
  const keywords = [
    'responsibilities', 'requirements', 'qualifications', 'experience',
    'skills', 'about the role', 'what you', 'job description',
    'preferred', 'benefits'
  ];

  const map = new Map();
  for (const sel of selectors) {
    try {
      for (const el of document.querySelectorAll(sel)) {
        if (!map.has(el)) map.set(el, sel);
      }
    } catch {}
  }

  let bestText = '';
  let bestScore = -1;
  for (const [el, sel] of map.entries()) {
    const t = clean(el.textContent || '');
    if (t.length < 180) continue;
    const low = t.toLowerCase();
    let score = Math.min(t.length / 80, 260);
    for (const kw of keywords) if (low.includes(kw)) score += 18;
    if (/job|description|posting|detail|role|position/i.test(sel)) score += 24;
    if (score > bestScore) {
      bestScore = score;
      bestText = t;
    }
  }

  let jsonLdDescription = '';
  const scripts = Array.from(document.querySelectorAll('script[type="application/ld+json"]'));
  for (const script of scripts) {
    try {
      const parsed = JSON.parse(script.textContent || '{}');
      const arr = Array.isArray(parsed) ? parsed : (Array.isArray(parsed['@graph']) ? parsed['@graph'] : [parsed]);
      for (const item of arr) {
        const type = item?.['@type'];
        const isJob = Array.isArray(type) ? type.some(x => String(x).toLowerCase() === 'jobposting') : String(type || '').toLowerCase() === 'jobposting';
        if (isJob && item?.description) {
          const div = document.createElement('div');
          div.innerHTML = String(item.description);
          const txt = clean(div.textContent || div.innerText || '');
          if (txt.length > jsonLdDescription.length) jsonLdDescription = txt;
        }
      }
    } catch {}
  }

  const merged = [bestText, jsonLdDescription]
    .filter(Boolean)
    .filter((v, i, a) => a.findIndex(x => x.slice(0, 180) === v.slice(0, 180)) === i)
    .join('\n\n')
    .trim();

  const finalDescription = trimCore(merged || bestText || jsonLdDescription || '');

  const title = clean(document.querySelector('h1')?.textContent || document.title || '').replace(/\s*\|.*$/, '').trim();

  const ranges = Array.from(finalDescription.matchAll(/([$€£]\s?\d[\d,]*(?:\.\d+)?\s*(?:-|–|—|to)\s*[$€£]?\s?\d[\d,]*(?:\.\d+)?(?:\s*\/?\s*(?:year|yr|annum|hour|hr))?)/gi));
  const salary = clean(ranges[0]?.[1] || finalDescription.match(/([$€£]\s?\d[\d,]*(?:\.\d+)?(?:\s*\/?\s*(?:year|yr|annum|hour|hr))?)/i)?.[1] || '');

  const visaLine = finalDescription.match(/(visa\s*sponsorship[^\n.]{0,120}|sponsorship[^\n.]{0,120}|work authorization[^\n.]{0,120})/i);
  let visa = clean(visaLine ? visaLine[1] : '');
  if (/no\s+sponsorship|not\s+available|will\s+not\s+sponsor|cannot\s+sponsor/i.test(visa)) visa = 'Not sponsored';
  else if (/sponsorship\s+available|will\s+sponsor|can\s+sponsor|require\s+sponsorship|visa\s+support/i.test(visa)) visa = 'Sponsorship available';

  const norm = finalDescription.toLowerCase();
  const idx = (terms) => {
    let best = -1;
    for (const term of terms) {
      const i = norm.indexOf(term.toLowerCase());
      if (i >= 0 && (best === -1 || i < best)) best = i;
    }
    return best;
  };
  const sliceSection = (startTerms, endTerms, maxLen = 1800) => {
    const start = idx(startTerms);
    if (start < 0) return '';
    let end = finalDescription.length;
    for (const endTerm of endTerms) {
      const i = norm.indexOf(endTerm.toLowerCase(), start + 10);
      if (i > start && i < end) end = i;
    }
    const raw = finalDescription.slice(start, Math.min(end, start + maxLen));
    return clean(raw.replace(/^.{0,80}?:?\s*/i, ''));
  };

  return {
    title,
    description: finalDescription,
    descriptionChars: finalDescription.length,
    descriptionWords: finalDescription ? finalDescription.split(/\s+/).length : 0,
    salary,
    visaSponsorship: visa,
    structured: {
      summary: sliceSection(
        ['the opportunity', 'about this role', 'about the role', 'job summary', 'role summary'],
        ["what you'll do", 'what you will do', 'responsibilities', 'requirements', 'what you need to succeed', 'our compensation', 'state-specific notices']
      ),
      responsibilities: sliceSection(
        ["what you'll do", 'what you will do', 'responsibilities', 'duties'],
        ['what you need to succeed', 'requirements', 'qualifications', 'bonus', 'our compensation', 'state-specific notices']
      ),
      requirements: sliceSection(
        ['what you need to succeed', 'requirements', 'qualifications', 'must have'],
        ['bonus', 'our compensation', 'state-specific notices']
      )
    },
    url: location.href
  };
})();
"""


def run() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "url": ADOBE_URL,
        "steps": [],
        "success": False,
        "errors": [],
    }

    try:
        # Browser validation (live page)
        options = Options()
        options.page_load_strategy = "eager"
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1440,2200")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=options)
        try:
            driver.set_page_load_timeout(45)
            try:
                driver.get(ADOBE_URL)
            except TimeoutException:
                report["steps"].append({"name": "navigate_timeout_fallback", "ok": True})
            WebDriverWait(driver, 40).until(lambda d: d.execute_script("return document.readyState") in {"interactive", "complete"})
            time.sleep(4)
            jd = driver.execute_script(JS_EXTRACT)
            report["jd"] = jd
            report["steps"].append({"name": "live_jd_extract", "ok": True, "chars": jd.get("descriptionChars", 0), "words": jd.get("descriptionWords", 0)})
        finally:
            driver.quit()

        if report.get("jd", {}).get("descriptionWords", 0) < 250:
            raise RuntimeError("Detected JD content is still too short (<250 words)")

        jd = report.get("jd", {})
        if len(str(jd.get("title", "")).strip()) < 5:
          raise RuntimeError("Detected role/title is missing or too short")
        salary = str(jd.get("salary", "")).strip().lower()
        if salary and ("reflects the cost of labor" in salary or len(salary) > 90):
          raise RuntimeError("Detected salary is not concise/on-point")
        visa = str(jd.get("visaSponsorship", "")).strip()
        if len(visa) > 80:
          raise RuntimeError("Detected visa sponsorship text is too long")
        structured = jd.get("structured") or {}
        if not any(str(structured.get(k, "")).strip() for k in ("summary", "responsibilities", "requirements")):
          raise RuntimeError("No structured JD sections detected")

        # Backend tailoring/review validation
        health = requests.get(f"{API_BASE}/api/health", timeout=10)
        health.raise_for_status()
        report["steps"].append({"name": "api_health", "ok": True, "provider": health.json().get("provider")})

        mr = requests.get(f"{API_BASE}/api/master-resume", timeout=20)
        mr.raise_for_status()
        mr_json = mr.json()
        resume_text = str(mr_json.get("text", ""))
        if len(resume_text.strip()) < 120:
            raise RuntimeError("Master resume text is too short for tailoring test")
        report["steps"].append({"name": "master_resume", "ok": True, "filename": mr_json.get("filename")})

        defaults = requests.get(f"{API_BASE}/api/default-instructions", timeout=10)
        defaults.raise_for_status()
        default_json = defaults.json()
        instructions = str(default_json.get("tailoringInstructions") or default_json.get("instructions") or "").strip()
        reviewer_instructions = str(default_json.get("reviewerInstructions") or "").strip()
        report["steps"].append({
            "name": "instruction_defaults",
            "ok": True,
            "tailoringChars": len(instructions),
            "reviewerChars": len(reviewer_instructions),
        })

        tailor_payload = {
            "resumeText": resume_text,
            "jobDescription": report["jd"]["description"],
            "jobTitle": report["jd"].get("title") or "Senior Software Development Engineer",
            "instructions": instructions,
            "reviewIterations": 2,
        }
        t_resp = requests.post(f"{API_BASE}/api/tailor", json=tailor_payload, timeout=180)
        if t_resp.status_code >= 400:
            raise RuntimeError(f"Tailor API failed ({t_resp.status_code}): {t_resp.text[:300]}")
        t_json = t_resp.json()
        if not t_json.get("success"):
            raise RuntimeError(f"Tailor API unsuccessful: {str(t_json)[:300]}")
        report["steps"].append({
            "name": "tailor",
            "ok": True,
            "atsAfter": (t_json.get("scoresAfter") or {}).get("ats"),
            "matchAfter": (t_json.get("scoresAfter") or {}).get("match"),
            "quality": t_json.get("quality"),
        })

        files = t_json.get("files") or {}
        available_artifacts = []
        for fmt in ("pdf", "docx"):
            path = str(files.get(fmt) or "").strip()
            if path:
                available_artifacts.append((fmt, path))
        if not available_artifacts:
            raise RuntimeError("Tailor output missing both PDF and DOCX files")

        tailored_text = str(t_json.get("tailoredText") or "").strip()
        if len(tailored_text) < 180:
            raise RuntimeError("Tailored text is too short for format/content validation")

        format_checks = []
        format_warnings = []
        for fmt, artifact_path in available_artifacts:
            f_resp = requests.get(f"{API_BASE}/api/resume-file", params={"path": artifact_path}, timeout=45)
            if f_resp.status_code >= 400:
                format_warnings.append(f"Failed to fetch tailored {fmt.upper()} file ({f_resp.status_code})")
                continue

            raw_bytes = list(f_resp.content)
            x_resp = requests.post(
                f"{API_BASE}/api/extract-resume-text",
                json={
                    "fileName": f"tailored_resume.{fmt}",
                    "fileBytes": raw_bytes,
                },
                timeout=90,
            )
            if x_resp.status_code >= 400:
                format_warnings.append(f"Failed to extract text from {fmt.upper()} file ({x_resp.status_code})")
                continue

            x_json = x_resp.json()
            extracted = str(x_json.get("text") or "").strip()
            if len(extracted) < 180:
                format_warnings.append(f"Extracted {fmt.upper()} text is too short/invalid")
                continue

            similarity = SequenceMatcher(None, tailored_text.lower(), extracted.lower()).ratio()
            if similarity < 0.55:
                format_warnings.append(f"Extracted {fmt.upper()} content diverges too much from tailored text (ratio={similarity:.2f})")
                continue

            format_checks.append({
                "format": fmt,
                "bytes": len(raw_bytes),
                "chars": len(extracted),
                "similarity": round(similarity, 3),
            })

        if not format_checks:
            raise RuntimeError(
                "No valid DOCX/PDF artifact passed extraction/content checks"
                + (f"; warnings: {' | '.join(format_warnings[:3])}" if format_warnings else "")
            )

        report["steps"].append({
            "name": "tailored_format_content_validation",
            "ok": True,
            "checks": format_checks,
            "warnings": format_warnings,
        })

        review_payload = {
            "tailoredText": t_json.get("tailoredText") or "",
            "masterText": t_json.get("masterText") or resume_text,
            "jobDescription": report["jd"]["description"],
        }
        r_resp = requests.post(f"{API_BASE}/api/review", json=review_payload, timeout=180)
        if r_resp.status_code >= 400:
            raise RuntimeError(f"Review API failed ({r_resp.status_code}): {r_resp.text[:300]}")
        r_json = r_resp.json()
        if not r_json.get("success"):
            raise RuntimeError(f"Review API unsuccessful: {str(r_json)[:300]}")

        report["steps"].append({
            "name": "review",
            "ok": True,
            "reviewerPassed": r_json.get("reviewerPassed"),
            "reviewer": r_json.get("reviewer"),
            "atsAfter": (r_json.get("scoresAfter") or {}).get("ats"),
            "matchAfter": (r_json.get("scoresAfter") or {}).get("match"),
        })

        report["success"] = True

    except Exception as exc:
        report["errors"].append(str(exc))
        report["success"] = False

    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"success": report["success"], "report": str(OUT)}, indent=2))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(run())
