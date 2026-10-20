"""Text embeddings with FastEmbed (ONNX Runtime, no PyTorch).

One model instance is shared by every user: `get_embedder()` caches it per model
name, so ten users don't load ten copies into memory.
"""
from __future__ import annotations

import threading
from functools import cached_property, lru_cache
from typing import Sequence

from config import CONFIG, MODELS_DIR


class FastEmbedder:
    def __init__(self, model_name: str | None = None, batch_size: int | None = None):
        self.model_name = model_name or CONFIG.embed_model
        self.batch_size = batch_size or CONFIG.embed_batch_size
        # ONNX sessions are thread-safe, but one at a time keeps peak memory low.
        self._lock = threading.Lock()

    @cached_property
    def _model(self):
        from fastembed import TextEmbedding

        print(f"Loading embedding model {self.model_name} ...")
        return TextEmbedding(
            model_name=self.model_name,
            cache_dir=str(MODELS_DIR),
            threads=CONFIG.embed_threads,
        )

    @cached_property
    def dim(self) -> int:
        return len(self.embed_query("dimension probe"))

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        with self._lock:
            vecs = self._model.passage_embed(list(texts), batch_size=self.batch_size)
            return [v.tolist() for v in vecs]

    def embed_query(self, text: str) -> list[float]:
        with self._lock:
            return next(iter(self._model.query_embed(text))).tolist()


@lru_cache(maxsize=2)
def get_embedder(model_name: str | None = None) -> FastEmbedder:
    return FastEmbedder(model_name or CONFIG.embed_model)
