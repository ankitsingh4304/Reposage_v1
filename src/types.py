from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Sequence, runtime_checkable


@dataclass(frozen=True)
class SourceFile:
    path: str
    language: str
    text: str


@dataclass(frozen=True)
class Chunk:
    id: str
    text: str
    path: str
    language: str
    start_line: int
    end_line: int
    symbol: str = ""

    def metadata(self) -> dict:
        return {
            "path": self.path,
            "language": self.language,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "symbol": self.symbol,
        }

    def citation(self) -> str:
        loc = f"{self.path}:{self.start_line}-{self.end_line}"
        return f"{loc} ({self.symbol})" if self.symbol else loc


@dataclass
class Hit:
    chunk: Chunk
    score: float
    extra: dict = field(default_factory=dict)


@runtime_checkable
class Embedder(Protocol):
    dim: int
    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


@runtime_checkable
class VectorStore(Protocol):
    def add(self, chunks: Sequence[Chunk], vectors: Sequence[Sequence[float]]) -> None: ...
    def search(self, query_vector: Sequence[float], k: int) -> list[Hit]: ...
    def count(self) -> int: ...
    def reset(self) -> None: ...


@runtime_checkable
class Retriever(Protocol):
    def retrieve(self, question: str, k: int) -> list[Hit]: ...


@runtime_checkable
class LLMClient(Protocol):
    def complete(self, system: str, user: str) -> str: ...
