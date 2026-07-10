"""Run a labeled eval set through a retriever, report metrics, save/compare runs."""
from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

from config import ROOT
from eval import metrics as M
from src.types import Retriever

RESULTS_DIR = ROOT / "eval" / "results"
K_VALUES = (1, 3, 5, 10)


def _ordered_unique(paths):
    seen, out = set(), []
    for p in paths:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def load_eval_set(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def evaluate(retriever: Retriever, eval_set: dict, retrieve_k: int = 10) -> dict:
    per_question = []
    for item in eval_set["questions"]:
        q, relevant = item["question"], item["relevant_files"]
        hits = retriever.retrieve(q, retrieve_k)
        retrieved = _ordered_unique([h.chunk.path for h in hits])
        row = {
            "question": q,
            "relevant": relevant,
            "retrieved": retrieved[:retrieve_k],
            "rr": M.reciprocal_rank(retrieved, relevant),
            "recall@10": M.recall_at_k(retrieved, relevant, 10),
        }
        for k in K_VALUES:
            row[f"hit@{k}"] = M.hit_at_k(retrieved, relevant, k)
        per_question.append(row)

    names = [f"hit@{k}" for k in K_VALUES] + ["rr", "recall@10"]
    aggregate = {m: round(mean(r[m] for r in per_question), 4) for m in per_question and names}
    aggregate["MRR"] = aggregate.pop("rr")
    return {
        "eval_set": eval_set.get("name", "unnamed"),
        "n": len(per_question),
        "aggregate": aggregate,
        "per_question": per_question,
    }


def save_result(result: dict, label: str) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"{label}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"label": label, **result}, f, indent=2)
    return path


def _load_result(label: str) -> dict | None:
    path = RESULTS_DIR / f"{label}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def print_report(result: dict, label: str, compare_to: str | None = None) -> None:
    agg = result["aggregate"]
    order = [f"hit@{k}" for k in K_VALUES] + ["MRR", "recall@10"]
    prev = _load_result(compare_to) if compare_to else None

    print(f"\nEval: {result['eval_set']}  ({result['n']} questions)")
    print(f"Run:  {label}" + (f"   vs   {compare_to}" if prev else ""))
    print("-" * 52)
    if prev:
        prev_agg = prev["aggregate"]
        print(f"{'metric':<12}{'this':>10}{'prev':>10}{'delta':>12}")
        for m in order:
            cur, old = agg[m], prev_agg.get(m, 0.0)
            d = cur - old
            arrow = "  " if abs(d) < 1e-9 else ("[+]" if d > 0 else "[-]")
            print(f"{m:<12}{cur:>10.3f}{old:>10.3f}{d:>+11.3f}  {arrow}")
    else:
        print(f"{'metric':<12}{'score':>10}")
        for m in order:
            print(f"{m:<12}{agg[m]:>10.3f}")
    print("-" * 52)


def run_cli(eval_path: str, label: str, retrieve_k: int, compare_to: str | None,
            retriever: Retriever | None = None, agentic: bool = False) -> dict:
    eval_set = load_eval_set(eval_path)
    if retriever is None:
        from src.pipeline.rag import RAGPipeline

        pipeline = RAGPipeline()
        retriever = pipeline.agentic_retriever() if agentic else pipeline.retriever
    result = evaluate(retriever, eval_set, retrieve_k=retrieve_k)
    path = save_result(result, label)
    print_report(result, label, compare_to)
    print(f"saved: {path}")
    return result
