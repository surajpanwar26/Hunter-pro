"""
Test script for Enhanced Resume Tailor features
Run this to verify all new features are working correctly.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import tkinter as tk
import ttkbootstrap as ttkb
from modules.dashboard.enhanced_resume_tailor import open_enhanced_resume_tailor_dialog

# Test data
TEST_RESUME = """JOHN DOE
Software Engineer

Backend developer with 3+ years of experience building scalable APIs and microservices.

EXPERIENCE
- Built REST APIs using Python Flask serving 10K+ requests/day
- Managed PostgreSQL databases with complex queries
- Deployed microservices on AWS ECS with Docker containers
- Collaborated with frontend teams in Agile sprints
- Developed Java backend services for e-commerce platform
- Implemented CI/CD pipelines using Jenkins
- Wrote unit tests achieving 80% code coverage

SKILLS
Python, Java, Flask, Spring Boot, AWS, Docker, PostgreSQL, MongoDB, REST APIs, Git
"""

TEST_JD = """Senior Backend Engineer at TechCorp

We're looking for an experienced Backend Engineer to join our growing team.

REQUIREMENTS:
- 4+ years of experience in building and developing backend applications
- Experience in crafting highly scalable and performant RESTful microservices
- Proficiency in Java, Kotlin, Go, Scala, or Python
- Fluency in database technology (RDBMS like Postgres or NoSQL like DynamoDB or Cassandra)
- Knowledge of SaaS, PaaS, and IaaS with hands-on experience with AWS, GAE, Azure
- Familiarity with cloud architecture patterns
- Experience with Kubernetes and container orchestration
- Strong testing practices and code review skills

RESPONSIBILITIES:
- Design and implement scalable microservices
- Collaborate with cross-functional teams in Agile environment
- Mentor junior developers
- Ensure code quality through testing, documentation, reliability, and security
- Monitor and optimize application performance
"""

def test_enhanced_features():
    """Test the enhanced resume tailor features."""
    print("=" * 70)
    print("ENHANCED RESUME TAILOR - FEATURE TEST")
    print("=" * 70)
    print()
    print("Testing new features:")
    print("✓ Diff highlighting (green additions, red removals)")
    print("✓ Skill suggestions with one-click add")
    print("✓ Before/After ATS score display")
    print("✓ Visual change tracker")
    print()
    print("Opening enhanced dialog with test data...")
    print()
    
    # Create root window
    root = ttkb.Window(themename="darkly")
    root.withdraw()  # Hide the root window
    
    # Open enhanced dialog with test data
    try:
        open_enhanced_resume_tailor_dialog(root, "ollama", TEST_RESUME)
        print("✅ Enhanced dialog opened successfully!")
        print()
        print("What to test:")
        print("1. Paste the test JD (or use your own)")
        print("2. Click 'Quick ATS Check' to see skill suggestions")
        print("3. Try adding a skill using the '+ Add' button")
        print("4. Click 'Start Tailoring' to see the full process")
        print("5. Check the 'Changes Highlighted' tab for color-coded diff")
        print("6. Verify Before/After ATS scores at the top")
        print()
    except Exception as e:
        print(f"❌ Error opening dialog: {e}")
        import traceback
        traceback.print_exc()
    
    root.mainloop()

if __name__ == "__main__":
    # Print test JD for easy copying
    print("\n" + "=" * 70)
    print("TEST JOB DESCRIPTION (copy this to paste in the dialog):")
    print("=" * 70)
    print(TEST_JD)
    print("=" * 70)
    print()
    
    input("Press Enter to open the Enhanced Resume Tailor dialog...")
    test_enhanced_features()
