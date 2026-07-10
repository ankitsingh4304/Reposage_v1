"""LangGraph agent: retrieve -> grade -> rewrite (retry) -> generate."""
from __future__ import annotations

from typing import TypedDict

from config import CONFIG
from src.agent.agentic import grade_relevance, rewrite_query
from src.pipeline.rag import SYSTEM_PROMPT, Answer, format_context
from src.types import Hit, LLMClient, Retriever


class AgentState(TypedDict, total=False):
    question: str
    query: str
    documents: list
    relevant: bool
    rewrites: int
    answer: str


def build_graph(base: Retriever, llm: LLMClient, k: int, max_rewrites: int):
    from langgraph.graph import END, START, StateGraph

    def retrieve(state: AgentState) -> AgentState:
        return {"documents": base.retrieve(state["query"], k)}

    def grade(state: AgentState) -> AgentState:
        return {"relevant": grade_relevance(llm, state["question"], state["documents"])}

    def decide(state: AgentState) -> str:
        if state["relevant"] or state.get("rewrites", 0) >= max_rewrites:
            return "generate"
        return "rewrite"

    def rewrite(state: AgentState) -> AgentState:
        new_q = rewrite_query(llm, state["question"], state["query"])
        return {"query": new_q, "rewrites": state.get("rewrites", 0) + 1}

    def generate(state: AgentState) -> AgentState:
        user = f"Code context:\n\n{format_context(state['documents'])}\n\nQuestion: {state['question']}"
        return {"answer": llm.complete(SYSTEM_PROMPT, user)}

    g = StateGraph(AgentState)
    g.add_node("retrieve", retrieve)
    g.add_node("grade", grade)
    g.add_node("rewrite", rewrite)
    g.add_node("generate", generate)
    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "grade")
    g.add_conditional_edges("grade", decide, {"generate": "generate", "rewrite": "rewrite"})
    g.add_edge("rewrite", "retrieve")
    g.add_edge("generate", END)
    return g.compile()


class AgenticRAG:
    def __init__(self, base: Retriever, llm: LLMClient, k: int | None = None,
                 max_rewrites: int | None = None):
        self.k = k or CONFIG.top_k
        self.max_rewrites = CONFIG.agent_max_rewrites if max_rewrites is None else max_rewrites
        self.graph = build_graph(base, llm, self.k, self.max_rewrites)

    def answer(self, question: str) -> Answer:
        final = self.graph.invoke({"question": question, "query": question, "rewrites": 0})
        hits: list[Hit] = final.get("documents", [])
        return Answer(text=final.get("answer", ""), sources=hits,
                      trace={"rewrites": final.get("rewrites", 0)})
