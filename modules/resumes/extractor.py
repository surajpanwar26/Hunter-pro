'''
Author:     Suraj Panwar
LinkedIn:   https://www.linkedin.com/in/surajpanwar/

Copyright (C) 2024-2026 Suraj Panwar

License:    GNU Affero General Public License
            https://www.gnu.org/licenses/agpl-3.0.en.html
            
GitHub:     https://github.com/surajpanwar/Auto_job_applier_linkedIn

Modified by: Suraj Panwar

Resume Extractor Module - Extracts text and information from resume files
'''

import os
import re

try:
    from config.personals import *
    from config.questions import default_resume_path
except ImportError:
    default_resume_path = "all resumes/default/resume.pdf"


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extracts text content from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text as string
    """
    try:
        import PyPDF2
        
        text = ""
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text.strip()
    except ImportError:
        print("PyPDF2 not installed. Install with: pip install PyPDF2")
        return ""
    except Exception as e:
        print(f"Error extracting PDF: {e}")
        return ""


def extract_text_from_docx(docx_path: str) -> str:
    """
    Extracts text content from a DOCX file.
    
    Args:
        docx_path: Path to the DOCX file
        
    Returns:
        Extracted text as string
    """
    try:
        import docx
        
        doc = docx.Document(docx_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text.strip()
    except ImportError:
        print("python-docx not installed. Install with: pip install python-docx")
        return ""
    except Exception as e:
        print(f"Error extracting DOCX: {e}")
        return ""


def extract_resume_text(resume_path: str = None) -> str:
    """
    Extracts text from a resume file (PDF or DOCX).
    
    Args:
        resume_path: Path to the resume file. Uses default if not provided.
        
    Returns:
        Extracted text as string
    """
    if resume_path is None:
        resume_path = default_resume_path
    
    if not os.path.exists(resume_path):
        print(f"Resume file not found: {resume_path}")
        return ""
    
    ext = os.path.splitext(resume_path)[1].lower()
    
    if ext == '.pdf':
        return extract_text_from_pdf(resume_path)
    elif ext in ['.docx', '.doc']:
        return extract_text_from_docx(resume_path)
    else:
        print(f"Unsupported file format: {ext}")
        return ""


def extract_email(text: str) -> str:
    """Extracts email address from text."""
    pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
    match = re.search(pattern, text)
    return match.group(0) if match else ""


def extract_phone(text: str) -> str:
    """Extracts phone number from text."""
    patterns = [
        r'\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
        r'\d{10}',
        r'\d{3}[-.\s]\d{3}[-.\s]\d{4}'
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return ""


def extract_skills_from_text(text: str) -> list:
    """
    Extracts potential skills from resume text.
    This is a basic extraction - AI-based extraction is more accurate.
    
    Args:
        text: Resume text content
        
    Returns:
        List of potential skills
    """
    # Common tech skills to look for
    common_skills = [
        'Python', 'JavaScript', 'Java', 'C++', 'C#', 'Ruby', 'Go', 'Rust', 'Swift', 'Kotlin',
        'React', 'Angular', 'Vue', 'Node.js', 'Django', 'Flask', 'Spring', 'Express',
        'SQL', 'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Elasticsearch',
        'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'Jenkins', 'Git',
        'Machine Learning', 'Deep Learning', 'TensorFlow', 'PyTorch', 'NLP',
        'REST', 'GraphQL', 'Microservices', 'Agile', 'Scrum', 'CI/CD',
        'Linux', 'Windows', 'MacOS', 'Shell', 'Bash',
        'HTML', 'CSS', 'TypeScript', 'SASS', 'Bootstrap', 'Tailwind',
        'Pandas', 'NumPy', 'Scikit-learn', 'Spark', 'Hadoop'
    ]
    
    found_skills = []
    text_lower = text.lower()
    
    for skill in common_skills:
        if skill.lower() in text_lower:
            found_skills.append(skill)
    
    return found_skills


def parse_resume(resume_path: str = None) -> dict:
    """
    Parses a resume and extracts structured information.
    
    Args:
        resume_path: Path to the resume file
        
    Returns:
        Dictionary with extracted information
    """
    text = extract_resume_text(resume_path)
    
    if not text:
        return {}
    
    return {
        'raw_text': text,
        'email': extract_email(text),
        'phone': extract_phone(text),
        'skills': extract_skills_from_text(text)
    }




