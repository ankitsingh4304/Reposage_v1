"""Relevance grading, query rewriting, and a self-correcting retriever."""
from __future__ import annotations

from config import CONFIG
from src.types import Hit, LLMClient, Retriever

_GRADE_SYSTEM = (
    "You judge whether retrieved code snippets are sufficient to answer a question "
    "about a codebase. Reply with exactly one word: YES or NO."
)

_REWRITE_SYSTEM = (
    "You rewrite a question about a codebase into a better code search query. "
    "Add likely function names, class names, and technical identifiers that would "
    "appear in the relevant source. Output only the rewritten query on one line."
)


def _snippet_block(hits: list[Hit], n: int = 4, chars: int = 500) -> str:
    return "\n\n".join(f"[{h.chunk.citation()}]\n{h.chunk.text[:chars]}" for h in hits[:n])


def grade_relevance(llm: LLMClient, question: str, hits: list[Hit]) -> bool:
    if not hits:
        return False
    user = (
        f"Question: {question}\n\nRetrieved snippets:\n{_snippet_block(hits)}\n\n"
        "Do these snippets contain the code needed to answer? Reply YES or NO."
    )
    return llm.complete(_GRADE_SYSTEM, user).strip().upper().startswith("Y")


def rewrite_query(llm: LLMClient, question: str, previous: str) -> str:
    user = (
        f"Original question: {question}\n"
        f"Previous search query (weak results): {previous}\n\n"
        "Rewrite into a stronger code-search query."
    )
    new_q = llm.complete(_REWRITE_SYSTEM, user).strip().splitlines()[0].strip()
    return new_q or question


class AgenticRetriever:
    def __init__(self, base: Retriever, llm: LLMClient, max_rewrites: int | None = None):
        self.base = base
        self.llm = llm
        self.max_rewrites = CONFIG.agent_max_rewrites if max_rewrites is None else max_rewrites
        self.last_trace: dict = {}

    def retrieve(self, question: str, k: int | None = None) -> list[Hit]:
        k = k or CONFIG.top_k
        query = question
        queries = [query]
        hits = self.base.retrieve(query, k)
        rewrites = 0
        while rewrites < self.max_rewrites and not grade_relevance(self.llm, question, hits):
            query = rewrite_query(self.llm, question, query)
            queries.append(query)
            hits = self.base.retrieve(query, k)
            rewrites += 1
        self.last_trace = {"rewrites": rewrites, "queries": queries}
        return hits
