from __future__ import annotations

from config import CONFIG
from src.types import LLMClient


def make_llm() -> LLMClient:
    if CONFIG.llm_is_anthropic:
        from src.llm.anthropic_client import AnthropicClient

        return AnthropicClient()
    from src.llm.openai_compatible import OpenAICompatibleLLM

    return OpenAICompatibleLLM()
