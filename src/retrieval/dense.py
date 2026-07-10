from __future__ import annotations

from config import CONFIG
from src.types import Embedder, Hit, VectorStore


class DenseRetriever:
    def __init__(self, embedder: Embedder, store: VectorStore):
        self.embedder = embedder
        self.store = store

    def retrieve(self, question: str, k: int | None = None) -> list[Hit]:
        k = k or CONFIG.top_k
        return self.store.search(self.embedder.embed_query(question), k)
