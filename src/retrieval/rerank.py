"""Cross-encoder reranker. Wraps a base retriever: fetch a pool of candidates,
then reorder them by direct (query, chunk) relevance and keep the top k."""
from __future__ import annotations

from functools import lru_cache

from config import CONFIG, MODELS_DIR
from src.types import Hit, Retriever


@lru_cache(maxsize=1)
def _load_cross_encoder(model_name: str):
    # FastEmbed's ONNX cross-encoder: no PyTorch, and one copy shared by all users.
    from fastembed.rerank.cross_encoder import TextCrossEncoder

    print(f"Loading reranker {model_name} ...")
    return TextCrossEncoder(model_name=model_name, cache_dir=str(MODELS_DIR),
                            threads=CONFIG.embed_threads)


class RerankingRetriever:
    def __init__(self, base: Retriever,
                 model_name: str = "Xenova/ms-marco-MiniLM-L-6-v2",
                 pool: int | None = None):
        self.base = base
        self.model_name = model_name
        self.pool = pool or CONFIG.rerank_pool

    def retrieve(self, question: str, k: int | None = None) -> list[Hit]:
        k = k or CONFIG.top_k
        candidates = self.base.retrieve(question, self.pool)
        if not candidates:
            return []
        model = _load_cross_encoder(self.model_name)
        scores = list(model.rerank(question, [h.chunk.text for h in candidates]))
        for h, s in zip(candidates, scores):
            h.score = float(s)
        candidates.sort(key=lambda h: h.score, reverse=True)
        return candidates[:k]
