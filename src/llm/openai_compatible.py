"""LLM client for any OpenAI-compatible endpoint (Gemini, Groq, OpenRouter, ...)."""
from __future__ import annotations

from functools import cached_property

from config import CONFIG


class OpenAICompatibleLLM:
    def __init__(self, model: str | None = None, base_url: str | None = None,
                 api_key: str | None = None, max_tokens: int | None = None):
        self.model = model or CONFIG.llm_model
        self.base_url = base_url or CONFIG.llm_base_url
        self.api_key = api_key or CONFIG.llm_api_key
        self.max_tokens = max_tokens or CONFIG.llm_max_tokens

    @cached_property
    def _client(self):
        from openai import OpenAI

        if not self.api_key:
            raise RuntimeError(
                f"No API key for provider '{CONFIG.llm_provider}'. Add it to .env."
            )
        # extra retries because free tiers throttle transiently (429/503)
        return OpenAI(api_key=self.api_key, base_url=self.base_url,
                      max_retries=5, timeout=60.0)

    def complete(self, system: str, user: str) -> str:
        response = self._client.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return (response.choices[0].message.content or "").strip()
