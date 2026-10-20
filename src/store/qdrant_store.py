"""Vector store on Qdrant.

All users share one collection; every point carries a `user_id` payload and every
query filters on it. With QDRANT_URL empty, Qdrant runs in-process and keeps its
files in data/qdrant (good for local dev and the CLI).
"""
from __future__ import annotations

import atexit
import uuid
from functools import lru_cache
from typing import Sequence

from config import CONFIG, QDRANT_LOCAL_DIR
from src.types import Chunk, Hit

_ID_NAMESPACE = uuid.UUID("6f0b2c1e-3a4d-4b5e-9c7f-8a1b2c3d4e5f")
_UPSERT_BATCH = 64


@lru_cache(maxsize=1)
def get_client():
    from qdrant_client import QdrantClient

    if CONFIG.qdrant_url:
        return QdrantClient(url=CONFIG.qdrant_url, api_key=CONFIG.qdrant_api_key or None,
                            timeout=60)
    QDRANT_LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    client = QdrantClient(path=str(QDRANT_LOCAL_DIR))
    atexit.register(client.close)  # close cleanly before Python tears down modules
    return client


def _chunk_from_payload(payload: dict) -> Chunk:
    return Chunk(
        id=payload.get("chunk_id", ""),
        text=payload.get("text", ""),
        path=payload.get("path", ""),
        language=payload.get("language", "text"),
        start_line=int(payload.get("start_line", 1)),
        end_line=int(payload.get("end_line", 1)),
        symbol=payload.get("symbol", ""),
    )


class QdrantStore:
    def __init__(self, user_id: str, dim: int, collection_name: str | None = None):
        from qdrant_client import models

        self._m = models
        self.user_id = str(user_id)
        self.dim = dim
        self.collection_name = collection_name or CONFIG.collection_name
        self._client = get_client()
        self._ensure_collection()
        self._filter = models.Filter(must=[
            models.FieldCondition(key="user_id", match=models.MatchValue(value=self.user_id))
        ])

    def _ensure_collection(self) -> None:
        m = self._m
        if not self._client.collection_exists(self.collection_name):
            self._client.create_collection(
                collection_name=self.collection_name,
                vectors_config=m.VectorParams(size=self.dim, distance=m.Distance.COSINE),
            )
            # Qdrant Cloud wants an index on fields used in filters.
            self._client.create_payload_index(
                collection_name=self.collection_name,
                field_name="user_id",
                field_schema=m.PayloadSchemaType.KEYWORD,
            )
            return
        info = self._client.get_collection(self.collection_name)
        size = info.config.params.vectors.size
        if size != self.dim:
            raise RuntimeError(
                f"Qdrant collection '{self.collection_name}' stores {size}-dim vectors but "
                f"the embedding model makes {self.dim}-dim ones. Set QDRANT_COLLECTION to a "
                "new name (or delete the old collection) after changing EMBED_MODEL."
            )

    def _point_id(self, chunk_id: str) -> str:
        return str(uuid.uuid5(_ID_NAMESPACE, f"{self.user_id}:{chunk_id}"))

    def add(self, chunks: Sequence[Chunk], vectors: Sequence[Sequence[float]]) -> None:
        points = [
            self._m.PointStruct(
                id=self._point_id(c.id),
                vector=list(v),
                payload={"user_id": self.user_id, "chunk_id": c.id, "text": c.text,
                         **c.metadata()},
            )
            for c, v in zip(chunks, vectors)
        ]
        for i in range(0, len(points), _UPSERT_BATCH):
            self._client.upsert(self.collection_name, points=points[i:i + _UPSERT_BATCH],
                                wait=True)

    def search(self, query_vector: Sequence[float], k: int) -> list[Hit]:
        res = self._client.query_points(
            collection_name=self.collection_name,
            query=list(query_vector),
            query_filter=self._filter,
            limit=k,
            with_payload=True,
        )
        return [Hit(chunk=_chunk_from_payload(p.payload or {}), score=float(p.score))
                for p in res.points]

    def all_chunks(self) -> list[Chunk]:
        chunks: list[Chunk] = []
        offset = None
        while True:
            points, offset = self._client.scroll(
                collection_name=self.collection_name,
                scroll_filter=self._filter,
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            chunks.extend(_chunk_from_payload(p.payload or {}) for p in points)
            if offset is None:
                return chunks

    def count(self) -> int:
        return self._client.count(self.collection_name, count_filter=self._filter,
                                  exact=True).count

    def reset(self) -> None:
        self._client.delete(
            collection_name=self.collection_name,
            points_selector=self._m.FilterSelector(filter=self._filter),
            wait=True,
        )
