from __future__ import annotations

import os
from dataclasses import dataclass

from config import CONFIG
from src.embeddings.fast import get_embedder
from src.ingest.chunk_factory import chunk_files
from src.ingest.loader import cleanup_clone, load_repo
from src.llm.factory import make_llm
from src.retrieval.factory import make_retriever
from src.storage.index_meta import delete_index_meta, read_index_meta, write_index_meta
from src.store.qdrant_store import QdrantStore
from src.types import Hit

SYSTEM_PROMPT = """You are a precise codebase assistant. Answer the user's question \
using ONLY the provided code context. Every claim about the code must be grounded in \
that context. Cite the file and line range for each fact you state, like \
`src/auth/login.py:42-58`. If the context does not contain the answer, say so plainly \
instead of guessing. Prefer short, direct answers with the relevant code references."""


@dataclass
class Answer:
    text: str
    sources: list[Hit]
    trace: dict | None = None


def format_context(hits: list[Hit]) -> str:
    return "\n\n".join(f"--- {h.chunk.citation()} ---\n{h.chunk.text}" for h in hits)


def format_history(history: list[dict] | None, max_chars: int = 600) -> str:
    """Earlier turns of the chat, trimmed, so follow-up questions make sense."""
    if not history:
        return ""
    lines = []
    for turn in history:
        who = "User" if turn.get("role") == "user" else "Assistant"
        text = (turn.get("content") or "").strip()
        if len(text) > max_chars:
            text = text[:max_chars] + " ..."
        lines.append(f"{who}: {text}")
    return "Earlier in this conversation:\n" + "\n\n".join(lines) + "\n\n"


def build_user_prompt(question: str, hits: list[Hit], history: list[dict] | None = None) -> str:
    return (f"{format_history(history)}Code context:\n\n{format_context(hits)}\n\n"
            f"Question: {question}")


def retrieval_query(question: str, history: list[dict] | None) -> str:
    # A follow-up like "and where is that tested?" retrieves better with the
    # previous question attached.
    if history:
        prev = [t["content"] for t in history if t.get("role") == "user" and t.get("content")]
        if prev:
            return f"{prev[-1]}\n{question}"
    return question


class RepoTooLargeError(ValueError):
    pass


class RAGPipeline:
    def __init__(self, user_id: int | str):
        self.user_id = user_id
        # query embedder must match the model the index was built with
        meta = read_index_meta(user_id)
        if "EMBED_MODEL" in os.environ:
            embed_model = None
        else:
            embed_model = meta.get("embed_model") if meta else None
        # Shared across users: one model in memory, not one per user.
        self.embedder = get_embedder(embed_model)
        self.store = QdrantStore(user_id, dim=self.embedder.dim)
        self.llm = make_llm()
        self._agent = None
        self.retriever = make_retriever(self.embedder, self.store)

    def _rebuild_retriever(self) -> None:
        # Hybrid search keeps a keyword index of the chunks in memory; rebuild it
        # after an ingest so it sees the new repo.
        self.retriever = make_retriever(self.embedder, self.store)
        self._agent = None

    def ingest(self, source: str, reset: bool = True) -> int:
        print(f"Loading {source} ...")
        try:
            files = load_repo(source)
        finally:
            cleanup_clone(source)  # file texts are in memory now; free the disk
        print(f"  {len(files)} files")

        print("Chunking ...")
        chunks = chunk_files(files)
        print(f"  {len(chunks)} chunks")
        if CONFIG.max_ingest_chunks and len(chunks) > CONFIG.max_ingest_chunks:
            raise RepoTooLargeError(
                f"This repo splits into {len(chunks)} chunks; this server's limit is "
                f"{CONFIG.max_ingest_chunks}. Try a smaller repo."
            )

        if reset:
            # If embedding fails halfway, show "no repo indexed" instead of a stale name.
            delete_index_meta(self.user_id)
            self.store.reset()

        print("Embedding + storing ...")
        batch = CONFIG.embed_batch_size
        for i in range(0, len(chunks), batch):
            group = chunks[i : i + batch]
            vectors = self.embedder.embed_documents([c.text for c in group])
            self.store.add(group, vectors)

        meta = {
            "source": source,
            "embed_model": self.embedder.model_name,
            "chunker": CONFIG.chunker,
            "n_files": len(files),
            "n_chunks": len(chunks),
            "count": self.store.count(),
        }
        write_index_meta(self.user_id, meta)
        self._rebuild_retriever()
        print(f"Done. Collection now holds {self.store.count()} chunks.")
        return len(chunks)

    def answer(self, question: str, k: int | None = None,
               history: list[dict] | None = None) -> Answer:
        hits = self.retriever.retrieve(retrieval_query(question, history), k or CONFIG.top_k)
        if not hits:
            return Answer(text="The index is empty. Run `ingest` first.", sources=[])
        user = build_user_prompt(question, hits, history)
        return Answer(text=self.llm.complete(SYSTEM_PROMPT, user), sources=hits)

    def answer_agentic(self, question: str, history: list[dict] | None = None) -> Answer:
        if self._agent is None:
            from src.agent.graph import AgenticRAG

            self._agent = AgenticRAG(self.retriever, self.llm)
        return self._agent.answer(question, history=history)

    def agentic_retriever(self):
        from src.agent.agentic import AgenticRetriever

        return AgenticRetriever(self.retriever, self.llm)
