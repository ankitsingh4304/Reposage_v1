from __future__ import annotations

import os
from functools import cached_property
from typing import Sequence

from config import CONFIG


def fastembed_supports(model_name: str) -> bool:
    try:
        from fastembed import TextEmbedding
    except ImportError:
        return False
    return any(m["model"] == model_name for m in TextEmbedding.list_supported_models())


class BGEEmbedder:
    """Embeds with fastembed (ONNX, no torch) when it supports the model, otherwise
    with sentence-transformers (needed for BAAI/bge-m3; install it separately)."""

    def __init__(self, model_name: str | None = None, batch_size: int | None = None):
        self.model_name = model_name or CONFIG.embed_model
        self.batch_size = batch_size or CONFIG.embed_batch_size

    @cached_property
    def backend(self) -> str:
        return "fastembed" if fastembed_supports(self.model_name) else "sentence-transformers"

    @cached_property
    def _model(self):
        print(f"Loading embedding model {self.model_name} ({self.backend}) ...")
        if self.backend == "fastembed":
            from fastembed import TextEmbedding

            threads = os.environ.get("EMBED_THREADS")
            # The ONNX memory arena keeps peak buffers forever (~800 MB at batch 32),
            # which OOMs 512 MB hosts; without it memory is returned after each batch.
            return TextEmbedding(self.model_name, threads=int(threads) if threads else None,
                                 enable_cpu_mem_arena=False)
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(self.model_name)

    @property
    def dim(self) -> int:
        return len(self.embed_query("dim"))

    def _encode(self, texts: list[str]):
        import numpy as np

        if self.backend == "fastembed":
            vecs = np.array(list(self._model.embed(texts, batch_size=self.batch_size)))
        else:
            vecs = self._model.encode(texts, batch_size=self.batch_size,
                                      show_progress_bar=len(texts) > 64, convert_to_numpy=True)
        return vecs / np.linalg.norm(vecs, axis=1, keepdims=True).clip(min=1e-12)

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return self._encode(list(texts)).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self._encode([text])[0].tolist()
