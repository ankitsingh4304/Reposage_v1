from __future__ import annotations

from functools import cached_property

from config import CONFIG


class AnthropicClient:
    def __init__(self, model: str | None = None, max_tokens: int | None = None):
        self.model = model or CONFIG.llm_model
        self.max_tokens = max_tokens or CONFIG.llm_max_tokens

    @cached_property
    def _client(self):
        import anthropic

        if not CONFIG.llm_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set.")
        return anthropic.Anthropic()

    def complete(self, system: str, user: str) -> str:
        response = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(b.text for b in response.content if b.type == "text").strip()
