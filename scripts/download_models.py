"""Download the FastEmbed model(s) into ./models at build time.

Render (and Docker) run this during the build, so the server never downloads the
model on a cold start. Run it locally too if you like: python scripts/download_models.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import CONFIG, MODELS_DIR  # noqa: E402


def main() -> None:
    from fastembed import TextEmbedding

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading embedding model {CONFIG.embed_model} -> {MODELS_DIR}")
    model = TextEmbedding(model_name=CONFIG.embed_model, cache_dir=str(MODELS_DIR))
    dim = len(next(iter(model.query_embed("hello"))))
    print(f"  ok, {dim} dimensions")

    if CONFIG.rerank:
        from fastembed.rerank.cross_encoder import TextCrossEncoder

        name = "Xenova/ms-marco-MiniLM-L-6-v2"
        print(f"Downloading reranker {name}")
        TextCrossEncoder(model_name=name, cache_dir=str(MODELS_DIR))


if __name__ == "__main__":
    main()
