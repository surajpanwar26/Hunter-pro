"""
Groq API Connection Module for Resume Tailoring and AI Operations

This module provides a robust connection to Groq's fast LLM API for:
- Resume tailoring with high-quality output
- Form filling assistance
- Job description analysis

Author: Suraj Panwar
Version: 2.0.0
"""
from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from typing import Optional, Any
from dataclasses import dataclass

from modules.helpers import print_lg


@dataclass
class GroqResponse:
    """Structured response from Groq API."""
    content: str
    model: str
    usage: dict
    finish_reason: str
    latency_ms: float


class GroqConnection:
    """
    Production-grade Groq API client with retry logic and error handling.
    """
    
    DEFAULT_MODEL = "llama-3.3-70b-versatile"
    FAST_MODEL = "llama-3.1-8b-instant"
    
    # Groq API endpoint
    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    
    def __init__(self, api_key: str, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model or self.DEFAULT_MODEL
        self._request_count = 0
        self._total_tokens = 0
        
    def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        timeout: int = 60,
    ) -> GroqResponse:
        """
        Send a chat completion request to Groq API.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
            system_prompt: Optional system prompt to prepend
            json_mode: If True, request JSON response format
            timeout: Request timeout in seconds
            
        Returns:
            GroqResponse with generated content
        """
        # Build messages list
        all_messages = []
        if system_prompt:
            all_messages.append({"role": "system", "content": system_prompt})
        all_messages.extend(messages)
        
        # Build request payload
        payload = {
            "model": self.model,
            "messages": all_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        
        # Make request with retry
        start_time = time.time()
        response_data = self._make_request(payload, timeout)
        latency = (time.time() - start_time) * 1000
        
        # Parse response
        choice = response_data.get("choices", [{}])[0]
        message = choice.get("message", {})
        usage = response_data.get("usage", {})
        
        self._request_count += 1
        self._total_tokens += usage.get("total_tokens", 0)
        
        return GroqResponse(
            content=message.get("content", ""),
            model=response_data.get("model", self.model),
            usage=usage,
            finish_reason=choice.get("finish_reason", ""),
            latency_ms=latency,
        )
    
    def _make_request(self, payload: dict, timeout: int, max_retries: int = 3) -> dict:
        """Make HTTP request with retry logic."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        data = json.dumps(payload).encode("utf-8")
        
        last_error = None
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(
                    self.API_URL,
                    data=data,
                    headers=headers,
                    method="POST"
                )
                
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
                    
            except urllib.error.HTTPError as e:
                last_error = e
                error_body = e.read().decode("utf-8") if e.fp else ""
                
                # Handle rate limiting
                if e.code == 429:
                    retry_after = int(e.headers.get("Retry-After", 5))
                    print_lg(f"Groq rate limited, waiting {retry_after}s...")
                    time.sleep(retry_after)
                    continue
                
                # Handle server errors with retry
                if e.code >= 500:
                    wait_time = 2 ** attempt
                    print_lg(f"Groq server error {e.code}, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                # Client errors - don't retry
                raise ValueError(f"Groq API error {e.code}: {error_body}")
                
            except urllib.error.URLError as e:
                last_error = e
                wait_time = 2 ** attempt
                print_lg(f"Network error, retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
                
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                raise
        
        raise ValueError(f"Failed after {max_retries} attempts: {last_error}")
    
    def tailor_resume(
        self,
        resume_text: str,
        job_description: str,
        instructions: Optional[str] = None,
    ) -> str:
        """
        Tailor a resume for a specific job using Groq's LLM.
        
        Args:
            resume_text: Original resume content
            job_description: Target job description
            instructions: Optional additional instructions
            
        Returns:
            Tailored resume text
        """
        from modules.ai.prompts import resume_tailor_prompt
        
        # Build the prompt
        prompt = resume_tailor_prompt.format(
            resume_text=resume_text,
            job_description=job_description,
            instructions=instructions or "No additional instructions.",
        )
        
        messages = [{"role": "user", "content": prompt}]
        
        response = self.chat(
            messages=messages,
            temperature=0.3,  # Lower temperature for more consistent output
            max_tokens=4096,
        )
        
        return response.content
    
    def analyze_job_description(self, job_description: str) -> dict:
        """
        Analyze a job description to extract key requirements.
        
        Returns dict with: tech_stack, skills, requirements, nice_to_have
        """
        from modules.ai.prompts import extract_skills_prompt
        
        prompt = extract_skills_prompt.format(job_description)
        messages = [{"role": "user", "content": prompt}]
        
        response = self.chat(
            messages=messages,
            temperature=0.1,
            max_tokens=2048,
            json_mode=True,
        )
        
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return {
                "tech_stack": [],
                "technical_skills": [],
                "other_skills": [],
                "required_skills": [],
                "nice_to_have": [],
            }
    
    def answer_question(
        self,
        question: str,
        user_info: str,
        context: Optional[str] = None,
    ) -> str:
        """
        Generate an answer for a form question.
        
        Args:
            question: The form question
            user_info: User's profile information
            context: Optional additional context
            
        Returns:
            Generated answer
        """
        from modules.ai.prompts import ai_answer_prompt
        
        prompt = ai_answer_prompt.format(user_info, question)
        if context:
            prompt += f"\n\nAdditional Context:\n{context}"
        
        messages = [{"role": "user", "content": prompt}]
        
        response = self.chat(
            messages=messages,
            temperature=0.5,
            max_tokens=500,
        )
        
        return response.content.strip()
    
    @property
    def stats(self) -> dict:
        """Get usage statistics."""
        return {
            "requests": self._request_count,
            "total_tokens": self._total_tokens,
            "model": self.model,
        }


# Singleton instance
_groq_client: Optional[GroqConnection] = None


def get_groq_client() -> Optional[GroqConnection]:
    """Get or create the Groq client singleton."""
    global _groq_client
    
    if _groq_client is None:
        try:
            from config.secrets import groq_api_key, groq_model
            
            if groq_api_key and groq_api_key != "your_groq_api_key_here":
                _groq_client = GroqConnection(groq_api_key, groq_model)
                print_lg(f"✅ Groq client initialized with model: {groq_model}")
            else:
                print_lg("⚠️ Groq API key not configured")
                
        except ImportError:
            print_lg("⚠️ Groq configuration not found in secrets")
        except Exception as e:
            print_lg(f"⚠️ Failed to initialize Groq client: {e}")
    
    return _groq_client


def tailor_resume_with_groq(
    resume_text: str,
    job_description: str,
    instructions: Optional[str] = None,
) -> str:
    """
    Convenience function to tailor a resume using Groq.
    Falls back to error message if client not available.
    """
    client = get_groq_client()
    if not client:
        return "[Error: Groq API not configured. Please add your API key to config/secrets.py]"
    
    try:
        return client.tailor_resume(resume_text, job_description, instructions)
    except Exception as e:
        return f"[Error tailoring resume: {str(e)}]"


def analyze_jd_with_groq(job_description: str) -> dict:
    """
    Convenience function to analyze a job description using Groq.
    """
    client = get_groq_client()
    if not client:
        return {}
    
    try:
        return client.analyze_job_description(job_description)
    except Exception as e:
        print_lg(f"JD analysis error: {e}")
        return {}


# ========== Backward Compatibility Functions ==========
# These functions provide the interface expected by runAiBot.py

def groq_create_client():
    """Create and return the Groq client (backward compatibility)."""
    return get_groq_client()


def groq_extract_skills(client, job_description: str) -> list:
    """
    Extract skills from a job description using Groq.
    
    Args:
        client: Groq client instance
        job_description: The job description text
        
    Returns:
        List of extracted skills
    """
    if not client:
        return []
    
    try:
        analysis = client.analyze_job_description(job_description)
        return analysis.get('required_skills', []) + analysis.get('preferred_skills', [])
    except Exception as e:
        print_lg(f"Error extracting skills: {e}")
        return []


def groq_answer_question(client, question: str, user_info: str, context: str = "") -> str:
    """
    Answer a form question using Groq.
    
    Args:
        client: Groq client instance
        question: The question to answer
        user_info: User's information for context
        context: Additional context
        
    Returns:
        Generated answer string
    """
    if not client:
        return ""
    
    try:
        return client.answer_question(question, user_info, context)
    except Exception as e:
        print_lg(f"Error answering question: {e}")
        return ""


def groq_tailor_resume(client, resume_text: str, job_description: str, instructions: str = "") -> str:
    """
    Tailor a resume for a job using Groq.
    
    Args:
        client: Groq client instance
        resume_text: Original resume text
        job_description: Target job description
        instructions: Optional custom instructions
        
    Returns:
        Tailored resume text
    """
    if not client:
        return resume_text
    
    try:
        return client.tailor_resume(resume_text, job_description, instructions)
    except Exception as e:
        print_lg(f"Error tailoring resume: {e}")
        return resume_text
