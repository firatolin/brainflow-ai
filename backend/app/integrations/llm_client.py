"""LLM provider abstraction.

- If GEMINI_API_KEY is configured, `GeminiProvider` is used.
- Otherwise `FallbackProvider` is used; it never invents facts, always returns
  a deterministic stub so the application keeps working.
- The provider is NEVER trusted to invent IDs, vehicle data, or delivery facts.
  All business facts come from our own DB and are passed in as `context`.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Protocol

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMProvider(Protocol):
    name: str
    available: bool

    def generate_json(self, prompt: str, *, schema_hint: str) -> dict | None:
        """Return a JSON object or None on any failure."""

    def generate_text(self, prompt: str, *, max_tokens: int = 400) -> str | None:
        """Return plain text or None on any failure."""


class FallbackProvider:
    name = "fallback"
    available = False

    def generate_json(self, prompt: str, *, schema_hint: str) -> dict | None:  # noqa: ARG002
        return None

    def generate_text(self, prompt: str, *, max_tokens: int = 400) -> str | None:  # noqa: ARG002
        return None


class GeminiProvider:
    name = "gemini"
    available = True

    def __init__(self, api_key: str, model: str, timeout_s: float):
        self._api_key = api_key
        self._model = model
        self._timeout_s = timeout_s

    def _client(self):
        # Lazy import so tests without google-genai installed still pass.
        from google import genai  # type: ignore
        return genai.Client(api_key=self._api_key)

    def generate_json(self, prompt: str, *, schema_hint: str) -> dict | None:
        try:
            client = self._client()
            full = f"{prompt}\n\nRespond ONLY with valid JSON matching: {schema_hint}"
            resp = client.models.generate_content(model=self._model, contents=full)
            text = (resp.text or "").strip()
            # Strip code fences if present
            if text.startswith("```"):
                text = text.split("```", 2)[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            return json.loads(text)
        except Exception as exc:  # noqa: BLE001
            logger.warning("gemini.generate_json failed: %s", exc)
            return None

    def generate_text(self, prompt: str, *, max_tokens: int = 400) -> str | None:
        try:
            client = self._client()
            resp = client.models.generate_content(model=self._model, contents=prompt)
            text = (resp.text or "").strip()
            return text or None
        except Exception as exc:  # noqa: BLE001
            logger.warning("gemini.generate_text failed: %s", exc)
            return None


_provider: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    global _provider
    if _provider is not None:
        return _provider
    if settings.GEMINI_API_KEY:
        _provider = GeminiProvider(
            settings.GEMINI_API_KEY,
            settings.GEMINI_MODEL,
            settings.GEMINI_TIMEOUT_SECONDS,
        )
    else:
        _provider = FallbackProvider()
    return _provider


def reset_provider_for_tests() -> None:
    """Test hook — clears cached provider so changes to settings take effect."""
    global _provider
    _provider = None
