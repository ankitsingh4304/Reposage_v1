from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
REPOS_DIR = DATA_DIR / "repos"
# Used only when QDRANT_URL is empty: Qdrant then runs in-process and stores vectors here.
QDRANT_LOCAL_DIR = DATA_DIR / "qdrant"
# Index info per user, used only when MONGO_URI is empty (CLI / local runs).
INDEX_META_DIR = DATA_DIR
# FastEmbed model files. Downloaded at build time (scripts/download_models.py) so the
# server doesn't fetch them on every cold start.
MODELS_DIR = Path(os.environ.get("FASTEMBED_CACHE_PATH", str(ROOT / "models")))


def _get(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Config:
    # FastEmbed (ONNX, no PyTorch) keeps memory low enough for a 512 MB server.
    embed_model: str = _get("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
    embed_batch_size: int = int(_get("EMBED_BATCH_SIZE", "16"))
    embed_threads: int = int(_get("EMBED_THREADS", "1"))

    # Qdrant: empty URL = local in-process mode (data/qdrant), handy for dev and the CLI.
    qdrant_url: str = _get("QDRANT_URL", "")
    qdrant_api_key: str = _get("QDRANT_API_KEY", "")
    collection_name: str = _get("QDRANT_COLLECTION", "reposage_chunks")

    # Protects a small server from repos that would take too long to embed.
    max_ingest_chunks: int = int(_get("MAX_INGEST_CHUNKS", "3000"))

    chunker: str = _get("CHUNKER", "recursive")            # recursive | treesitter
    chunk_size: int = int(_get("CHUNK_SIZE", "1200"))
    chunk_overlap: int = int(_get("CHUNK_OVERLAP", "150"))

    top_k: int = int(_get("TOP_K", "8"))
    retrieve_k: int = int(_get("RETRIEVE_K", "40"))
    retriever: str = _get("RETRIEVER", "hybrid")           # dense | hybrid
    agent_max_rewrites: int = int(_get("AGENT_MAX_REWRITES", "2"))
    rerank: bool = _get("RERANK", "0") in {"1", "true", "True"}
    rerank_pool: int = int(_get("RERANK_POOL", "12"))

    llm_provider: str = _get("LLM_PROVIDER", "groq")
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
        # llama-3.3-70b-versatile was shut down on Groq on 2026-08-16.
        "model": "openai/gpt-oss-120b",
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
