"""AI provider abstraction supporting OpenAI, Anthropic, and Google."""

import json
import logging
from abc import ABC, abstractmethod

from app.core.config import settings

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """Abstract base for AI chat providers."""

    @abstractmethod
    async def chat(self, system_prompt: str, user_message: str) -> str | None:
        """Send a chat message and return the response text, or None on failure."""
        ...


class OpenAIProvider(AIProvider):
    def __init__(self):
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=60.0)

    async def chat(self, system_prompt: str, user_message: str) -> str | None:
        try:
            resp = await self._client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.3,
                max_completion_tokens=4096,
                response_format={"type": "json_object"},
            )
            return resp.choices[0].message.content
        except Exception:
            logger.exception("OpenAI chat failed")
            return None


class AnthropicProvider(AIProvider):
    def __init__(self):
        import anthropic
        self._client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key, timeout=60.0,
        )

    async def chat(self, system_prompt: str, user_message: str) -> str | None:
        try:
            resp = await self._client.messages.create(
                model=settings.anthropic_model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            return resp.content[0].text
        except Exception:
            logger.exception("Anthropic chat failed")
            return None


class GoogleProvider(AIProvider):
    def __init__(self):
        from google import genai
        self._client = genai.Client(api_key=settings.google_ai_api_key)

    async def chat(self, system_prompt: str, user_message: str) -> str | None:
        try:
            from google.genai import types
            response = await self._client.aio.models.generate_content(
                model=settings.google_model,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.3,
                    max_output_tokens=4096,
                    response_mime_type="application/json",
                ),
            )
            return response.text
        except Exception:
            logger.exception("Google AI chat failed")
            return None


# Module-level cached provider
_provider: AIProvider | None = None
_provider_name: str | None = None


def get_ai_provider() -> AIProvider | None:
    """Get the configured AI provider, or None if unavailable."""
    global _provider, _provider_name

    target = settings.ai_provider
    if _provider and _provider_name == target:
        return _provider

    try:
        if target == "openai" and settings.openai_api_key:
            _provider = OpenAIProvider()
        elif target == "anthropic" and settings.anthropic_api_key:
            _provider = AnthropicProvider()
        elif target == "google" and settings.google_ai_api_key:
            _provider = GoogleProvider()
        else:
            logger.warning("No AI provider configured or API key missing for '%s'", target)
            _provider = None
        _provider_name = target
    except Exception:
        logger.exception("Failed to initialize AI provider '%s'", target)
        _provider = None
        _provider_name = None

    return _provider


def set_ai_provider(name: str) -> bool:
    """Switch the active AI provider at runtime. Returns True if successful."""
    global _provider, _provider_name
    old = settings.ai_provider
    settings.ai_provider = name
    _provider = None
    _provider_name = None
    result = get_ai_provider()
    if result is None:
        settings.ai_provider = old
        _provider = None
        _provider_name = None
        return False
    return True


async def test_ai_provider() -> dict:
    """Test connectivity to the current AI provider."""
    provider = get_ai_provider()
    if not provider:
        return {"status": "not_configured", "provider": settings.ai_provider}
    try:
        result = await provider.chat(
            "You are a test endpoint. Respond with valid JSON: {\"ok\": true}",
            "Please respond with the JSON test object.",
        )
        if result:
            return {"status": "connected", "provider": settings.ai_provider}
        return {"status": "error", "provider": settings.ai_provider}
    except Exception as e:
        return {"status": "error", "provider": settings.ai_provider, "detail": str(e)}


def parse_ai_json(text: str | None) -> dict | list | None:
    """Safely parse AI response as JSON."""
    if not text:
        return None
    try:
        # Strip markdown code fences if present
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        logger.warning("Failed to parse AI response as JSON: %s", text[:200])
        return None
