/**
 * Resume Scoring & Analysis Engine
 * Ported from Python's resume_tailoring.py _score_match() and _extract_jd_keywords()
 *
 * Provides real ATS scoring, keyword extraction, and skill matching
 * entirely client-side for instant results without server dependency.
 */

/* eslint-env browser */
/* global chrome */

// ============================================================================
// Skill Synonym Mapping (from Python SKILL_SYNONYMS)
// ============================================================================
const SKILL_SYNONYMS = {
  // Programming languages
  'python': ['python3', 'py', 'cpython'],
  'javascript': ['js', 'ecmascript', 'es6', 'es2015+'],
  'typescript': ['ts'],
  'c++': ['cpp', 'c plus plus', 'cplusplus'],
  'c#': ['csharp', 'c sharp', 'dotnet'],
  'golang': ['go language', 'go-lang'],
  'ruby': ['ruby on rails', 'ror'],
  'scala': ['scala-lang'],
  'kotlin': ['kt'],
  'swift': ['swiftui'],
  'php': ['php7', 'php8', 'laravel'],

  // Frameworks & libraries
  'react': ['react.js', 'reactjs', 'react native'],
  'angular': ['angular.js', 'angularjs'],
  'vue': ['vue.js', 'vuejs'],
  'node.js': ['nodejs', 'node'],
  'next.js': ['nextjs', 'next'],
  'express': ['express.js', 'expressjs'],
  'django': ['djangorestframework', 'drf'],
  'flask': ['flask-restful'],
  'spring': ['spring boot', 'spring framework', 'springboot'],
  'fastapi': ['fast-api'],

  // Databases
  'sql': ['mysql', 'postgresql', 'postgres', 'mssql', 'sql server', 'sqlite', 'tsql', 'pl/sql'],
  'nosql': ['no-sql', 'non-relational'],
  'mongodb': ['mongo', 'mongoose'],
  'redis': ['redis cache'],
  'elasticsearch': ['elastic search', 'elastic', 'opensearch'],

  // Cloud & DevOps
  'aws': ['amazon web services', 'ec2', 's3', 'lambda', 'cloudfront'],
  'azure': ['microsoft azure', 'az', 'azure devops'],
  'gcp': ['google cloud', 'google cloud platform'],
  'docker': ['containerization', 'containers', 'dockerfile'],
  'kubernetes': ['k8s', 'kube', 'kubectl'],
  'terraform': ['iac', 'infrastructure as code', 'hashicorp'],
  'jenkins': ['ci server', 'jenkins pipeline'],
  'ci/cd': ['continuous integration', 'continuous deployment', 'cicd', 'ci cd'],
  'git': ['github', 'gitlab', 'bitbucket', 'version control'],

  // AI/ML
  'machine learning': ['ml', 'deep learning', 'dl', 'neural networks'],
  'ai': ['artificial intelligence'],
  'natural language processing': ['nlp'],
  'computer vision': ['cv', 'image recognition'],
  'tensorflow': ['tf'],
  'pytorch': ['torch'],

  // Data
  'data science': ['data analysis', 'data analytics'],
  'big data': ['data engineering', 'data pipeline'],
  'apache spark': ['spark', 'pyspark'],
  'hadoop': ['hdfs', 'mapreduce'],
  'tableau': ['data visualization'],
  'power bi': ['powerbi', 'power-bi'],

  // Messaging
  'kafka': ['apache kafka'],
  'rabbitmq': ['rabbit mq', 'amqp'],

  // Methodologies
  'agile': ['scrum', 'kanban', 'sprint', 'agile methodology'],
  'microservices': ['micro-services', 'microservice architecture'],
  'rest': ['restful', 'rest api', 'restful api'],
  'graphql': ['graph ql'],
  'api': ['apis', 'web service', 'web services', 'endpoint'],

  // Soft skills
  'leadership': ['lead', 'leading', 'led teams', 'team lead'],
  'communication': ['communicate', 'communicating'],
  'teamwork': ['team player', 'collaboration', 'collaborative'],
  'problem solving': ['problem-solving', 'troubleshooting'],
  'project management': ['pm', 'project manager', 'pmp'],
};


// ============================================================================
// Technical Keyword Bank
// ============================================================================
const TECH_KEYWORDS = new Set([
  'python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue',
  'node.js', 'nodejs', 'sql', 'nosql', 'mongodb', 'postgresql', 'mysql',
  'redis', 'elasticsearch', 'aws', 'azure', 'gcp', 'docker', 'kubernetes',
  'jenkins', 'ci/cd', 'terraform', 'api', 'rest', 'graphql', 'microservices',
  'agile', 'scrum', 'git', 'linux', 'machine learning', 'ml', 'ai',
  'data science', 'html', 'css', 'spring', 'django', 'flask', 'c++', 'c#',
  'golang', 'rust', 'scala', 'kotlin', 'swift', 'ruby', 'php', '.net',
  'kafka', 'rabbitmq', 'spark', 'hadoop', 'tableau', 'power bi',
  'spring boot', 'express', 'fastapi', 'next.js', 'webpack', 'sass',
  'pandas', 'numpy', 'scikit-learn', 'tensorflow', 'pytorch', 'keras',
  'selenium', 'cypress', 'jest', 'mocha', 'pytest', 'junit',
  'oauth', 'jwt', 'saml', 'ldap', 'ssl', 'tls', 'https',
  'nginx', 'apache', 'tomcat', 'iis',
  'bash', 'powershell', 'shell scripting',
  'jira', 'confluence', 'slack', 'trello',
]);

const SOFT_KEYWORDS = new Set([
  'leadership', 'communication', 'teamwork', 'collaboration',
  'problem solving', 'analytical', 'critical thinking',
  'time management', 'project management', 'stakeholder',
  'mentoring', 'cross functional', 'presentation', 'negotiation',
  'adaptability', 'creativity', 'initiative', 'self-motivated',
  'attention to detail', 'deadline-driven', 'prioritization',
]);


// ============================================================================
// Core Functions
// ============================================================================

/**
 * Normalize text for keyword matching.
 * @param {string} text
 * @returns {string}
 */
function normalizeText(text) {
  if (!text) return '';
  return text.toLowerCase()
    .replace(/[\-\/\.]+/g, ' ')
    .replace(/[^a-z0-9\s\+\#]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}


/**
 * Extract keywords from job description text.
 * Returns categorized technical and soft skill keywords.
 *
 * @param {string} jdText - Job description text
 * @returns {{ technical: string[], soft: string[], all: string[] }}
 */
function extractJDKeywords(jdText) {
  const normalized = normalizeText(jdText);
  const techFound = [];
  const softFound = [];

  // Check technical keywords
  for (const kw of TECH_KEYWORDS) {
    const normKw = normalizeText(kw);
    if (normalized.includes(normKw)) {
      techFound.push(kw);
      continue;
    }
    // Check synonyms
    if (SKILL_SYNONYMS[kw]) {
      for (const syn of SKILL_SYNONYMS[kw]) {
        if (normalized.includes(normalizeText(syn))) {
          techFound.push(kw);
          break;
        }
      }
    }
  }

  // Check soft skills
  for (const kw of SOFT_KEYWORDS) {
    const normKw = normalizeText(kw);
    if (normalized.includes(normKw)) {
      softFound.push(kw);
      continue;
    }
    if (SKILL_SYNONYMS[kw]) {
      for (const syn of SKILL_SYNONYMS[kw]) {
        if (normalized.includes(normalizeText(syn))) {
          softFound.push(kw);
          break;
        }
      }
    }
  }

  return {
    technical: [...new Set(techFound)].sort(),
    soft: [...new Set(softFound)].sort(),
    all: [...new Set([...techFound, ...softFound])].sort(),
  };
}


/**
 * Score how well a resume matches a job description.
 * Port of Python's _score_match() with synonym expansion.
 *
 * @param {string} resumeText - Resume content
 * @param {string} jdText - Job description content
 * @returns {{ match: number, ats: number, matched: number, total: number,
 *             techFound: string[], techMissing: string[],
 *             softFound: string[], softMissing: string[],
 *             found: string[], missing: string[] }}
 */
function scoreMatch(resumeText, jdText) {
  const jdKeywords = extractJDKeywords(jdText);
  const resumeNormalized = normalizeText(resumeText);

  const found = [];
  const missing = [];
  const techFound = [];
  const techMissing = [];
  const softFound = [];
  const softMissing = [];

  /**
   * Check if a keyword (or any of its synonyms) exists in the resume.
   */
  function keywordInResume(kw) {
    const normKw = normalizeText(kw);
    if (resumeNormalized.includes(normKw)) return true;

    // Check synonyms
    const syns = SKILL_SYNONYMS[kw];
    if (syns) {
      for (const syn of syns) {
        if (resumeNormalized.includes(normalizeText(syn))) return true;
      }
    }

    // Reverse lookup: check if kw appears as a synonym value
    for (const [canonical, synList] of Object.entries(SKILL_SYNONYMS)) {
      if (synList.includes(kw) && resumeNormalized.includes(normalizeText(canonical))) {
        return true;
      }
    }

    return false;
  }

  // Score technical keywords
  for (const kw of jdKeywords.technical) {
    if (keywordInResume(kw)) {
      found.push(kw);
      techFound.push(kw);
    } else {
      missing.push(kw);
      techMissing.push(kw);
    }
  }

  // Score soft skills
  for (const kw of jdKeywords.soft) {
    if (keywordInResume(kw)) {
      found.push(kw);
      softFound.push(kw);
    } else {
      missing.push(kw);
      softMissing.push(kw);
    }
  }

  const total = found.length + missing.length;
  const matched = found.length;

  // ATS score: keyword match percentage (weighted: tech 70%, soft 30%)
  const techTotal = techFound.length + techMissing.length;
  const softTotal = softFound.length + softMissing.length;

  const techScore = techTotal > 0 ? (techFound.length / techTotal) * 100 : 100;
  const softScore = softTotal > 0 ? (softFound.length / softTotal) * 100 : 100;

  // Weighted ATS score
  const ats = Math.round(
    techTotal > 0 || softTotal > 0
      ? (techScore * 0.7) + (softScore * 0.3)
      : 0
  );

  // Match score: overall keyword hit rate
  const match = total > 0 ? Math.round((matched / total) * 100) : 0;

  return {
    match,
    ats,
    matched,
    total,
    found,
    missing,
    techFound,
    techMissing,
    softFound,
    softMissing,
  };
}


/**
 * Generate an HTML diff/comparison report between original and tailored resume.
 *
 * @param {string} original - Original resume text
 * @param {string} tailored - Tailored resume text
 * @param {string[]} matchedKeywords - Keywords found in tailored resume
 * @param {string[]} missingKeywords - Keywords still missing
 * @returns {string} HTML string for the preview
 */
function generatePreviewHTML(original, tailored, matchedKeywords, missingKeywords) {
  const escHtml = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  // Highlight keywords in tailored text
  let highlightedTailored = escHtml(tailored);
  for (const kw of matchedKeywords) {
    const regex = new RegExp(`\\b(${kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})\\b`, 'gi');
    highlightedTailored = highlightedTailored.replace(
      regex,
      '<span class="keyword-match">$1</span>'
    );
  }

  return `
    <div class="preview-container">
      <div class="preview-panel original-panel">
        <h3>📄 Original Resume</h3>
        <div class="resume-content">${escHtml(original)}</div>
      </div>
      <div class="preview-panel tailored-panel">
        <h3>✨ Tailored Resume</h3>
        <div class="resume-content">${highlightedTailored}</div>
      </div>
    </div>
    <div class="keyword-analysis">
      <div class="kw-section kw-found">
        <h4>✅ Matched Keywords (${matchedKeywords.length})</h4>
        <div class="kw-tags">${matchedKeywords.map(k => `<span class="kw-tag found">${escHtml(k)}</span>`).join('')}</div>
      </div>
      <div class="kw-section kw-missing">
        <h4>⚠️ Missing Keywords (${missingKeywords.length})</h4>
        <div class="kw-tags">${missingKeywords.map(k => `<span class="kw-tag missing">${escHtml(k)}</span>`).join('')}</div>
      </div>
    </div>
  `;
}


/**
 * Calculate improvement metrics between before and after scores.
 *
 * @param {{ ats: number, match: number }} before
 * @param {{ ats: number, match: number }} after
 * @returns {{ atsImprovement: number, matchImprovement: number, summary: string }}
 */
function calculateImprovement(before, after) {
  const atsImprovement = after.ats - before.ats;
  const matchImprovement = after.match - before.match;

  let summary = '';
  if (atsImprovement > 15) {
    summary = '🚀 Excellent improvement! Resume is much better aligned with the JD.';
  } else if (atsImprovement > 5) {
    summary = '✅ Good improvement. Key skills are now better represented.';
  } else if (atsImprovement > 0) {
    summary = '📊 Minor improvement. Consider adding more specific keywords.';
  } else {
    summary = '📋 Resume was already well-matched. Minimal changes needed.';
  }

  return { atsImprovement, matchImprovement, summary };
}


// ============================================================================
// Export for use in popup.js
// ============================================================================
// Using window global since Chrome extensions don't support ES modules in popup
if (typeof window !== 'undefined') {
  window.ResumeEngine = {
    extractJDKeywords,
    scoreMatch,
    generatePreviewHTML,
    calculateImprovement,
    normalizeText,
    SKILL_SYNONYMS,
    TECH_KEYWORDS,
    SOFT_KEYWORDS,
  };
}
