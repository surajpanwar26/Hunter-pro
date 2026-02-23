import re


def _clean(v: str) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def _extract_salary(text: str) -> str:
    ranges = re.findall(r"([$€£]\s?\d[\d,]*(?:\.\d+)?\s*(?:-|–|—|to)\s*[$€£]?\s?\d[\d,]*(?:\.\d+)?(?:\s*\/?\s*(?:year|yr|annum|hour|hr))?)", text, re.I)
    if ranges:
        return _clean(ranges[0])
    m = re.search(r"([$€£]\s?\d[\d,]*(?:\.\d+)?(?:\s*\/?\s*(?:year|yr|annum|hour|hr))?)", text, re.I)
    return _clean(m.group(1)) if m else ""


def _extract_visa(text: str) -> str:
    m = re.search(r"(visa\s*sponsorship[^\n.]{0,120}|sponsorship[^\n.]{0,120}|work authorization[^\n.]{0,120})", text, re.I)
    if not m:
        return ""
    sentence = _clean(m.group(1))
    if re.search(r"no\s+sponsorship|not\s+available|will\s+not\s+sponsor|cannot\s+sponsor", sentence, re.I):
        return "Not sponsored"
    if re.search(r"sponsorship\s+available|will\s+sponsor|can\s+sponsor|require\s+sponsorship|visa\s+support", sentence, re.I):
        return "Sponsorship available"
    return sentence


def test_salary_is_concise_range_for_adobe_like_text():
    text = (
        "Our compensation reflects the cost of labor across several U.S. geographic markets. "
        "The U.S. pay range for this position is $159,200 -- $301,600 annually. "
        "In California, the pay range for this position is $208,300 - $301,600."
    )
    salary = _extract_salary(text)
    assert "$301,600" in salary
    assert ("$159,200" in salary) or ("$208,300" in salary)
    assert "reflects the cost of labor" not in salary.lower()


def test_visa_status_is_short_and_normalized():
    t1 = "Visa sponsorship is not available for this role."
    t2 = "Work authorization and sponsorship available for select candidates."
    assert _extract_visa(t1) == "Not sponsored"
    assert _extract_visa(t2) == "Sponsorship available"
