"""
Resume Quality Validator - Validate AI output and ensure quality.

Features:
1. ATS score validation (target 85%+)
2. Resume structure validation
3. Keyword density check (avoid keyword stuffing)
4. Readability scoring
5. Auto-retry with improved prompts if quality is low
"""
from __future__ import annotations

import re
from typing import Optional
from dataclasses import dataclass, field

from modules.ai.jd_analyzer import JDAnalysis, analyze_jd_fast, calculate_resume_match_score


@dataclass
class QualityReport:
    """Quality assessment of a tailored resume."""
    
    # ATS Metrics
    ats_score: float = 0.0
    weighted_ats_score: float = 0.0
    keyword_coverage: float = 0.0
    
    # Quality Metrics
    structure_score: float = 0.0
    readability_score: float = 0.0
    keyword_density: float = 0.0  # Should be 2-5% for good ATS
    
    # Flags
    has_contact_info: bool = False
    has_summary: bool = False
    has_experience: bool = False
    has_skills: bool = False
    has_education: bool = False
    
    # Issues
    warnings: list[str] = field(default_factory=list)
    critical_issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    
    # Overall
    overall_grade: str = "F"  # A, B, C, D, F
    pass_threshold: bool = False


# Minimum thresholds for a quality resume
QUALITY_THRESHOLDS = {
    "ats_score_min": 75.0,  # Minimum ATS score
    "ats_score_target": 85.0,  # Target ATS score
    "keyword_density_min": 1.5,  # Minimum keyword density %
    "keyword_density_max": 6.0,  # Maximum (avoid stuffing)
    "min_word_count": 200,
    "max_word_count": 1000,
    "min_bullet_points": 5,
}


def validate_resume_structure(resume_text: str) -> dict:
    """Check if resume has all required sections."""
    text_lower = resume_text.lower()
    
    sections = {
        "contact": bool(re.search(r'(?:email|phone|linkedin|@|\+\d)', text_lower)),
        "summary": bool(re.search(r'(?:summary|profile|objective|about)', text_lower)),
        "experience": bool(re.search(r'(?:experience|employment|work\s*history)', text_lower)),
        "skills": bool(re.search(r'(?:skills|technologies|tech\s*stack|competencies)', text_lower)),
        "education": bool(re.search(r'(?:education|degree|university|college|b\.?s\.?|m\.?s\.?|phd)', text_lower)),
    }
    
    return sections


def calculate_readability_score(text: str) -> float:
    """
    Simple readability score based on:
    - Sentence length (shorter is better for ATS)
    - Word complexity (simpler is better)
    - Bullet point usage
    """
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if not sentences:
        return 0.0
    
    # Average words per sentence (target: 15-20)
    avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
    length_score = 100 - abs(17.5 - avg_sentence_length) * 3
    length_score = max(0, min(100, length_score))
    
    # Bullet point bonus
    bullet_count = len(re.findall(r'(?:^|\n)\s*[-*•]\s', text))
    bullet_score = min(100, bullet_count * 10)  # 10 bullets = 100%
    
    # Action verb usage (good for ATS)
    action_verbs = [
        'developed', 'built', 'created', 'implemented', 'designed', 'led', 'managed',
        'optimized', 'improved', 'reduced', 'increased', 'achieved', 'delivered',
        'automated', 'deployed', 'architected', 'collaborated', 'mentored'
    ]
    text_lower = text.lower()
    action_count = sum(1 for v in action_verbs if v in text_lower)
    action_score = min(100, action_count * 15)
    
    # Combined score
    return (length_score * 0.3 + bullet_score * 0.3 + action_score * 0.4)


def calculate_keyword_density(resume_text: str, keywords: set[str]) -> float:
    """Calculate keyword density as percentage of total words."""
    words = resume_text.lower().split()
    total_words = len(words)
    
    if total_words == 0:
        return 0.0
    
    keyword_count = 0
    for word in words:
        word_clean = re.sub(r'[^\w]', '', word)
        if word_clean in {kw.lower() for kw in keywords}:
            keyword_count += 1
    
    return (keyword_count / total_words) * 100


def validate_tailored_resume(
    original_resume: str,
    tailored_resume: str,
    job_description: str,
    jd_analysis: Optional[JDAnalysis] = None,
) -> QualityReport:
    """
    Comprehensive validation of a tailored resume.
    
    Returns a QualityReport with detailed metrics and recommendations.
    """
    report = QualityReport()
    
    # Get JD analysis if not provided
    if jd_analysis is None:
        jd_analysis = analyze_jd_fast(job_description)
    
    # Calculate ATS match score
    match_result = calculate_resume_match_score(tailored_resume, jd_analysis)
    report.ats_score = match_result["simple_score"]
    report.weighted_ats_score = match_result["weighted_score"]
    report.keyword_coverage = (match_result["matched_count"] / match_result["total_keywords"] * 100) if match_result["total_keywords"] > 0 else 0
    
    # Validate structure
    structure = validate_resume_structure(tailored_resume)
    report.has_contact_info = structure["contact"]
    report.has_summary = structure["summary"]
    report.has_experience = structure["experience"]
    report.has_skills = structure["skills"]
    report.has_education = structure["education"]
    report.structure_score = sum(structure.values()) / len(structure) * 100
    
    # Readability score
    report.readability_score = calculate_readability_score(tailored_resume)
    
    # Keyword density
    all_keywords = jd_analysis.get_all_keywords()
    report.keyword_density = calculate_keyword_density(tailored_resume, all_keywords)
    
    # Check for issues
    _check_issues(report, tailored_resume, original_resume, match_result, jd_analysis)
    
    # Calculate overall grade
    report.overall_grade = _calculate_grade(report)
    report.pass_threshold = report.weighted_ats_score >= QUALITY_THRESHOLDS["ats_score_min"]
    
    return report


def _check_issues(
    report: QualityReport,
    tailored: str,
    original: str,
    match_result: dict,
    analysis: JDAnalysis
) -> None:
    """Identify issues and generate suggestions."""
    
    # Critical issues
    if report.ats_score < 50:
        report.critical_issues.append(f"ATS score too low ({report.ats_score:.1f}%). Target: 75%+")
    
    if not report.has_experience:
        report.critical_issues.append("Missing EXPERIENCE section")
    
    if not report.has_skills:
        report.critical_issues.append("Missing SKILLS section")
    
    if match_result["missing_high_priority"]:
        missing = match_result["missing_high_priority"][:5]
        report.critical_issues.append(f"Missing critical keywords: {', '.join(missing)}")
    
    # Warnings
    if report.keyword_density > QUALITY_THRESHOLDS["keyword_density_max"]:
        report.warnings.append(f"Keyword density too high ({report.keyword_density:.1f}%). Risk of keyword stuffing.")
    
    if report.keyword_density < QUALITY_THRESHOLDS["keyword_density_min"]:
        report.warnings.append(f"Keyword density too low ({report.keyword_density:.1f}%). Add more relevant keywords.")
    
    word_count = len(tailored.split())
    if word_count < QUALITY_THRESHOLDS["min_word_count"]:
        report.warnings.append(f"Resume too short ({word_count} words). Add more detail.")
    
    if word_count > QUALITY_THRESHOLDS["max_word_count"]:
        report.warnings.append(f"Resume too long ({word_count} words). Consider condensing.")
    
    if not report.has_contact_info:
        report.warnings.append("No contact information detected")
    
    # Suggestions
    if match_result["missing_medium_priority"]:
        missing = match_result["missing_medium_priority"][:3]
        report.suggestions.append(f"Consider adding: {', '.join(missing)}")
    
    if report.readability_score < 70:
        report.suggestions.append("Use more action verbs and bullet points")
    
    if not report.has_summary:
        report.suggestions.append("Add a professional summary section")


def _calculate_grade(report: QualityReport) -> str:
    """Calculate overall letter grade."""
    # Weighted scoring
    score = (
        report.weighted_ats_score * 0.4 +
        report.structure_score * 0.2 +
        report.readability_score * 0.2 +
        (100 - len(report.critical_issues) * 20) * 0.2
    )
    
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"


def should_retry_tailoring(report: QualityReport) -> tuple[bool, str]:
    """
    Determine if we should retry the tailoring with a different prompt.
    
    Returns (should_retry, reason).
    """
    if report.critical_issues:
        return True, f"Critical issues: {report.critical_issues[0]}"
    
    if report.weighted_ats_score < QUALITY_THRESHOLDS["ats_score_min"]:
        return True, f"ATS score {report.weighted_ats_score:.1f}% below minimum {QUALITY_THRESHOLDS['ats_score_min']}%"
    
    if report.overall_grade in ("D", "F"):
        return True, f"Overall grade {report.overall_grade} is too low"
    
    return False, "Quality acceptable"


def get_retry_instructions(report: QualityReport, analysis: JDAnalysis) -> str:
    """
    Generate improved instructions for retry attempt based on what's missing.
    """
    instructions = ["IMPORTANT - Previous attempt had issues. Please ensure:"]
    
    if report.critical_issues:
        for issue in report.critical_issues[:3]:
            if "Missing critical keywords" in issue:
                # Extract keywords from the issue
                keywords = issue.replace("Missing critical keywords: ", "")
                instructions.append(f"- MUST include these keywords: {keywords}")
            else:
                instructions.append(f"- Fix: {issue}")
    
    if report.weighted_ats_score < 75:
        high_priority = analysis.high_priority_keywords[:10]
        instructions.append(f"- Prioritize adding: {', '.join(high_priority)}")
    
    if report.keyword_density > 6:
        instructions.append("- Reduce keyword repetition - use synonyms")
    
    if not report.has_skills:
        instructions.append("- Include a clear SKILLS section with relevant technologies")
    
    return "\n".join(instructions)


def format_quality_report(report: QualityReport) -> str:
    """Format the quality report for display."""
    lines = [
        "=" * 60,
        "RESUME QUALITY REPORT",
        "=" * 60,
        "",
        f"Overall Grade: {report.overall_grade}",
        f"Pass Threshold: {'✓' if report.pass_threshold else '✗'}",
        "",
        "ATS METRICS:",
        f"  Simple ATS Score: {report.ats_score:.1f}%",
        f"  Weighted ATS Score: {report.weighted_ats_score:.1f}%",
        f"  Keyword Coverage: {report.keyword_coverage:.1f}%",
        f"  Keyword Density: {report.keyword_density:.1f}%",
        "",
        "STRUCTURE:",
        f"  Structure Score: {report.structure_score:.1f}%",
        f"  Has Contact Info: {'✓' if report.has_contact_info else '✗'}",
        f"  Has Summary: {'✓' if report.has_summary else '✗'}",
        f"  Has Experience: {'✓' if report.has_experience else '✗'}",
        f"  Has Skills: {'✓' if report.has_skills else '✗'}",
        f"  Has Education: {'✓' if report.has_education else '✗'}",
        "",
        f"Readability Score: {report.readability_score:.1f}%",
    ]
    
    if report.critical_issues:
        lines.append("")
        lines.append("⚠️ CRITICAL ISSUES:")
        for issue in report.critical_issues:
            lines.append(f"  • {issue}")
    
    if report.warnings:
        lines.append("")
        lines.append("⚡ WARNINGS:")
        for warning in report.warnings:
            lines.append(f"  • {warning}")
    
    if report.suggestions:
        lines.append("")
        lines.append("💡 SUGGESTIONS:")
        for suggestion in report.suggestions:
            lines.append(f"  • {suggestion}")
    
    lines.append("")
    lines.append("=" * 60)
    
    return "\n".join(lines)


# Quick test
if __name__ == "__main__":
    test_jd = """
    Software Engineer - 3+ years Python, JavaScript, React, Node.js, PostgreSQL, MongoDB
    AWS, Docker, Kubernetes, CI/CD, Agile methodology, mentoring skills required.
    """
    
    test_original = """
    John Doe
    Software Developer
    
    EXPERIENCE
    - Built REST APIs with Python Flask
    - Worked with PostgreSQL databases
    - Deployed on AWS with Docker
    
    SKILLS
    Python, JavaScript, Flask, Docker, AWS, Git
    """
    
    test_tailored = """
    John Doe
    Software Engineer | Python | React | AWS | Kubernetes
    email@example.com | linkedin.com/in/johndoe
    
    SUMMARY
    Experienced Software Engineer with 3+ years building scalable applications
    using Python, JavaScript, React, and Node.js. Expert in cloud deployment
    with AWS, Docker, and Kubernetes. Strong advocate of Agile methodology
    and mentoring team members.
    
    EXPERIENCE
    Senior Software Developer | ABC Corp | 2020-Present
    - Developed RESTful APIs using Python Flask serving 1M+ requests
    - Built React frontends with TypeScript and Node.js backends
    - Managed PostgreSQL and MongoDB databases at scale
    - Deployed microservices on AWS using Docker and Kubernetes
    - Led Agile sprints and mentored junior developers
    - Implemented CI/CD pipelines reducing deployment time 50%
    
    SKILLS
    Python, JavaScript, TypeScript, React, Node.js, PostgreSQL, MongoDB,
    AWS, Docker, Kubernetes, CI/CD, Agile, REST APIs
    
    EDUCATION
    B.S. Computer Science | University | 2020
    """
    
    report = validate_tailored_resume(test_original, test_tailored, test_jd)
    print(format_quality_report(report))
