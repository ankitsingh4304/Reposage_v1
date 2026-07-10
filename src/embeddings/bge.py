from __future__ import annotations

from functools import cached_property
from typing import Sequence

from config import CONFIG


class BGEEmbedder:
    def __init__(self, model_name: str | None = None, batch_size: int | None = None):
        self.model_name = model_name or CONFIG.embed_model
        self.batch_size = batch_size or CONFIG.embed_batch_size

    @cached_property
    def _model(self):
        from sentence_transformers import SentenceTransformer

        print(f"Loading embedding model {self.model_name} ...")
        return SentenceTransformer(self.model_name)

    @property
    def dim(self) -> int:
        return self._model.get_sentence_embedding_dimension()

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        vecs = self._model.encode(
            list(texts),
            batch_size=self.batch_size,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 64,
            convert_to_numpy=True,
        )
        return vecs.tolist()

    def embed_query(self, text: str) -> list[float]:
        vec = self._model.encode(text, normalize_embeddings=True, convert_to_numpy=True)
        return vec.tolist()
