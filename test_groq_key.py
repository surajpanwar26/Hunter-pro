"""
Test Groq API Key and Resume Tailoring Performance
"""
import time
from openai import OpenAI

# Test API key
groq_api_key = "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"
groq_api_url = "https://api.groq.com/openai/v1"
# Updated to current model (llama-3.1-70b-versatile was decommissioned)
groq_model = "llama-3.3-70b-versatile"  # Current best model

def test_api_key():
    """Test if the Groq API key is valid"""
    print("🔑 Testing Groq API Key...")
    try:
        client = OpenAI(api_key=groq_api_key, base_url=groq_api_url)
        
        # Test with a simple completion
        response = client.chat.completions.create(
            model=groq_model,
            messages=[{"role": "user", "content": "Say 'API key is valid' if you can read this."}],
            max_tokens=20
        )
        
        print("✅ API Key is VALID!")
        print(f"   Response: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"❌ API Key is INVALID or there's an error:")
        print(f"   Error: {str(e)}")
        return False

def test_resume_tailoring_speed():
    """Test resume tailoring speed with sample job description"""
    print("\n⏱️  Testing Resume Tailoring Speed...")
    
    sample_jd = """
    Senior Software Engineer
    
    We are looking for an experienced Software Engineer with:
    - 5+ years of Python development experience
    - Strong experience with Django, Flask, or FastAPI
    - Experience with AWS, Docker, and Kubernetes
    - Experience with CI/CD pipelines
    - Strong problem-solving skills
    - Excellent communication skills
    
    Responsibilities:
    - Design and develop scalable backend services
    - Collaborate with cross-functional teams
    - Mentor junior developers
    - Write clean, maintainable code
    """
    
    sample_resume = """
    John Doe
    Software Engineer
    
    Experience:
    - 6 years of software development
    - Proficient in Python, JavaScript, Java
    - Built REST APIs using Flask
    - Deployed applications on cloud platforms
    - Worked in agile teams
    
    Skills: Python, JavaScript, SQL, Git, Linux
    """
    
    prompt = f"""You are a professional resume writer. Tailor this resume to match the job description.
Keep it concise and highlight relevant skills.

Job Description:
{sample_jd}

Current Resume:
{sample_resume}

Provide a tailored version that emphasizes relevant experience and keywords from the JD."""
    
    try:
        client = OpenAI(api_key=groq_api_key, base_url=groq_api_url)
        
        print(f"   Model: {groq_model}")
        start_time = time.time()
        
        response = client.chat.completions.create(
            model=groq_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.3
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"✅ Resume Tailoring Completed!")
        print(f"   Time taken: {duration:.2f} seconds")
        print(f"   Tokens used: {response.usage.total_tokens}")
        print(f"   Speed: ~{response.usage.total_tokens / duration:.0f} tokens/second")
        
        print(f"\n📝 Sample Output (first 300 chars):")
        output = response.choices[0].message.content
        print(f"   {output[:300]}...")
        
        return duration
        
    except Exception as e:
        print(f"❌ Error during resume tailoring test:")
        print(f"   Error: {str(e)}")
        return None

def check_rate_limits():
    """Display Groq free tier rate limits"""
    print("\n📊 Groq Free Tier Rate Limits:")
    print("   Model: llama-3.3-70b-versatile (Current)")
    print("   Requests per minute: 30")
    print("   Requests per day: 14,400")
    print("   Tokens per minute: 6,000")
    print("   Tokens per request: ~1,000-2,000 for resume tailoring")
    print("\n   Estimated resumes per hour: ~600-1000")
    print("   (Limited by rate limit, not speed)")
    print("\n   ⚠️  Note: llama-3.1-70b-versatile was decommissioned")
    print("   ✅  Now using: llama-3.3-70b-versatile (Latest)")

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 GROQ API KEY & PERFORMANCE TEST")
    print("=" * 60)
    
    # Test 1: API Key Validity
    is_valid = test_api_key()
    
    if is_valid:
        # Test 2: Resume Tailoring Speed
        duration = test_resume_tailoring_speed()
        
        # Test 3: Rate Limits Info
        check_rate_limits()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS COMPLETED!")
        if duration:
            print(f"⚡ Average time per resume: {duration:.2f} seconds")
            print(f"📈 Estimated capacity: ~{3600/duration:.0f} resumes/hour")
        print("=" * 60)
    else:
        print("\n⚠️  Cannot proceed with performance tests - Invalid API key")
        print("=" * 60)
