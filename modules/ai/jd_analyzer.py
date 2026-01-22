"""
Smart Job Description Analyzer - Extract insights for better resume tailoring.

Features:
1. AI-powered keyword extraction (required vs nice-to-have)
2. Experience level detection
3. Company culture signals
4. Industry-specific terminology mapping
5. Weighted keyword scoring for prioritization
"""
from __future__ import annotations

import re
import json
from typing import Optional
from dataclasses import dataclass, field, asdict

from config.secrets import ai_provider


@dataclass
class JDAnalysis:
    """Structured analysis of a job description."""
    
    # Core requirements
    required_skills: list[str] = field(default_factory=list)
    nice_to_have_skills: list[str] = field(default_factory=list)
    
    # Technical categories (weighted by importance)
    programming_languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    databases: list[str] = field(default_factory=list)
    cloud_platforms: list[str] = field(default_factory=list)
    devops_tools: list[str] = field(default_factory=list)
    
    # Soft skills and practices
    methodologies: list[str] = field(default_factory=list)
    soft_skills: list[str] = field(default_factory=list)
    
    # Context
    experience_years: tuple[int, int] = (0, 0)  # (min, max)
    seniority_level: str = "mid"  # junior, mid, senior, lead, principal
    team_size_hint: str = ""
    remote_policy: str = ""
    
    # Weighted keywords for ATS optimization
    high_priority_keywords: list[str] = field(default_factory=list)
    medium_priority_keywords: list[str] = field(default_factory=list)
    low_priority_keywords: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def get_all_keywords(self) -> set[str]:
        """Get all keywords for ATS matching."""
        all_kw = set()
        all_kw.update(self.required_skills)
        all_kw.update(self.nice_to_have_skills)
        all_kw.update(self.programming_languages)
        all_kw.update(self.frameworks)
        all_kw.update(self.databases)
        all_kw.update(self.cloud_platforms)
        all_kw.update(self.devops_tools)
        all_kw.update(self.methodologies)
        all_kw.update(self.soft_skills)
        return all_kw


# Comprehensive keyword database with patterns
KEYWORD_PATTERNS = {
    "programming_languages": {
        "patterns": [
            r'\b(python|java|kotlin|go|golang|scala|javascript|typescript|c\+\+|c#|ruby|rust|php|swift|perl|r\b|julia|elixir|clojure|haskell|lua|dart|groovy)\b'
        ],
        "priority": "high",
        "aliases": {"golang": "Go", "js": "JavaScript", "ts": "TypeScript", "py": "Python"}
    },
    "frameworks": {
        "patterns": [
            r'\b(spring\s*boot|spring|flask|django|fastapi|express|node\.?js|react|angular|vue|\.net|rails|laravel|nextjs|nuxt|svelte|nestjs|gin|echo|fiber|actix)\b'
        ],
        "priority": "high",
        "aliases": {"springboot": "Spring Boot", "nodejs": "Node.js"}
    },
    "databases": {
        "patterns": [
            r'\b(postgresql|postgres|mysql|mongodb|dynamodb|cassandra|redis|elasticsearch|oracle|sql\s*server|sqlite|mariadb|couchdb|neo4j|cockroachdb|timescaledb|influxdb)\b',
            r'\b(nosql|rdbms|sql)\b'
        ],
        "priority": "high",
        "aliases": {"postgres": "PostgreSQL", "mongo": "MongoDB", "dynamo": "DynamoDB"}
    },
    "cloud_platforms": {
        "patterns": [
            r'\b(aws|amazon\s*web\s*services|azure|gcp|google\s*cloud|heroku|digitalocean|cloudflare|vercel|netlify)\b',
            r'\b(ec2|s3|lambda|ecs|eks|rds|sqs|sns|cloudwatch|route53|cloudfront|vpc|iam)\b',  # AWS services
            r'\b(saas|paas|iaas)\b'
        ],
        "priority": "high",
        "aliases": {"amazon web services": "AWS", "google cloud": "GCP"}
    },
    "devops_tools": {
        "patterns": [
            r'\b(docker|kubernetes|k8s|jenkins|terraform|ansible|puppet|chef|gitlab|github\s*actions|circleci|travis|argo|helm|istio|prometheus|grafana|datadog|splunk|elk)\b',
            r'\b(ci/?cd|continuous\s*integration|continuous\s*deployment|continuous\s*delivery)\b'
        ],
        "priority": "high",
        "aliases": {"k8s": "Kubernetes", "ci/cd": "CI/CD"}
    },
    "methodologies": {
        "patterns": [
            r'\b(agile|scrum|kanban|waterfall|devops|devsecops|sre|lean|xp|extreme\s*programming|pair\s*programming|tdd|bdd|ddd)\b'
        ],
        "priority": "medium",
        "aliases": {}
    },
    "architecture": {
        "patterns": [
            r'\b(microservices?|monolith|serverless|event[\s-]?driven|cqrs|event\s*sourcing|rest(?:ful)?|graphql|grpc|soap|message\s*queue|pub[\s-]?sub)\b',
            r'\b(distributed\s*systems?|high\s*availability|fault\s*tolerant|scalab(?:le|ility)|load\s*balanc(?:ing|er))\b'
        ],
        "priority": "high",
        "aliases": {"rest": "REST", "restful": "RESTful"}
    },
    "soft_skills": {
        "patterns": [
            r'\b(mentor(?:ing)?|leadership|lead|collaborat(?:e|ion)|communicat(?:e|ion)|team\s*player|cross[\s-]?functional|stakeholder)\b',
            r'\b(problem[\s-]?solving|critical\s*thinking|analytical|detail[\s-]?oriented|self[\s-]?starter|proactive)\b'
        ],
        "priority": "medium",
        "aliases": {}
    },
    "practices": {
        "patterns": [
            r'\b(code\s*review|testing|unit\s*test(?:ing)?|integration\s*test(?:ing)?|e2e|security|performance|reliability|monitoring|observability|logging|documentation)\b'
        ],
        "priority": "medium",
        "aliases": {}
    }
}

# Experience level indicators
SENIORITY_PATTERNS = {
    "junior": [r'\b(junior|entry[\s-]?level|0-2\s*years?|1-2\s*years?|1-3\s*years?|graduate|intern)\b'],
    "mid": [r'\b(mid[\s-]?level|3-5\s*years?|2-4\s*years?|4-6\s*years?)\b'],
    "senior": [r'\b(senior|5\+\s*years?|5-8\s*years?|6-10\s*years?|7\+\s*years?|experienced)\b'],
    "lead": [r'\b(lead|principal|staff|8\+\s*years?|10\+\s*years?|architect)\b'],
}


def analyze_jd_fast(job_description: str) -> JDAnalysis:
    """
    Fast regex-based JD analysis (no AI required).
    Use this for local/offline processing.
    """
    jd_lower = job_description.lower()
    analysis = JDAnalysis()
    
    # Extract keywords by category
    for category, config in KEYWORD_PATTERNS.items():
        keywords = set()
        for pattern in config["patterns"]:
            matches = re.findall(pattern, jd_lower, re.IGNORECASE)
            # Normalize and add matches
            for match in matches:
                normalized = config.get("aliases", {}).get(match.lower(), match)
                keywords.add(normalized)
        
        # Assign to appropriate field
        if category == "programming_languages":
            analysis.programming_languages = list(keywords)
        elif category == "frameworks":
            analysis.frameworks = list(keywords)
        elif category == "databases":
            analysis.databases = list(keywords)
        elif category == "cloud_platforms":
            analysis.cloud_platforms = list(keywords)
        elif category == "devops_tools":
            analysis.devops_tools = list(keywords)
        elif category == "methodologies":
            analysis.methodologies = list(keywords)
        elif category == "soft_skills":
            analysis.soft_skills = list(keywords)
        
        # Add to priority lists
        priority = config.get("priority", "medium")
        if priority == "high":
            analysis.high_priority_keywords.extend(keywords)
        elif priority == "medium":
            analysis.medium_priority_keywords.extend(keywords)
        else:
            analysis.low_priority_keywords.extend(keywords)
    
    # Detect experience requirements
    exp_matches = re.findall(r'(\d+)\+?\s*(?:-\s*(\d+))?\s*years?', jd_lower)
    if exp_matches:
        min_exp = min(int(m[0]) for m in exp_matches)
        max_exp = max(int(m[1]) if m[1] else int(m[0]) for m in exp_matches)
        analysis.experience_years = (min_exp, max_exp)
    
    # Detect seniority level
    for level, patterns in SENIORITY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, jd_lower):
                analysis.seniority_level = level
                break
    
    # Detect required vs nice-to-have (simple heuristics)
    # Split JD into sections
    required_section = ""
    nice_to_have_section = ""
    
    # Look for "required" section
    req_match = re.search(r'(?:requirements?|required|must\s*have|qualifications?)[:\s]*(.*?)(?:nice\s*to\s*have|preferred|bonus|$)', jd_lower, re.DOTALL | re.IGNORECASE)
    if req_match:
        required_section = req_match.group(1)
    
    # Look for "nice to have" section
    nth_match = re.search(r'(?:nice\s*to\s*have|preferred|bonus|plus)[:\s]*(.*?)$', jd_lower, re.DOTALL | re.IGNORECASE)
    if nth_match:
        nice_to_have_section = nth_match.group(1)
    
    # Extract keywords from each section
    all_keywords = analysis.get_all_keywords()
    for kw in all_keywords:
        kw_lower = kw.lower()
        if kw_lower in nice_to_have_section:
            analysis.nice_to_have_skills.append(kw)
        elif kw_lower in required_section or kw_lower in jd_lower:
            analysis.required_skills.append(kw)
    
    # Detect remote policy
    if re.search(r'\b(remote|work\s*from\s*home|wfh|hybrid|on[\s-]?site|in[\s-]?office)\b', jd_lower):
        if "remote" in jd_lower:
            analysis.remote_policy = "remote" if "fully remote" in jd_lower else "hybrid"
        elif "on-site" in jd_lower or "in-office" in jd_lower:
            analysis.remote_policy = "on-site"
    
    return analysis


def analyze_jd_with_ai(job_description: str, provider: Optional[str] = None) -> JDAnalysis:
    """
    AI-powered JD analysis for more accurate extraction.
    Falls back to fast analysis if AI fails.
    """
    resolved_provider = (provider or ai_provider or "ollama").lower()
    
    prompt = f"""Analyze this job description and extract structured information.

JOB DESCRIPTION:
{job_description}

Return a JSON object with these exact fields:
{{
    "required_skills": ["list of must-have skills"],
    "nice_to_have_skills": ["list of nice-to-have/bonus skills"],
    "programming_languages": ["Python", "Java", etc.],
    "frameworks": ["Spring Boot", "React", etc.],
    "databases": ["PostgreSQL", "MongoDB", etc.],
    "cloud_platforms": ["AWS", "Azure", etc.],
    "devops_tools": ["Docker", "Kubernetes", etc.],
    "methodologies": ["Agile", "Scrum", etc.],
    "soft_skills": ["mentoring", "collaboration", etc.],
    "experience_years_min": 3,
    "experience_years_max": 5,
    "seniority_level": "senior"
}}

Output ONLY the JSON, no other text."""

    try:
        if resolved_provider == "ollama":
            from modules.ai import ollama_integration as _oll
            result = str(_oll.generate(prompt, timeout=120, stream=False))
            # Extract JSON from response
            json_match = re.search(r'\{[^{}]*\}', result, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                analysis = JDAnalysis(
                    required_skills=data.get("required_skills", []),
                    nice_to_have_skills=data.get("nice_to_have_skills", []),
                    programming_languages=data.get("programming_languages", []),
                    frameworks=data.get("frameworks", []),
                    databases=data.get("databases", []),
                    cloud_platforms=data.get("cloud_platforms", []),
                    devops_tools=data.get("devops_tools", []),
                    methodologies=data.get("methodologies", []),
                    soft_skills=data.get("soft_skills", []),
                    experience_years=(
                        data.get("experience_years_min", 0),
                        data.get("experience_years_max", 0)
                    ),
                    seniority_level=data.get("seniority_level", "mid"),
                )
                # Build priority lists
                analysis.high_priority_keywords = (
                    analysis.programming_languages + 
                    analysis.frameworks + 
                    analysis.databases +
                    analysis.cloud_platforms +
                    analysis.devops_tools
                )
                analysis.medium_priority_keywords = (
                    analysis.methodologies + 
                    analysis.soft_skills
                )
                return analysis
    except Exception as e:
        print(f"AI analysis failed, using fast analysis: {e}")
    
    # Fallback to regex-based analysis
    return analyze_jd_fast(job_description)


def get_keyword_priority_score(keyword: str, analysis: JDAnalysis) -> int:
    """
    Get priority score for a keyword (higher = more important for ATS).
    
    Returns:
        3 = high priority (required skill)
        2 = medium priority (nice-to-have or technical)
        1 = low priority (soft skill or general)
    """
    kw_lower = keyword.lower()
    
    # Required skills get highest priority
    if any(kw_lower == s.lower() for s in analysis.required_skills):
        return 3
    
    # High priority technical keywords
    if any(kw_lower == s.lower() for s in analysis.high_priority_keywords):
        return 3
    
    # Nice-to-have and medium priority
    if any(kw_lower == s.lower() for s in analysis.nice_to_have_skills):
        return 2
    if any(kw_lower == s.lower() for s in analysis.medium_priority_keywords):
        return 2
    
    return 1


def calculate_resume_match_score(resume_text: str, analysis: JDAnalysis) -> dict:
    """
    Calculate how well a resume matches the JD analysis.
    
    Returns detailed scoring breakdown.
    """
    resume_lower = resume_text.lower()
    
    all_keywords = analysis.get_all_keywords()
    matched = []
    missing = []
    
    for kw in all_keywords:
        if kw.lower() in resume_lower:
            matched.append(kw)
        else:
            missing.append(kw)
    
    # Calculate weighted score
    total_weight = 0
    matched_weight = 0
    
    for kw in all_keywords:
        priority = get_keyword_priority_score(kw, analysis)
        total_weight += priority
        if kw.lower() in resume_lower:
            matched_weight += priority
    
    weighted_score = (matched_weight / total_weight * 100) if total_weight > 0 else 0
    simple_score = (len(matched) / len(all_keywords) * 100) if all_keywords else 0
    
    # Categorize missing keywords by priority
    missing_high = [kw for kw in missing if get_keyword_priority_score(kw, analysis) == 3]
    missing_medium = [kw for kw in missing if get_keyword_priority_score(kw, analysis) == 2]
    missing_low = [kw for kw in missing if get_keyword_priority_score(kw, analysis) == 1]
    
    return {
        "simple_score": round(simple_score, 1),
        "weighted_score": round(weighted_score, 1),
        "total_keywords": len(all_keywords),
        "matched_count": len(matched),
        "matched_keywords": matched,
        "missing_count": len(missing),
        "missing_high_priority": missing_high,
        "missing_medium_priority": missing_medium,
        "missing_low_priority": missing_low,
        "recommendation": _get_recommendation(weighted_score, missing_high),
    }


def _get_recommendation(score: float, missing_critical: list) -> str:
    """Generate improvement recommendation based on score."""
    if score >= 90:
        return "Excellent match! Resume is well-optimized for this role."
    elif score >= 75:
        return f"Good match. Consider adding: {', '.join(missing_critical[:3])}" if missing_critical else "Good match!"
    elif score >= 60:
        return f"Moderate match. Missing critical keywords: {', '.join(missing_critical[:5])}"
    else:
        return f"Low match. Significant gaps in: {', '.join(missing_critical[:5])}"


# Quick test
if __name__ == "__main__":
    test_jd = """
    Software Engineer at TechCorp
    
    Requirements:
    - 3+ years experience with Python, JavaScript, TypeScript
    - Experience with React, Node.js, REST APIs, RESTful services
    - Database experience: PostgreSQL, MongoDB, Redis, DynamoDB
    - Cloud platforms: AWS, Azure, GCP
    - DevOps: Docker, Kubernetes, CI/CD, Jenkins
    - Agile/Scrum methodology
    - Experience with microservices architecture
    
    Nice to have:
    - Kotlin, Go, Rust experience is a plus
    - Strong mentoring and leadership skills
    - SaaS, PaaS, IaaS knowledge
    """
    
    print("=" * 60)
    print("JD ANALYSIS (Fast Mode)")
    print("=" * 60)
    analysis = analyze_jd_fast(test_jd)
    print(f"Programming Languages: {analysis.programming_languages}")
    print(f"Frameworks: {analysis.frameworks}")
    print(f"Databases: {analysis.databases}")
    print(f"Cloud: {analysis.cloud_platforms}")
    print(f"DevOps: {analysis.devops_tools}")
    print(f"Methodologies: {analysis.methodologies}")
    print(f"Soft Skills: {analysis.soft_skills}")
    print(f"Experience: {analysis.experience_years[0]}-{analysis.experience_years[1]} years")
    print(f"Seniority: {analysis.seniority_level}")
    print(f"\nHigh Priority Keywords: {analysis.high_priority_keywords}")
    print(f"Required Skills: {analysis.required_skills}")
    print(f"Nice-to-Have: {analysis.nice_to_have_skills}")
