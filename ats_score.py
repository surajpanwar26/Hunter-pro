# ATS Score Calculator
def calculate_ats_score(resume, job_description):
    '''Calculate ATS match score between resume and JD'''
    
    jd_lower = job_description.lower()
    resume_lower = resume.lower()
    
    # Key technical skills from the JD
    tech_keywords = [
        'backend', 'software engineer', 'scalable', 'microservices', 'restful',
        'java', 'kotlin', 'go', 'scala', 'python', 'postgresql', 'postgres',
        'nosql', 'dynamodb', 'cassandra', 'mongodb', 'aws', 'azure', 'gcp',
        'docker', 'kubernetes', 'ci/cd', 'agile', 'cloud', 'saas', 'paas', 'iaas',
        'distributed', 'api', 'rest', 'monitoring', 'testing', 'security',
        'performance', 'reliability', 'collaboration', 'mentor'
    ]
    
    # Check which keywords are in resume
    found = []
    missing = []
    for kw in tech_keywords:
        if kw in resume_lower:
            found.append(kw)
        elif kw in jd_lower:
            missing.append(kw)
    
    # Calculate score
    total_jd_keywords = len([k for k in tech_keywords if k in jd_lower])
    matched = len(found)
    score = (matched / total_jd_keywords * 100) if total_jd_keywords > 0 else 0
    
    return {
        'score': round(score, 1),
        'matched': matched,
        'total': total_jd_keywords,
        'found': found,
        'missing': missing[:10]
    }

# The JD
jd = '''Backend Software Engineer at Atlassian
4+ years of experience in building and developing backend applications
Experience in crafting highly scalable and performant RESTful microservices
Proficiency in Java, Kotlin, Go, Scala, or Python
Fluency in database technology (RDBMS like Postgres or NoSQL like DynamoDB or Cassandra)
Knowledge of SaaS, PaaS, and IaaS with hands-on experience with AWS, GAE, Azure
Familiarity with cloud architecture patterns
Agile software development
Mentoring teammates
Code review with testing, documentation, reliability, security, and performance
'''

# Original resume
original = '''SURAJ PANWAR
Software Engineer
Backend developer with 3+ years of experience building scalable APIs and microservices.
Built REST APIs using Python Flask serving 10K+ requests/day
Managed PostgreSQL databases with complex queries
Deployed microservices on AWS ECS with Docker containers
Collaborated with frontend teams in Agile sprints
Developed Java backend services for e-commerce platform
Implemented CI/CD pipelines using Jenkins
Wrote unit tests achieving 80% code coverage
Python, Java, Flask, Spring Boot, AWS, Docker, PostgreSQL, MongoDB, REST APIs, Git
'''

# Tailored resume (from our test)
tailored = '''SURAJ PANWAR
Software Engineer
Backend developer with 3+ years of experience building scalable APIs and microservices, with a passion for collaboration and expertise in cloud architecture patterns.
Built REST APIs using Python Flask serving 10K+ requests/day, leveraging scalability and performance best practices.
Managed PostgreSQL databases with complex queries, ensuring complete visibility and error reporting.
Deployed microservices on AWS ECS with Docker containers, aligning with cloud architecture patterns.
Developed Java backend services for e-commerce platform, applying best practices of readability, testing patterns, and documentation.
Implemented CI/CD pipelines using Jenkins, ensuring reliability and security.
Python, Java, Flask, Spring Boot, AWS, Docker, PostgreSQL, REST APIs, Git, Database Technology (RDBMS like Postgres or NoSQL like Cassandra)
'''

print('='*70)
print('ATS SCORE COMPARISON')
print('='*70)

orig_score = calculate_ats_score(original, jd)
tail_score = calculate_ats_score(tailored, jd)

print()
print('ORIGINAL RESUME:')
print(f'  ATS Score: {orig_score["score"]}%')
print(f'  Keywords Matched: {orig_score["matched"]}/{orig_score["total"]}')
print(f'  Found: {orig_score["found"]}')
print()
print('TAILORED RESUME:')
print(f'  ATS Score: {tail_score["score"]}%')
print(f'  Keywords Matched: {tail_score["matched"]}/{tail_score["total"]}')
print(f'  Found: {tail_score["found"]}')
print()
print('='*70)
print('IMPROVEMENT')
print('='*70)
improvement = tail_score['score'] - orig_score['score']
print(f'  Score Increase: +{improvement:.1f}%')
print(f'  New Keywords Added: {set(tail_score["found"]) - set(orig_score["found"])}')
print()
print('STILL MISSING (consider adding):')
print(f'  {tail_score["missing"]}')
