"""
Resume Reviewer Agent - Production-Level AI-Powered Resume Review & Correction System

This module provides a comprehensive, autonomous reviewer agent that:
1. Reviews tailored resumes for quality issues across multiple parameters
2. Automatically corrects identified issues when beneficial
3. Tracks all changes made with detailed explanations
4. Integrates seamlessly with the dashboard for visibility
5. Only makes changes when necessary - preserves already good resumes

Author: Suraj Panwar
Version: 1.0.0
"""
from __future__ import annotations

import re
import json
import hashlib
import os
from datetime import datetime
from typing import Optional, Literal, Any
from dataclasses import dataclass, field
from enum import Enum

from modules.helpers import print_lg


class ReviewSeverity(Enum):
    """Severity levels for review findings."""
    CRITICAL = "critical"     # Must fix - blocks submission
    HIGH = "high"             # Should fix - significantly impacts quality
    MEDIUM = "medium"         # Recommended fix - improves quality
    LOW = "low"               # Optional fix - minor improvement
    INFO = "info"             # Informational only


class ReviewCategory(Enum):
    """Categories of review findings."""
    ATS_COMPLIANCE = "ats_compliance"
    GRAMMAR_SPELLING = "grammar_spelling"
    KEYWORD_OPTIMIZATION = "keyword_optimization"
    STRUCTURE = "structure"
    FORMATTING = "formatting"
    CONSISTENCY = "consistency"
    CONTENT_QUALITY = "content_quality"
    CONTACT_INFO = "contact_info"
    QUANTIFICATION = "quantification"
    ACTION_VERBS = "action_verbs"


@dataclass
class ReviewFinding:
    """A single finding from the review process."""
    category: ReviewCategory
    severity: ReviewSeverity
    issue: str
    location: str  # Where in the resume
    original_text: Optional[str] = None
    corrected_text: Optional[str] = None
    explanation: str = ""
    auto_fixed: bool = False
    
    def to_dict(self) -> dict:
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "issue": self.issue,
            "location": self.location,
            "original_text": self.original_text,
            "corrected_text": self.corrected_text,
            "explanation": self.explanation,
            "auto_fixed": self.auto_fixed,
        }


@dataclass 
class ReviewReport:
    """Complete review report with findings and metrics."""
    # Metadata
    review_id: str = ""
    timestamp: str = ""
    job_title: str = ""
    company: str = ""
    
    # Scores (0-100)
    overall_score: float = 0.0
    ats_score: float = 0.0
    grammar_score: float = 0.0
    keyword_score: float = 0.0
    structure_score: float = 0.0
    consistency_score: float = 0.0
    
    # Findings
    findings: list[ReviewFinding] = field(default_factory=list)
    
    # Summary
    total_issues: int = 0
    critical_issues: int = 0
    auto_fixed_count: int = 0
    requires_attention: bool = False
    
    # Resume states
    original_resume: str = ""
    corrected_resume: str = ""
    was_modified: bool = False
    
    # Improvement summary
    improvements_made: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "review_id": self.review_id,
            "timestamp": self.timestamp,
            "job_title": self.job_title,
            "company": self.company,
            "overall_score": self.overall_score,
            "ats_score": self.ats_score,
            "grammar_score": self.grammar_score,
            "keyword_score": self.keyword_score,
            "structure_score": self.structure_score,
            "consistency_score": self.consistency_score,
            "total_issues": self.total_issues,
            "critical_issues": self.critical_issues,
            "auto_fixed_count": self.auto_fixed_count,
            "requires_attention": self.requires_attention,
            "was_modified": self.was_modified,
            "improvements_made": self.improvements_made,
            "findings": [f.to_dict() for f in self.findings],
        }


# ============================================================================
# PRODUCTION-LEVEL REVIEW CONFIGURATION
# ============================================================================

REVIEW_CONFIG = {
    # Auto-fix thresholds
    "auto_fix_enabled": True,
    "min_confidence_for_auto_fix": 0.85,
    "max_auto_fixes_per_resume": 20,
    
    # Quality thresholds
    "min_ats_score": 75.0,
    "target_ats_score": 85.0,
    "min_keyword_density": 1.5,
    "max_keyword_density": 6.0,
    "min_word_count": 250,
    "max_word_count": 900,
    
    # Structure requirements
    "required_sections": ["experience", "skills", "education"],
    "recommended_sections": ["summary", "contact"],
    
    # Grammar/Style
    "common_typos": {
        "teh": "the", "recieve": "receive", "seperate": "separate",
        "occured": "occurred", "accomodate": "accommodate",
        "acheive": "achieve", "beleive": "believe", "definitly": "definitely",
        "enviroment": "environment", "experiance": "experience",
        "managment": "management", "occassion": "occasion",
        "proffesional": "professional", "responsibilites": "responsibilities",
    },
    
    # Weak words to replace with action verbs
    "weak_phrases": {
        "responsible for": "managed",
        "worked on": "developed",
        "helped with": "contributed to",
        "was involved in": "led",
        "assisted with": "supported",
        "took part in": "participated in",
    },
    
    # Strong action verbs (by category)
    "action_verbs": {
        "leadership": ["led", "directed", "managed", "supervised", "coordinated", "mentored"],
        "achievement": ["achieved", "exceeded", "delivered", "accomplished", "earned", "attained"],
        "technical": ["developed", "built", "implemented", "engineered", "designed", "architected"],
        "improvement": ["improved", "optimized", "enhanced", "streamlined", "accelerated", "reduced"],
        "communication": ["presented", "communicated", "negotiated", "collaborated", "facilitated"],
    },
}


class ReviewerAgent:
    """
    Production-Level Resume Reviewer Agent
    
    Autonomously reviews, analyzes, and corrects tailored resumes to ensure
    they meet INDUSTRY-LEVEL quality standards before submission.
    
    Features:
    - Multi-phase review (structure, ATS, keywords, grammar, etc.)
    - Word-by-word analysis for professional standards
    - Auto-correction of issues
    - AI-powered fixes for complex issues
    - Iterative review loop until quality threshold met
    - Industry-level resume formatting validation
    """
    
    # Industry-standard resume requirements
    INDUSTRY_STANDARDS = {
        'max_pages': 1,
        'bullet_start_verbs': True,  # Bullets should start with action verbs
        'quantification_ratio': 0.4,  # 40% of bullets should have numbers
        'no_personal_pronouns': True,  # No I, me, my, we, our
        'no_articles_in_bullets': True,  # Bullets shouldn't start with a, an, the
        'consistent_tense': True,  # Past for past jobs, present for current
        'no_buzzwords': ['synergy', 'go-getter', 'think outside the box', 'guru', 'ninja', 'rockstar'],
        'required_contact_info': ['email', 'phone', 'linkedin'],
        'max_bullet_length': 150,  # Characters per bullet
        'min_bullet_length': 30,
        'font_recommendations': ['Arial', 'Calibri', 'Garamond', 'Times New Roman'],
        'margins_recommendation': '0.5-1 inch',
    }
    
    # Professional word replacements
    PROFESSIONAL_WORDS = {
        'helped': ['facilitated', 'enabled', 'supported', 'assisted'],
        'worked': ['collaborated', 'partnered', 'contributed'],
        'made': ['developed', 'created', 'established', 'built'],
        'did': ['executed', 'performed', 'completed', 'accomplished'],
        'got': ['obtained', 'acquired', 'secured', 'achieved'],
        'used': ['utilized', 'leveraged', 'employed', 'applied'],
        'ran': ['managed', 'directed', 'led', 'oversaw'],
        'changed': ['transformed', 'revised', 'modified', 'enhanced'],
        'fixed': ['resolved', 'remediated', 'corrected', 'addressed'],
        'started': ['initiated', 'launched', 'pioneered', 'established'],
    }
    
    def __init__(self, config: dict | None = None):
        self.config = config or REVIEW_CONFIG
        self._ai_client = None
        self._review_history: list[ReviewReport] = []
        self._max_review_iterations = 3  # Max AI fix iterations
        self._quality_threshold = 85.0  # Min score to pass (INDUSTRY STANDARD)

    def _log_review_outcome(self, report: ReviewReport, iteration: int) -> None:
        passed = report.overall_score >= self._quality_threshold and report.critical_issues == 0
        status = "PASSED" if passed else "SENT BACK"
        fixed = "FIXED" if report.was_modified or report.auto_fixed_count > 0 else "NO FIXES"
        print_lg(
            f"[Reviewer] RESULT: {status} | {fixed} | Score: {report.overall_score:.0f}% | "
            f"Critical: {report.critical_issues} | Iterations: {iteration}"
        )
        
    def review_and_fix_iteratively(
        self,
        tailored_resume: str,
        original_resume: str,
        job_description: str,
        job_title: str = "",
        company: str = "",
        max_iterations: int = 3,
    ) -> ReviewReport:
        """
        Review resume and iteratively fix issues until quality threshold met.
        
        This method:
        1. Reviews the resume
        2. If critical issues found, uses AI to fix them
        3. Re-reviews until score >= threshold or max iterations reached
        
        Returns:
            Final ReviewReport with fully corrected resume
        """
        print_lg("\n🔄 REVIEWER AGENT: Starting iterative review & fix process")
        print_lg(f"   └─ Job: {job_title} @ {company}")
        print_lg(f"   └─ Quality Threshold: {self._quality_threshold}%")
        print_lg(f"   └─ Max Iterations: {max_iterations}")
        
        current_resume = tailored_resume
        iteration = 0
        all_improvements = []
        total_auto_fixes = 0
        initial_score = None
        
        while iteration < max_iterations:
            iteration += 1
            print_lg(f"\n   ┌─ ITERATION {iteration}/{max_iterations} {'─'*30}")
            
            # Run review
            report = self.review_resume(
                tailored_resume=current_resume,
                original_resume=original_resume,
                job_description=job_description,
                job_title=job_title,
                company=company,
                auto_correct=True,
                use_ai_review=False,
            )
            
            if initial_score is None:
                initial_score = report.overall_score
            
            total_auto_fixes += report.auto_fixed_count
            all_improvements.extend(report.improvements_made)
            
            print_lg(f"   │ Score: {report.overall_score:.0f}% | Critical: {report.critical_issues} | Fixed: {report.auto_fixed_count}")
            
            # Check if quality threshold met (85% for industry standard)
            if report.overall_score >= self._quality_threshold and report.critical_issues == 0:
                print_lg(f"   └─ ✅ Quality threshold MET: {report.overall_score:.0f}% >= {self._quality_threshold:.0f}%")
                improvement = report.overall_score - initial_score if initial_score else 0
                print_lg(f"   └─ 📈 Total improvement: +{improvement:.0f}% over {iteration} iteration(s)")
                report.improvements_made = list(set(all_improvements))
                report.auto_fixed_count = total_auto_fixes
                self._log_review_outcome(report, iteration)
                return report
            
            # If critical issues remain, try AI fix
            if report.critical_issues > 0 or report.overall_score < 60:
                print_lg(f"   │ 🤖 Attempting AI fix for {report.critical_issues} critical issues...")
                fixed_resume = self._ai_fix_resume(
                    resume=report.corrected_resume,
                    report=report,
                    job_description=job_description,
                    job_title=job_title,
                )
                if fixed_resume and fixed_resume != current_resume:
                    current_resume = fixed_resume
                    all_improvements.append(f"AI fixed issues in iteration {iteration}")
                    print_lg("   │ ✅ AI applied fixes, re-reviewing...")
                    continue
                else:
                    print_lg("   │ ℹ️ No AI fixes applied")
            
            # Use the corrected resume for next iteration
            current_resume = report.corrected_resume
            
            # If score improved but still below threshold, continue
            if iteration < max_iterations and report.overall_score < self._quality_threshold:
                print_lg(f"   │ ⚠️ Score {report.overall_score:.0f}% below threshold {self._quality_threshold:.0f}%, continuing...")
                continue
            
            break
        
        # Final report
        report.improvements_made = list(set(all_improvements))
        report.auto_fixed_count = total_auto_fixes
        
        improvement = report.overall_score - initial_score if initial_score else 0
        print_lg(f"\n   ┌─ FINAL RESULTS {'─'*35}")
        print_lg(f"   │ Completed after {iteration} iteration(s)")
        print_lg(f"   │ Final Score: {report.overall_score:.0f}%")
        print_lg(f"   │ Total Improvement: +{improvement:.0f}%")
        print_lg(f"   │ Auto-Fixes Applied: {total_auto_fixes}")
        print_lg(f"   │ Improvements Made: {len(all_improvements)}")
        if report.overall_score < self._quality_threshold:
            print_lg(f"   └─ ⚠️ Could not reach {self._quality_threshold}% threshold")
        else:
            print_lg("   └─ ✅ Quality threshold achieved!")

        self._log_review_outcome(report, iteration)
        
        return report
    
    def _ai_fix_resume(
        self,
        resume: str,
        report: ReviewReport,
        job_description: str,
        job_title: str,
    ) -> Optional[str]:
        """Use AI to fix critical issues in the resume."""
        try:
            # Build fix prompt based on findings
            critical_issues = [f for f in report.findings if f.severity == ReviewSeverity.CRITICAL]
            high_issues = [f for f in report.findings if f.severity == ReviewSeverity.HIGH]
            
            if not critical_issues and not high_issues:
                return None
            
            issues_text = "\n".join([
                f"- {f.issue}: {f.explanation}" 
                for f in (critical_issues + high_issues)[:5]
            ])
            
            fix_prompt = f"""Fix the following issues in this resume:

ISSUES TO FIX:
{issues_text}

JOB TITLE: {job_title}

CURRENT RESUME:
{resume}

INSTRUCTIONS:
1. Fix ALL the listed issues
2. Keep the resume to exactly 1 page
3. Preserve the original format and structure
4. Only make necessary changes to fix the issues
5. Return ONLY the fixed resume text, no explanations

FIXED RESUME:"""

            # Use existing AI infrastructure from resume_tailoring
            from modules.ai.resume_tailoring import _call_ai_provider
            from config.secrets import ai_provider
            
            resolved_provider = (ai_provider or "ollama").lower()
            response = _call_ai_provider(resolved_provider, fix_prompt, client=None)
            
            if response and len(response) > 200:
                # Clean up response
                if "FIXED RESUME:" in response:
                    response = response.split("FIXED RESUME:")[-1].strip()
                return response
            
        except Exception as e:
            print_lg(f"   └─ AI fix error: {e}")
        
        return None
        
    def review_resume(
        self,
        tailored_resume: str,
        original_resume: str,
        job_description: str,
        job_title: str = "",
        company: str = "",
        auto_correct: bool = True,
        use_ai_review: bool = False,
    ) -> ReviewReport:
        """
        Comprehensive resume review with automatic correction.
        
        Args:
            tailored_resume: The AI-tailored resume to review
            original_resume: The original resume for reference
            job_description: The job description for keyword matching
            job_title: Job title for metadata
            company: Company name for metadata
            auto_correct: Whether to automatically fix issues
            use_ai_review: Whether to use AI for advanced review (requires API)
            
        Returns:
            ReviewReport with all findings and corrected resume
        """
        print_lg("🔍 Reviewer Agent: Starting COMPREHENSIVE INDUSTRY-LEVEL resume review...")
        
        # Initialize report
        report = ReviewReport(
            review_id=self._generate_review_id(tailored_resume),
            timestamp=datetime.now().isoformat(),
            job_title=job_title,
            company=company,
            original_resume=tailored_resume,
        )
        
        working_resume = tailored_resume
        issues_before = 0
        
        # === PHASE 1: Structure Analysis ===
        print_lg("   └─ Phase 1: Analyzing resume structure...")
        working_resume = self._review_structure(working_resume, report, auto_correct)
        phase1_issues = len(report.findings) - issues_before
        if phase1_issues > 0:
            print_lg(f"      └─ Found {phase1_issues} structure issue(s)")
        issues_before = len(report.findings)
        
        # === PHASE 2: ATS Compliance Check ===
        print_lg("   └─ Phase 2: Checking ATS compliance...")
        working_resume = self._review_ats_compliance(working_resume, job_description, report, auto_correct)
        phase2_issues = len(report.findings) - issues_before
        if phase2_issues > 0:
            print_lg(f"      └─ Found {phase2_issues} ATS issue(s)")
        issues_before = len(report.findings)
        
        # === PHASE 3: Keyword Optimization ===
        print_lg("   └─ Phase 3: Optimizing keywords...")
        working_resume = self._review_keywords(working_resume, job_description, report, auto_correct)
        phase3_issues = len(report.findings) - issues_before
        if phase3_issues > 0:
            print_lg(f"      └─ Found {phase3_issues} keyword issue(s)")
        issues_before = len(report.findings)
        
        # === PHASE 4: Grammar & Spelling ===
        print_lg("   └─ Phase 4: Checking grammar and spelling...")
        working_resume = self._review_grammar(working_resume, report, auto_correct)
        phase4_issues = len(report.findings) - issues_before
        if phase4_issues > 0:
            print_lg(f"      └─ Found {phase4_issues} grammar issue(s)")
        issues_before = len(report.findings)
        
        # === PHASE 5: Consistency Check ===
        print_lg("   └─ Phase 5: Verifying consistency...")
        working_resume = self._review_consistency(working_resume, original_resume, report, auto_correct)
        phase5_issues = len(report.findings) - issues_before
        if phase5_issues > 0:
            print_lg(f"      └─ Found {phase5_issues} consistency issue(s)")
        issues_before = len(report.findings)
        
        # === PHASE 6: Action Verb Enhancement ===
        print_lg("   └─ Phase 6: Enhancing action verbs...")
        working_resume = self._review_action_verbs(working_resume, report, auto_correct)
        phase6_issues = len(report.findings) - issues_before
        if phase6_issues > 0:
            print_lg(f"      └─ Found {phase6_issues} weak verb(s) to enhance")
        issues_before = len(report.findings)
        
        # === PHASE 7: Quantification Check ===
        print_lg("   └─ Phase 7: Checking quantification...")
        self._review_quantification(working_resume, report)
        phase7_issues = len(report.findings) - issues_before
        if phase7_issues > 0:
            print_lg(f"      └─ Found {phase7_issues} quantification issue(s)")
        issues_before = len(report.findings)
        
        # === PHASE 8: WORD-BY-WORD INDUSTRY STANDARD CHECK (NEW) ===
        print_lg("   └─ Phase 8: Word-by-word industry standard analysis...")
        working_resume = self._review_industry_standards(working_resume, report, auto_correct)
        phase8_issues = len(report.findings) - issues_before
        if phase8_issues > 0:
            print_lg(f"      └─ Found {phase8_issues} industry standard issue(s)")
        
        # === FINALIZE REPORT ===
        report.corrected_resume = working_resume
        report.was_modified = (working_resume != tailored_resume)
        
        # Calculate final scores
        self._calculate_final_scores(report, working_resume, job_description)
        
        # Summarize findings
        report.total_issues = len(report.findings)
        report.critical_issues = sum(1 for f in report.findings if f.severity == ReviewSeverity.CRITICAL)
        report.auto_fixed_count = sum(1 for f in report.findings if f.auto_fixed)
        report.requires_attention = report.critical_issues > 0 or report.overall_score < 70
        
        # Generate improvement summary
        if report.was_modified:
            report.improvements_made = self._generate_improvement_summary(report)
        
        # Store in history
        self._review_history.append(report)
        
        # Log summary
        self._log_review_summary(report)
        
        return report
    
    def _generate_review_id(self, text: str) -> str:
        """Generate unique review ID."""
        content = f"{text}_{datetime.now().isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:12]
    
    def _review_structure(self, resume: str, report: ReviewReport, auto_correct: bool) -> str:
        """Review and fix resume structure."""
        text_lower = resume.lower()
        
        # Check required sections
        section_patterns = {
            "experience": r'(?:experience|employment|work\s*history)',
            "skills": r'(?:skills|technologies|tech\s*stack|competencies)',
            "education": r'(?:education|degree|university|college)',
            "summary": r'(?:summary|profile|objective|about\s*me)',
            "contact": r'(?:email|phone|linkedin|@|\+\d)',
        }
        
        found_sections = {}
        for section, pattern in section_patterns.items():
            found_sections[section] = bool(re.search(pattern, text_lower))
        
        # Report missing required sections
        for section in self.config["required_sections"]:
            if not found_sections.get(section, False):
                report.findings.append(ReviewFinding(
                    category=ReviewCategory.STRUCTURE,
                    severity=ReviewSeverity.CRITICAL,
                    issue=f"Missing required section: {section.upper()}",
                    location="Document structure",
                    explanation=f"ATS systems expect a clear {section.upper()} section",
                ))
        
        # Report missing recommended sections
        for section in self.config["recommended_sections"]:
            if not found_sections.get(section, False):
                report.findings.append(ReviewFinding(
                    category=ReviewCategory.STRUCTURE,
                    severity=ReviewSeverity.MEDIUM,
                    issue=f"Missing recommended section: {section.upper()}",
                    location="Document structure",
                    explanation=f"Adding a {section.upper()} section improves readability",
                ))
        
        # Calculate structure score
        required_count = sum(1 for s in self.config["required_sections"] if found_sections.get(s, False))
        report.structure_score = (required_count / len(self.config["required_sections"])) * 100
        
        return resume
    
    def _review_ats_compliance(self, resume: str, job_description: str, report: ReviewReport, auto_correct: bool) -> str:
        """Review ATS compliance and fix issues."""
        working = resume
        
        # Check for problematic characters
        problematic_chars = {
            '\u2018': "'", '\u2019': "'",  # Smart quotes
            '\u201c': '"', '\u201d': '"',  # Smart double quotes
            '\u2013': '-', '\u2014': '-',  # En/Em dashes
            '\u2026': '...', '\u00a0': ' ', # Ellipsis, non-breaking space
        }
        
        for bad_char, good_char in problematic_chars.items():
            if bad_char in working:
                if auto_correct:
                    working = working.replace(bad_char, good_char)
                    report.findings.append(ReviewFinding(
                        category=ReviewCategory.ATS_COMPLIANCE,
                        severity=ReviewSeverity.LOW,
                        issue=f"Replaced problematic character",
                        location="Throughout document",
                        original_text=bad_char,
                        corrected_text=good_char,
                        auto_fixed=True,
                    ))
        
        return working
    
    def _review_keywords(self, resume: str, job_description: str, report: ReviewReport, auto_correct: bool) -> str:
        """Review keyword optimization."""
        resume_lower = resume.lower()
        jd_lower = job_description.lower()
        
        # Extract keywords from JD
        tech_keywords = self._extract_tech_keywords(jd_lower)
        
        # Check which keywords are present
        found = set()
        missing = set()
        
        for kw in tech_keywords:
            if kw in resume_lower:
                found.add(kw)
            else:
                missing.add(kw)
        
        # Calculate keyword score
        if tech_keywords:
            report.keyword_score = (len(found) / len(tech_keywords)) * 100
        else:
            report.keyword_score = 100.0
        
        # Report missing important keywords
        if missing:
            report.findings.append(ReviewFinding(
                category=ReviewCategory.KEYWORD_OPTIMIZATION,
                severity=ReviewSeverity.MEDIUM,
                issue=f"Missing {len(missing)} keywords from job description",
                location="Skills/Experience sections",
                explanation=f"Consider adding: {', '.join(list(missing)[:5])}...",
            ))
        
        return resume
    
    def _extract_tech_keywords(self, text: str) -> set:
        """Extract technical keywords from text."""
        tech_terms = {
            'python', 'java', 'javascript', 'typescript', 'go', 'rust', 'c++', 'c#',
            'react', 'angular', 'vue', 'node.js', 'django', 'flask', 'spring',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform',
            'sql', 'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch',
            'git', 'ci/cd', 'agile', 'scrum', 'devops', 'microservices',
            'machine learning', 'deep learning', 'nlp', 'data science',
            'rest', 'api', 'graphql', 'kafka', 'rabbitmq',
        }
        
        found = set()
        for term in tech_terms:
            if term in text:
                found.add(term)
        
        return found
    
    def _review_grammar(self, resume: str, report: ReviewReport, auto_correct: bool) -> str:
        """Review grammar and spelling."""
        working = resume
        fixes_made = 0
        
        # Fix common typos
        for typo, correction in self.config["common_typos"].items():
            pattern = re.compile(r'\b' + typo + r'\b', re.IGNORECASE)
            if pattern.search(working):
                if auto_correct:
                    working = pattern.sub(correction, working)
                    fixes_made += 1
                report.findings.append(ReviewFinding(
                    category=ReviewCategory.GRAMMAR_SPELLING,
                    severity=ReviewSeverity.HIGH,
                    issue=f"Spelling error: '{typo}'",
                    location="Document",
                    original_text=typo,
                    corrected_text=correction,
                    auto_fixed=auto_correct,
                ))
        
        # Calculate grammar score
        report.grammar_score = max(0, 100 - (fixes_made * 5))
        
        return working
    
    def _review_consistency(self, resume: str, original: str, report: ReviewReport, auto_correct: bool) -> str:
        """Review consistency with original resume."""
        # Check if contact info is preserved
        email_pattern = r'[\w.-]+@[\w.-]+\.\w+'
        original_emails = re.findall(email_pattern, original)
        resume_emails = re.findall(email_pattern, resume)
        
        if original_emails and not resume_emails:
            report.findings.append(ReviewFinding(
                category=ReviewCategory.CONSISTENCY,
                severity=ReviewSeverity.CRITICAL,
                issue="Contact email appears to be missing",
                location="Contact section",
            ))
        
        # Check for dramatic length changes
        original_words = len(original.split())
        resume_words = len(resume.split())
        
        if original_words > 0:
            change_ratio = resume_words / original_words
            if change_ratio < 0.5:
                report.findings.append(ReviewFinding(
                    category=ReviewCategory.CONSISTENCY,
                    severity=ReviewSeverity.HIGH,
                    issue="Resume is significantly shorter than original",
                    location="Overall document",
                    explanation=f"Original: {original_words} words, Tailored: {resume_words} words",
                ))
            elif change_ratio > 1.5:
                report.findings.append(ReviewFinding(
                    category=ReviewCategory.CONSISTENCY,
                    severity=ReviewSeverity.MEDIUM,
                    issue="Resume is significantly longer than original",
                    location="Overall document",
                    explanation=f"Original: {original_words} words, Tailored: {resume_words} words",
                ))
        
        report.consistency_score = 100 - (len([f for f in report.findings if f.category == ReviewCategory.CONSISTENCY]) * 20)
        
        return resume
    
    def _review_action_verbs(self, resume: str, report: ReviewReport, auto_correct: bool) -> str:
        """Review and enhance action verbs."""
        working = resume
        
        for weak, strong in self.config["weak_phrases"].items():
            pattern = re.compile(r'\b' + weak + r'\b', re.IGNORECASE)
            if pattern.search(working):
                if auto_correct:
                    working = pattern.sub(strong, working)
                report.findings.append(ReviewFinding(
                    category=ReviewCategory.ACTION_VERBS,
                    severity=ReviewSeverity.LOW,
                    issue=f"Weak phrase '{weak}' could be stronger",
                    location="Bullet points",
                    original_text=weak,
                    corrected_text=strong,
                    auto_fixed=auto_correct,
                ))
        
        return working
    
    def _review_quantification(self, resume: str, report: ReviewReport):
        """Check for quantified achievements."""
        # Count bullet points with numbers
        lines = resume.split('\n')
        bullet_lines = [line for line in lines if line.strip().startswith(('•', '-', '*', '●'))]
        quantified = [line for line in bullet_lines if re.search(r'\d+', line)]
        
        if bullet_lines:
            quant_ratio = len(quantified) / len(bullet_lines)
            if quant_ratio < 0.3:
                report.findings.append(ReviewFinding(
                    category=ReviewCategory.QUANTIFICATION,
                    severity=ReviewSeverity.MEDIUM,
                    issue=f"Only {len(quantified)}/{len(bullet_lines)} bullet points have metrics",
                    location="Experience section",
                    explanation="Add numbers, percentages, or metrics to strengthen impact",
                ))
    
    def _review_industry_standards(self, resume: str, report: ReviewReport, auto_correct: bool) -> str:
        """
        WORD-BY-WORD industry standard review.
        
        Checks EVERY word and sentence against professional resume standards:
        - No personal pronouns (I, me, my, we, our)
        - Bullets start with action verbs
        - No weak/filler words
        - No buzzwords
        - Proper capitalization
        - Professional word choices
        """
        working = resume
        lines = working.splitlines()
        modified_lines = []
        
        # Personal pronouns to remove (never use in professional resume)
        personal_pronouns = {'i', 'me', 'my', 'mine', 'myself', 'we', 'us', 'our', 'ours', 'ourselves'}
        
        # Filler words to flag
        filler_words = {'very', 'really', 'basically', 'actually', 'just', 'simply', 'absolutely'}
        
        # Buzzwords to avoid (industry standard)
        buzzwords = {'synergy', 'guru', 'ninja', 'rockstar', 'wizard', 'go-getter', 
                     'self-starter', 'think outside the box', 'leverage', 'paradigm'}
        
        # Weak verbs that should be stronger
        weak_verbs = {'helped', 'worked', 'did', 'made', 'got', 'was', 'were', 'had'}
        
        for line in lines:
            modified_line = line
            words = line.split()
            
            # Check each word
            for i, word in enumerate(words):
                word_lower = word.lower().strip('.,;:!?()[]{}')
                
                # Check for personal pronouns at sentence start
                if word_lower in personal_pronouns:
                    report.findings.append(ReviewFinding(
                        category=ReviewCategory.FORMATTING,
                        severity=ReviewSeverity.HIGH,
                        issue=f"Personal pronoun '{word}' found",
                        location=f"Line: {line[:50]}...",
                        explanation="Industry standard: Never use personal pronouns (I, me, my) in resumes",
                    ))
                
                # Check for filler words
                if word_lower in filler_words:
                    report.findings.append(ReviewFinding(
                        category=ReviewCategory.FORMATTING,
                        severity=ReviewSeverity.MEDIUM,
                        issue=f"Filler word '{word}' found",
                        location=f"Line: {line[:50]}...",
                        explanation="Remove filler words for more impactful language",
                    ))
                
                # Check for buzzwords
                if word_lower in buzzwords:
                    report.findings.append(ReviewFinding(
                        category=ReviewCategory.FORMATTING,
                        severity=ReviewSeverity.MEDIUM,
                        issue=f"Buzzword '{word}' found",
                        location=f"Line: {line[:50]}...",
                        explanation="Avoid cliché buzzwords - use concrete achievements instead",
                    ))
            
            # Check bullet points start with action verbs
            if modified_line.strip().startswith(('•', '-', '*', '●')):
                bullet_text = modified_line.strip().lstrip('•-*● ').strip()
                first_word = bullet_text.split()[0].lower() if bullet_text.split() else ''
                
                # Check if starts with weak verb
                if first_word in weak_verbs:
                    report.findings.append(ReviewFinding(
                        category=ReviewCategory.ACTION_VERBS,
                        severity=ReviewSeverity.MEDIUM,
                        issue=f"Bullet starts with weak verb '{first_word}'",
                        location=f"Bullet: {bullet_text[:50]}...",
                        explanation="Start bullets with strong action verbs (Led, Developed, Achieved)",
                    ))
                    
                    # Auto-correct weak verbs
                    if auto_correct and first_word in self.PROFESSIONAL_WORDS:
                        replacement = self.PROFESSIONAL_WORDS[first_word][0]
                        # Preserve capitalization
                        if bullet_text[0].isupper():
                            replacement = replacement.capitalize()
                        modified_line = modified_line.replace(first_word, replacement, 1)
                        report.findings[-1].auto_fixed = True
                        report.findings[-1].corrected_text = replacement
                
                # Check bullet length (industry standard: 1-2 lines, 30-150 chars)
                if len(bullet_text) > 150:
                    report.findings.append(ReviewFinding(
                        category=ReviewCategory.FORMATTING,
                        severity=ReviewSeverity.LOW,
                        issue=f"Bullet too long ({len(bullet_text)} chars)",
                        location=f"Bullet: {bullet_text[:50]}...",
                        explanation="Industry standard: Keep bullets to 1-2 lines (under 150 characters)",
                    ))
                elif len(bullet_text) < 30 and len(bullet_text) > 5:
                    report.findings.append(ReviewFinding(
                        category=ReviewCategory.FORMATTING,
                        severity=ReviewSeverity.LOW,
                        issue=f"Bullet too short ({len(bullet_text)} chars)",
                        location=f"Bullet: {bullet_text[:50]}...",
                        explanation="Add more detail or metrics to strengthen this bullet",
                    ))
            
            modified_lines.append(modified_line)
        
        # Check overall page length (industry standard: 1 page for < 10 years exp)
        word_count = len(working.split())
        if word_count > 800:
            report.findings.append(ReviewFinding(
                category=ReviewCategory.FORMATTING,
                severity=ReviewSeverity.HIGH,
                issue=f"Resume too long ({word_count} words)",
                location="Overall document",
                explanation="Industry standard: Keep resume to 1 page (~500-700 words) unless 10+ years experience",
            ))
        elif word_count < 250:
            report.findings.append(ReviewFinding(
                category=ReviewCategory.FORMATTING,
                severity=ReviewSeverity.HIGH,
                issue=f"Resume too short ({word_count} words)",
                location="Overall document",
                explanation="Resume lacks sufficient detail - add more achievements and skills",
            ))
        
        return '\n'.join(modified_lines)
    
    def _calculate_final_scores(self, report: ReviewReport, resume: str, job_description: str):
        """Calculate final scores."""
        # Weighted average of component scores
        weights = {
            'structure': 0.2,
            'ats': 0.25,
            'keywords': 0.25,
            'grammar': 0.15,
            'consistency': 0.15,
        }
        
        report.ats_score = report.keyword_score  # Use keyword score as ATS proxy
        
        report.overall_score = (
            report.structure_score * weights['structure'] +
            report.ats_score * weights['ats'] +
            report.keyword_score * weights['keywords'] +
            report.grammar_score * weights['grammar'] +
            report.consistency_score * weights['consistency']
        )
    
    def _generate_improvement_summary(self, report: ReviewReport) -> list[str]:
        """Generate human-readable improvement summary."""
        improvements = []
        
        fixed_findings = [f for f in report.findings if f.auto_fixed]
        
        grammar_fixes = [f for f in fixed_findings if f.category == ReviewCategory.GRAMMAR_SPELLING]
        if grammar_fixes:
            improvements.append(f"Fixed {len(grammar_fixes)} spelling/grammar issues")
        
        verb_fixes = [f for f in fixed_findings if f.category == ReviewCategory.ACTION_VERBS]
        if verb_fixes:
            improvements.append(f"Enhanced {len(verb_fixes)} weak phrases with stronger action verbs")
        
        ats_fixes = [f for f in fixed_findings if f.category == ReviewCategory.ATS_COMPLIANCE]
        if ats_fixes:
            improvements.append(f"Fixed {len(ats_fixes)} ATS compatibility issues")
        
        return improvements
    
    def _log_review_summary(self, report: ReviewReport):
        """Log detailed review summary with findings breakdown."""
        print_lg("\n📊 REVIEWER AGENT - DETAILED SUMMARY")
        print_lg(f"   ┌{'─'*50}")
        print_lg(f"   │ 🎯 Overall Quality Score: {report.overall_score:.0f}%")
        print_lg(f"   │ 📐 Structure Score: {report.structure_score:.0f}%")
        print_lg(f"   │ 🔑 Keyword Score: {report.keyword_score:.0f}%")
        print_lg(f"   │ ✏️  Grammar Score: {report.grammar_score:.0f}%")
        print_lg(f"   └{'─'*50}")
        
        # Count issues by severity
        critical = sum(1 for f in report.findings if f.severity == ReviewSeverity.CRITICAL)
        high = sum(1 for f in report.findings if f.severity == ReviewSeverity.HIGH)
        medium = sum(1 for f in report.findings if f.severity == ReviewSeverity.MEDIUM)
        low = sum(1 for f in report.findings if f.severity == ReviewSeverity.LOW)
        
        print_lg("\n📋 ISSUES BREAKDOWN:")
        print_lg(f"   └─ 🔴 Critical: {critical}")
        print_lg(f"   └─ 🟠 High: {high}")
        print_lg(f"   └─ 🟡 Medium: {medium}")
        print_lg(f"   └─ 🟢 Low: {low}")
        
        # Count issues by category
        category_counts = {}
        for f in report.findings:
            cat_name = f.category.value
            category_counts[cat_name] = category_counts.get(cat_name, 0) + 1
        
        if category_counts:
            print_lg("\n📂 ISSUES BY CATEGORY:")
            for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
                print_lg(f"   └─ {cat.replace('_', ' ').title()}: {count} issue(s)")
        
        # Log auto-fixes
        if report.auto_fixed_count > 0:
            print_lg(f"\n🔧 AUTO-FIXES APPLIED: {report.auto_fixed_count}")
            fixed = [f for f in report.findings if f.auto_fixed]
            for fix in fixed[:5]:  # Show first 5 fixes
                original = fix.original_text[:30] if fix.original_text else "N/A"
                corrected = fix.corrected_text[:30] if fix.corrected_text else "N/A"
                print_lg(f"   └─ {fix.category.value}: '{original}...' → '{corrected}...'")
            if len(fixed) > 5:
                print_lg(f"   └─ ... and {len(fixed) - 5} more fixes")
        
        # Log improvements made
        if report.improvements_made:
            print_lg("\n✅ IMPROVEMENTS MADE:")
            for imp in report.improvements_made:
                print_lg(f"   └─ {imp}")
        
        # Log remaining issues requiring attention
        remaining_critical = [f for f in report.findings if f.severity == ReviewSeverity.CRITICAL and not f.auto_fixed]
        if remaining_critical:
            print_lg("\n⚠️  REQUIRES MANUAL ATTENTION:")
            for issue in remaining_critical[:3]:
                print_lg(f"   └─ {issue.issue}")
                if issue.explanation:
                    print_lg(f"      💡 Note: {issue.explanation[:80]}...")
        
        # Final assessment
        if report.overall_score >= 85 and report.critical_issues == 0:
            print_lg("\n🌟 ASSESSMENT: PASSED - Resume meets industry standards!")
        elif report.overall_score >= 70:
            print_lg("\n✅ ASSESSMENT: GOOD - Resume is well-optimized")
        elif report.overall_score >= 50:
            print_lg("\n⚠️  ASSESSMENT: FAIR - Some improvements recommended")
        else:
            print_lg("\n❌ ASSESSMENT: NEEDS WORK - Significant issues found")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_agent_instance: ReviewerAgent | None = None


def get_reviewer_agent() -> ReviewerAgent:
    """Get or create singleton reviewer agent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = ReviewerAgent()
    return _agent_instance


def review_tailored_resume(
    tailored_resume: str,
    original_resume: str,
    job_description: str,
    job_title: str = "",
    company: str = "",
    auto_correct: bool = True,
) -> tuple[str, ReviewReport]:
    """
    Convenience function to review a tailored resume.
    
    Returns:
        Tuple of (corrected_resume, review_report)
    """
    agent = get_reviewer_agent()
    report = agent.review_resume(
        tailored_resume=tailored_resume,
        original_resume=original_resume,
        job_description=job_description,
        job_title=job_title,
        company=company,
        auto_correct=auto_correct,
    )
    return report.corrected_resume, report


def quick_review(resume: str, job_description: str) -> dict:
    """
    Quick review returning dashboard-friendly format.
    """
    agent = get_reviewer_agent()
    report = agent.review_resume(
        tailored_resume=resume,
        original_resume=resume,
        job_description=job_description,
        auto_correct=True,
        use_ai_review=False,
    )
    return {
        "score": report.overall_score,
        "issues": report.total_issues,
        "fixed": report.auto_fixed_count,
        "findings": [f.to_dict() for f in report.findings],
    }
