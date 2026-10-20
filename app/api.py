from __future__ import annotations

import sys
import threading
import os
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime

from config import CONFIG
from src.ingest.loader import normalize_github_url
from src.pipeline.rag import RAGPipeline, RepoTooLargeError
from src.storage.index_meta import read_index_meta

from app import models, auth
from app.database import db

app = FastAPI(title="Chat with a Codebase")
frontend_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv("FRONTEND_URL", "http://localhost:5173").split(",")
    if origin.strip()
]
for local_origin in ("http://localhost:5173", "http://127.0.0.1:5173"):
    if local_origin not in frontend_origins:
        frontend_origins.append(local_origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)

# Recently active users keep a ready pipeline. The models inside are shared, so each
# entry only costs that user's keyword index; the oldest entry is dropped past the cap.
_MAX_PIPELINES = int(os.getenv("MAX_CACHED_PIPELINES", "20"))
_pipelines: OrderedDict[str, RAGPipeline] = OrderedDict()
_lock = threading.Lock()
# One ingest at a time: embedding is the heaviest thing this server does.
_ingest_lock = threading.Lock()


def pipeline(user_id: str) -> RAGPipeline:
    uid = str(user_id)
    with _lock:
        if uid in _pipelines:
            _pipelines.move_to_end(uid)
        else:
            _pipelines[uid] = RAGPipeline(uid)
            while len(_pipelines) > _MAX_PIPELINES:
                _pipelines.popitem(last=False)
        return _pipelines[uid]


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


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/status")
def status(user: models.User = Depends(auth.get_current_user)) -> dict:
    return {"index": read_index_meta(user.id), "engine": engine_info()}


@app.post("/api/ingest")
def ingest(body: IngestBody, user: models.User = Depends(auth.get_current_user)) -> dict:
    source = body.source.strip()
    if not source:
        raise HTTPException(400, "Repository URL is required.")
    url = normalize_github_url(source)
    if url is None:
        raise HTTPException(
            400, "Paste a public GitHub repo URL, like https://github.com/pallets/click")
    if not _ingest_lock.acquire(blocking=False):
        raise HTTPException(429, "Another repository is being indexed. Try again in a minute.")
    try:
        n = pipeline(user.id).ingest(url)
    except RepoTooLargeError as e:
        raise HTTPException(413, str(e))
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}")
    finally:
        _ingest_lock.release()
    return {"n_chunks": n, "index": read_index_meta(user.id)}


@app.post("/api/ask")
def ask(body: AskBody, user: models.User = Depends(auth.get_current_user)) -> dict:
    question = body.question.strip()
    if not question:
        raise HTTPException(400, "Question is required.")
    if read_index_meta(user.id) is None:
        raise HTTPException(409, "No repository indexed yet.")
    try:
        pipe = pipeline(user.id)
        ans = pipe.answer_agentic(question) if body.agentic else pipe.answer(question)
        
        db.chat_history.insert_one({
            "user_id": user.id,
            "question": question,
            "answer": ans.text,
            "sources": [s.chunk.citation() for s in ans.sources],
            "timestamp": datetime.utcnow()
        })
        
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}")
    return {
        "text": ans.text,
        "sources": [serialize(h) for h in ans.sources],
        "trace": ans.trace,
    }


_DIST = ROOT / "frontend" / "dist"
if _DIST.exists():
    _DIST_ROOT = _DIST.resolve()
    app.mount("/assets", StaticFiles(directory=str(_DIST / "assets")), name="assets")

    # Client-side routes (e.g. /login) must fall back to index.html on refresh.
    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(404, "Not Found")
        file = (_DIST_ROOT / full_path).resolve()
        if full_path and file.is_file() and _DIST_ROOT in file.parents:
            return FileResponse(file)
        return FileResponse(_DIST_ROOT / "index.html")
else:
    @app.get("/")
    def root() -> dict:
        return {"status": "ok", "docs": "/docs"}
