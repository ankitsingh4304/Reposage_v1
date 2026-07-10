from __future__ import annotations

import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import CONFIG
from src.pipeline.rag import RAGPipeline, read_index_meta

app = FastAPI(title="Chat with a Codebase")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_pipeline: RAGPipeline | None = None
_lock = threading.Lock()


def pipeline() -> RAGPipeline:
    global _pipeline
    with _lock:
        if _pipeline is None:
            _pipeline = RAGPipeline()
        return _pipeline


def engine_info() -> dict:
    return {
        "provider": CONFIG.llm_provider,
        "model": CONFIG.llm_model.split("/")[-1],
        "retriever": CONFIG.retriever + (" + rerank" if CONFIG.rerank else ""),
    }


def serialize(hit) -> dict:
    c = hit.chunk
    return {
        "citation": c.citation(),
        "path": c.path,
        "language": c.language,
        "start_line": c.start_line,
        "end_line": c.end_line,
        "symbol": c.symbol,
        "text": c.text,
        "score": round(hit.score, 4),
    }


class IngestBody(BaseModel):
    source: str


class AskBody(BaseModel):
    question: str
    agentic: bool = False


@app.get("/api/status")
def status() -> dict:
    return {"index": read_index_meta(), "engine": engine_info()}


@app.post("/api/ingest")
def ingest(body: IngestBody) -> dict:
    source = body.source.strip()
    if not source:
        raise HTTPException(400, "Repository URL or path is required.")
    try:
        n = pipeline().ingest(source)
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}")
    return {"n_chunks": n, "index": read_index_meta()}


@app.post("/api/ask")
def ask(body: AskBody) -> dict:
    question = body.question.strip()
    if not question:
        raise HTTPException(400, "Question is required.")
    if read_index_meta() is None:
        raise HTTPException(409, "No repository indexed yet.")
    try:
        pipe = pipeline()
        ans = pipe.answer_agentic(question) if body.agentic else pipe.answer(question)
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}")
    return {
        "text": ans.text,
        "sources": [serialize(h) for h in ans.sources],
        "trace": ans.trace,
    }


_DIST = ROOT / "frontend" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="static")
