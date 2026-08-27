from __future__ import annotations

import json
import os
from dataclasses import dataclass

from config import CONFIG, DATA_DIR
from src.embeddings.bge import BGEEmbedder
from src.ingest.chunk_factory import chunk_files
from src.ingest.loader import load_repo
from src.llm.factory import make_llm
from src.retrieval.factory import make_retriever
from src.store.chroma_store import ChromaStore
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


def get_index_meta_path(user_id: int | str):
    return DATA_DIR / f"index_{user_id}.json"

def read_index_meta(user_id: int | str) -> dict | None:
    path = get_index_meta_path(user_id)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


class RAGPipeline:
    def __init__(self, user_id: int | str):
        self.user_id = user_id
        # query embedder must match the model the index was built with
        meta = read_index_meta(user_id)
        if "EMBED_MODEL" in os.environ:
            embed_model = None
        else:
            embed_model = meta.get("embed_model") if meta else None
        self.embedder = BGEEmbedder(model_name=embed_model)
        self.store = ChromaStore(collection_name=f"user_{user_id}")
        self.retriever = make_retriever(self.embedder, self.store)
        self.llm = make_llm()

    def ingest(self, source: str, reset: bool = True) -> int:
        if reset:
            self.store.reset()

        print(f"Loading {source} ...")
        files = load_repo(source)
        print(f"  {len(files)} files")

        print("Chunking ...")
        chunks = chunk_files(files)
        print(f"  {len(chunks)} chunks")

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
        meta_path = get_index_meta_path(self.user_id)
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
        print(f"Done. Collection now holds {self.store.count()} chunks.")
        return len(chunks)

    def answer(self, question: str, k: int | None = None) -> Answer:
        hits = self.retriever.retrieve(question, k or CONFIG.top_k)
        if not hits:
            return Answer(text="The index is empty. Run `ingest` first.", sources=[])
        user = f"Code context:\n\n{format_context(hits)}\n\nQuestion: {question}"
        return Answer(text=self.llm.complete(SYSTEM_PROMPT, user), sources=hits)

    def answer_agentic(self, question: str) -> Answer:
        if getattr(self, "_agent", None) is None:
            from src.agent.graph import AgenticRAG

            self._agent = AgenticRAG(self.retriever, self.llm)
        return self._agent.answer(question)

    def agentic_retriever(self):
        from src.agent.agentic import AgenticRetriever

        return AgenticRetriever(self.retriever, self.llm)
