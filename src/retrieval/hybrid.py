"""Dense + BM25 retrieval fused with Reciprocal Rank Fusion."""
from __future__ import annotations

import re

from config import CONFIG
from src.types import Chunk, Embedder, Hit, VectorStore

_WORD = re.compile(r"[A-Za-z0-9]+")
_CAMEL = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+")


def tokenize(text: str) -> list[str]:
    # split on non-alphanumerics, then break camelCase into subwords
    out: list[str] = []
    for w in _WORD.findall(text):
        out.append(w.lower())
        subs = _CAMEL.findall(w)
        if len(subs) > 1:
            out.extend(s.lower() for s in subs)
    return out


class HybridRetriever:
    def __init__(self, embedder: Embedder, store: VectorStore, rrf_k: int = 60,
                 pool: int | None = None):
        from rank_bm25 import BM25Okapi

        self.embedder = embedder
        self.store = store
        self.rrf_k = rrf_k
        self.pool = pool or CONFIG.retrieve_k
        self._chunks: list[Chunk] = store.all_chunks()
        # BM25Okapi divides by the corpus size, so it can't be built for an empty index.
        self._bm25 = BM25Okapi([tokenize(c.text) for c in self._chunks]) if self._chunks else None

    def retrieve(self, question: str, k: int | None = None) -> list[Hit]:
        k = k or CONFIG.top_k

        dense_hits = self.store.search(self.embedder.embed_query(question), self.pool)

        if self._bm25 is None:
            return dense_hits[:k]
        scores = self._bm25.get_scores(tokenize(question))
        top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[: self.pool]

        chunk_by_id: dict[str, Chunk] = {}
        rrf: dict[str, float] = {}
        for rank, h in enumerate(dense_hits):
            chunk_by_id[h.chunk.id] = h.chunk
            rrf[h.chunk.id] = rrf.get(h.chunk.id, 0.0) + 1.0 / (self.rrf_k + rank + 1)
        for rank, i in enumerate(top_idx):
            c = self._chunks[i]
            chunk_by_id.setdefault(c.id, c)
            rrf[c.id] = rrf.get(c.id, 0.0) + 1.0 / (self.rrf_k + rank + 1)

        ranked = sorted(rrf.items(), key=lambda kv: kv[1], reverse=True)[:k]
        return [Hit(chunk=chunk_by_id[cid], score=score) for cid, score in ranked]
