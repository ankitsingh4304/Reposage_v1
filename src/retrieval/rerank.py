"""Cross-encoder reranker. Wraps a base retriever: fetch a pool of candidates,
then reorder them by direct (query, chunk) relevance and keep the top k."""
from __future__ import annotations

from functools import cached_property

from config import CONFIG
from src.types import Hit, Retriever


class RerankingRetriever:
    def __init__(self, base: Retriever,
                 model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
                 pool: int | None = None):
        self.base = base
        self.model_name = model_name
        self.pool = pool or CONFIG.rerank_pool

    @cached_property
    def _score(self):
        print(f"Loading reranker {self.model_name} ...")
        try:
            from fastembed.rerank.cross_encoder import TextCrossEncoder
        except ImportError:
            from sentence_transformers import CrossEncoder

            model = CrossEncoder(self.model_name)
            return lambda q, docs: model.predict([(q, d) for d in docs])
        # fastembed ships the same model as an ONNX export under the Xenova namespace.
        onnx_name = self.model_name.replace("cross-encoder/", "Xenova/")
        model = TextCrossEncoder(onnx_name)
        return lambda q, docs: list(model.rerank(q, docs))

    def retrieve(self, question: str, k: int | None = None) -> list[Hit]:
        k = k or CONFIG.top_k
        candidates = self.base.retrieve(question, self.pool)
        if not candidates:
            return []
        scores = self._score(question, [h.chunk.text for h in candidates])
        for h, s in zip(candidates, scores):
            h.score = float(s)
        candidates.sort(key=lambda h: h.score, reverse=True)
        return candidates[:k]
