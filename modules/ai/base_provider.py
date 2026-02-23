"""
Unified AI Provider Interface
=============================
Abstract base class that all AI providers must implement, plus a factory
function that returns the correct provider based on ``config.secrets.ai_provider``.

Usage
-----
    from modules.ai.base_provider import get_ai_provider

    provider = get_ai_provider()          # reads ai_provider from config
    client   = provider.create_client()
    skills   = provider.extract_skills(client, jd_text)
    answer   = provider.answer_question(client, "What is your notice period?",
                                         user_information_all=user_info)
"""

from __future__ import annotations

import abc
from typing import Any, Literal, Optional

from modules.helpers import print_lg


class AIProvider(abc.ABC):
    """Common contract every AI provider MUST satisfy."""

    name: str = "base"

    # ------------------------------------------------------------------
    # Client lifecycle
    # ------------------------------------------------------------------
    @abc.abstractmethod
    def create_client(self) -> Any:
        """Create and return a provider-specific client object.

        Returns ``None`` when the provider cannot be initialised (missing key, etc.).
        """

    def close_client(self, client: Any) -> None:       # noqa: B027
        """Optional cleanup hook — providers override if needed."""

    # ------------------------------------------------------------------
    # Core capabilities
    # ------------------------------------------------------------------
    @abc.abstractmethod
    def extract_skills(self, client: Any, job_description: str, **kwargs) -> dict | list | None:
        """Extract structured skills from a job description.

        Should return a dict/list on success, ``None`` on failure.
        """

    @abc.abstractmethod
    def answer_question(
        self,
        client: Any,
        question: str,
        *,
        options: list[str] | None = None,
        question_type: Literal["text", "textarea", "single_select", "multiple_select"] = "text",
        job_description: str | None = None,
        about_company: str | None = None,
        user_information_all: str | None = None,
        **kwargs,
    ) -> str:
        """Generate an answer for a form question.

        MUST return a **string** (empty on failure) so callers can safely
        use the result in form field filling without type checks.
        """

    # ------------------------------------------------------------------
    # Optional — resume tailoring
    # ------------------------------------------------------------------
    def tailor_resume(
        self,
        client: Any,
        resume_text: str,
        job_description: str,
        instructions: str = "",
    ) -> str:
        """Tailor a resume for a specific job.  Defaults to returning the
        original text — providers override to add real functionality."""
        return resume_text

    # ------------------------------------------------------------------
    # Helpers (shared)
    # ------------------------------------------------------------------
    def _emit_event(self, event: str, data: dict | None = None) -> None:
        try:
            from modules.dashboard import log_handler
            log_handler.publish_event(event=event, data=data or {}, source=self.name)
        except Exception:
            pass

    def __repr__(self) -> str:
        return f"<AIProvider:{self.name}>"


# ======================================================================
# Concrete adapters — thin wrappers around existing provider modules
# ======================================================================

class OpenAIProvider(AIProvider):
    name = "openai"

    def create_client(self) -> Any:
        from modules.ai.openaiConnections import ai_create_openai_client
        return ai_create_openai_client()

    def close_client(self, client: Any) -> None:
        from modules.ai.openaiConnections import ai_close_openai_client
        ai_close_openai_client(client)

    def extract_skills(self, client: Any, job_description: str, **kwargs) -> dict | list | None:
        from modules.ai.openaiConnections import ai_extract_skills
        return ai_extract_skills(client, job_description)

    def answer_question(self, client, question, *, options=None, question_type="text",
                        job_description=None, about_company=None,
                        user_information_all=None, **kw) -> str:
        from modules.ai.openaiConnections import ai_answer_question
        result = ai_answer_question(
            client, question, options=options, question_type=question_type,
            job_description=job_description, about_company=about_company,
            user_information_all=user_information_all,
        )
        return str(result) if result else ""


class GeminiProvider(AIProvider):
    name = "gemini"

    def create_client(self) -> Any:
        from modules.ai.geminiConnections import gemini_create_client
        return gemini_create_client()

    def extract_skills(self, client: Any, job_description: str, **kwargs) -> dict | list | None:
        from modules.ai.geminiConnections import gemini_extract_skills
        return gemini_extract_skills(client, job_description)

    def answer_question(self, client, question, *, options=None, question_type="text",
                        job_description=None, about_company=None,
                        user_information_all=None, **kw) -> str:
        from modules.ai.geminiConnections import gemini_answer_question
        result = gemini_answer_question(
            client, question, options=options, question_type=question_type,
            job_description=job_description, about_company=about_company,
            user_information_all=user_information_all,
        )
        return str(result) if result else ""


class DeepSeekProvider(AIProvider):
    name = "deepseek"

    def create_client(self) -> Any:
        from modules.ai.deepseekConnections import deepseek_create_client
        return deepseek_create_client()

    def extract_skills(self, client: Any, job_description: str, **kwargs) -> dict | list | None:
        from modules.ai.deepseekConnections import deepseek_extract_skills
        return deepseek_extract_skills(client, job_description)

    def answer_question(self, client, question, *, options=None, question_type="text",
                        job_description=None, about_company=None,
                        user_information_all=None, **kw) -> str:
        from modules.ai.deepseekConnections import deepseek_answer_question
        result = deepseek_answer_question(
            client, question, options=options, question_type=question_type,
            job_description=job_description, about_company=about_company,
            user_information_all=user_information_all,
        )
        # deepseek may return {"error": ...} dict — normalise to str
        if isinstance(result, dict):
            return result.get("error", "") if "error" in result else str(result)
        return str(result) if result else ""


class GroqProvider(AIProvider):
    name = "groq"

    def create_client(self) -> Any:
        from modules.ai.groqConnections import groq_create_client
        return groq_create_client()

    def extract_skills(self, client: Any, job_description: str, **kwargs) -> dict | list | None:
        from modules.ai.groqConnections import groq_extract_skills
        return groq_extract_skills(client, job_description)

    def answer_question(self, client, question, *, options=None, question_type="text",
                        job_description=None, about_company=None,
                        user_information_all=None, **kw) -> str:
        from modules.ai.groqConnections import groq_answer_question
        result = groq_answer_question(client, question, user_information_all or "", job_description or "")
        return str(result) if result else ""

    def tailor_resume(self, client, resume_text, job_description, instructions="") -> str:
        from modules.ai.groqConnections import groq_tailor_resume
        return groq_tailor_resume(client, resume_text, job_description, instructions)


class OllamaProvider(AIProvider):
    name = "ollama"

    def create_client(self) -> Any:
        # Ollama is a local binary — no persistent client needed.
        return "ollama_local"

    def extract_skills(self, client: Any, job_description: str, **kwargs) -> dict | list | None:
        from modules.ai.ollama_integration import generate
        from modules.ai.prompts import extract_skills_prompt
        from modules.helpers import convert_to_json
        raw = generate(extract_skills_prompt.format(job_description), timeout=120)
        if isinstance(raw, str) and not raw.startswith("[Ollama Error]"):
            return convert_to_json(raw)
        return None

    def answer_question(self, client, question, *, options=None, question_type="text",
                        job_description=None, about_company=None,
                        user_information_all=None, **kw) -> str:
        from modules.ai.ollama_integration import generate
        from modules.ai.prompts import ai_answer_prompt
        prompt = ai_answer_prompt.format(user_information_all or "", question)
        if job_description:
            prompt += f"\n\nJOB DESCRIPTION:\n{job_description}"
        result = generate(prompt, timeout=90)
        return str(result) if result and not str(result).startswith("[Ollama Error]") else ""


class HuggingFaceProvider(AIProvider):
    """Stub — HuggingFace has no dedicated connection module yet."""
    name = "huggingface"

    def create_client(self) -> Any:
        print_lg("⚠️  HuggingFace provider has no dedicated module — falling back to OpenAI-compatible client")
        from modules.ai.openaiConnections import ai_create_openai_client
        return ai_create_openai_client()

    def extract_skills(self, client, job_description, **kw):
        from modules.ai.openaiConnections import ai_extract_skills
        return ai_extract_skills(client, job_description)

    def answer_question(self, client, question, **kw) -> str:
        from modules.ai.openaiConnections import ai_answer_question
        result = ai_answer_question(client, question, **kw)
        return str(result) if result else ""


# ======================================================================
# Factory
# ======================================================================

_PROVIDERS: dict[str, type[AIProvider]] = {
    "openai":      OpenAIProvider,
    "gemini":      GeminiProvider,
    "deepseek":    DeepSeekProvider,
    "groq":        GroqProvider,
    "ollama":      OllamaProvider,
    "huggingface": HuggingFaceProvider,
}


def get_ai_provider(provider_name: str | None = None) -> AIProvider:
    """Return an ``AIProvider`` instance for *provider_name*.

    If *provider_name* is ``None`` it is read from ``config.secrets.ai_provider``.
    Raises ``ValueError`` for unknown names.
    """
    if provider_name is None:
        try:
            from config.secrets import ai_provider
            provider_name = ai_provider
        except ImportError:
            raise ValueError("Cannot determine AI provider — config.secrets.ai_provider is missing")

    key = provider_name.lower().strip()
    cls = _PROVIDERS.get(key)
    if cls is None:
        raise ValueError(
            f"Unknown AI provider '{provider_name}'. "
            f"Supported: {', '.join(sorted(_PROVIDERS))}"
        )
    return cls()
