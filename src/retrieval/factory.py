from __future__ import annotations

from config import CONFIG
from src.types import Embedder, Retriever, VectorStore


def make_retriever(embedder: Embedder, store: VectorStore) -> Retriever:
    if CONFIG.retriever == "hybrid":
        from src.retrieval.hybrid import HybridRetriever

        base: Retriever = HybridRetriever(embedder, store)
    else:
        from src.retrieval.dense import DenseRetriever

        base = DenseRetriever(embedder, store)

    if CONFIG.rerank:
        from src.retrieval.rerank import RerankingRetriever

        return RerankingRetriever(base)
    return base
