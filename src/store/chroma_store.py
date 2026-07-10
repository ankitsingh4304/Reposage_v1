from __future__ import annotations

from typing import Sequence

from config import CHROMA_DIR, CONFIG
from src.types import Chunk, Hit


class ChromaStore:
    def __init__(self, collection_name: str | None = None):
        import chromadb

        self.collection_name = collection_name or CONFIG.collection_name
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add(self, chunks: Sequence[Chunk], vectors: Sequence[Sequence[float]]) -> None:
        if not chunks:
            return
        self._collection.add(
            ids=[c.id for c in chunks],
            embeddings=[list(v) for v in vectors],
            documents=[c.text for c in chunks],
            metadatas=[c.metadata() for c in chunks],
        )

    def search(self, query_vector: Sequence[float], k: int) -> list[Hit]:
        res = self._collection.query(
            query_embeddings=[list(query_vector)],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )
        hits: list[Hit] = []
        for cid, doc, meta, dist in zip(
            res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0]
        ):
            chunk = Chunk(
                id=cid,
                text=doc,
                path=meta.get("path", ""),
                language=meta.get("language", "text"),
                start_line=int(meta.get("start_line", 1)),
                end_line=int(meta.get("end_line", 1)),
                symbol=meta.get("symbol", ""),
            )
            hits.append(Hit(chunk=chunk, score=1.0 - float(dist)))
        return hits

    def all_chunks(self) -> list[Chunk]:
        res = self._collection.get(include=["documents", "metadatas"])
        chunks = []
        for cid, doc, meta in zip(res["ids"], res["documents"], res["metadatas"]):
            chunks.append(
                Chunk(
                    id=cid,
                    text=doc,
                    path=meta.get("path", ""),
                    language=meta.get("language", "text"),
                    start_line=int(meta.get("start_line", 1)),
                    end_line=int(meta.get("end_line", 1)),
                    symbol=meta.get("symbol", ""),
                )
            )
        return chunks

    def count(self) -> int:
        return self._collection.count()

    def reset(self) -> None:
        self._client.delete_collection(self.collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
