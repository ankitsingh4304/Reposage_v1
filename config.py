from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
REPOS_DIR = DATA_DIR / "repos"
CHROMA_DIR = DATA_DIR / "chroma"
INDEX_META = DATA_DIR / "index_meta.json"


def _get(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Config:
    embed_model: str = _get("EMBED_MODEL", "BAAI/bge-m3")
    embed_batch_size: int = int(_get("EMBED_BATCH_SIZE", "32"))

    collection_name: str = _get("COLLECTION_NAME", "codebase")

    chunker: str = _get("CHUNKER", "recursive")            # recursive | treesitter
    chunk_size: int = int(_get("CHUNK_SIZE", "1200"))
    chunk_overlap: int = int(_get("CHUNK_OVERLAP", "150"))

    top_k: int = int(_get("TOP_K", "8"))
    retrieve_k: int = int(_get("RETRIEVE_K", "40"))
    retriever: str = _get("RETRIEVER", "dense")            # dense | hybrid
    agent_max_rewrites: int = int(_get("AGENT_MAX_REWRITES", "2"))
    rerank: bool = _get("RERANK", "0") in {"1", "true", "True"}
    rerank_pool: int = int(_get("RERANK_POOL", "12"))

    llm_provider: str = _get("LLM_PROVIDER", "gemini")
    llm_max_tokens: int = int(_get("LLM_MAX_TOKENS", "4096"))

    @property
    def _preset(self) -> dict:
        return LLM_PRESETS.get(self.llm_provider, LLM_PRESETS["gemini"])

    @property
    def llm_is_anthropic(self) -> bool:
        return self.llm_provider == "anthropic"

    @property
    def llm_model(self) -> str:
        return _get("LLM_MODEL", self._preset["model"])

    @property
    def llm_base_url(self) -> str | None:
        return _get("LLM_BASE_URL", self._preset["base_url"] or "") or None

    @property
    def llm_api_key(self) -> str:
        return _get("LLM_API_KEY", "") or _get(self._preset["key_env"], "")


# provider -> OpenAI-compatible endpoint + default model + key env var
LLM_PRESETS = {
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "model": "gemini-flash-latest",
        "key_env": "GEMINI_API_KEY",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "key_env": "GROQ_API_KEY",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "qwen/qwen3-coder:free",
        "key_env": "OPENROUTER_API_KEY",
    },
    "anthropic": {
        "base_url": None,
        "model": "claude-opus-4-8",
        "key_env": "ANTHROPIC_API_KEY",
    },
}

CONFIG = Config()

IGNORE_DIRS = {
    ".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build",
    ".next", "target", "vendor", ".idea", ".vscode", "site-packages", ".mypy_cache",
    ".pytest_cache", "coverage", ".turbo", "out",
}
IGNORE_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".pdf", ".zip", ".gz", ".tar",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".lock", ".woff", ".woff2", ".ttf",
    ".mp4", ".mp3", ".mov", ".class", ".pyc", ".min.js", ".map",
}
MAX_FILE_BYTES = 500_000
