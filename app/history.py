"""Per-user chats, repository history and profile, stored in MongoDB.

Nothing here is kept in the server's memory: every request reads what it needs
from MongoDB, so chat history doesn't count against the 512 MB limit.
"""
from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from pymongo import ASCENDING, DESCENDING

from app import auth, models
from app.database import db

router = APIRouter(prefix="/api", tags=["history"])

TITLE_MAX = 60
CHATS_LIMIT = 100
HISTORY_TURNS = 6  # earlier messages sent to the LLM for follow-up questions


def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def ensure_indexes() -> None:
    db.conversations.create_index([("user_id", ASCENDING), ("updated_at", DESCENDING)])
    db.messages.create_index([("conversation_id", ASCENDING), ("created_at", ASCENDING)])
    db.repos.create_index([("user_id", ASCENDING), ("source", ASCENDING)], unique=True)


def make_title(question: str) -> str:
    title = " ".join(question.split())
    return title if len(title) <= TITLE_MAX else title[: TITLE_MAX - 1].rstrip() + "…"


def _oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise HTTPException(404, "Chat not found.")


def get_owned_chat(chat_id: str, user_id: str) -> dict:
    chat = db.conversations.find_one({"_id": _oid(chat_id), "user_id": str(user_id)})
    if chat is None:
        raise HTTPException(404, "Chat not found.")
    return chat


def chat_summary(c: dict) -> dict:
    return {
        "id": str(c["_id"]),
        "title": c.get("title") or "New chat",
        "repo": c.get("repo"),
        "created_at": iso(c.get("created_at")),
        "updated_at": iso(c.get("updated_at")),
    }


def message_out(m: dict) -> dict:
    return {
        "id": str(m["_id"]),
        "role": m["role"],
        "content": m.get("content", ""),
        "sources": m.get("sources") or [],
        "trace": m.get("trace"),
        "created_at": iso(m.get("created_at")),
    }


def recent_history(chat_id: ObjectId) -> list[dict]:
    """Last few messages of a chat, oldest first, for follow-up context."""
    docs = list(db.messages.find({"conversation_id": chat_id}, {"role": 1, "content": 1})
                .sort("created_at", DESCENDING).limit(HISTORY_TURNS))
    return [{"role": d["role"], "content": d.get("content", "")} for d in reversed(docs)]


def save_exchange(user_id: str, chat: dict | None, question: str, repo: str | None,
                  answer: dict) -> dict:
    """Store one question + answer. Creates the chat on its first message."""
    ts = now()
    if chat is None:
        chat = {"user_id": str(user_id), "title": make_title(question), "repo": repo,
                "created_at": ts, "updated_at": ts}
        chat["_id"] = db.conversations.insert_one(chat).inserted_id
    else:
        db.conversations.update_one({"_id": chat["_id"]},
                                    {"$set": {"updated_at": ts, "repo": chat.get("repo") or repo}})
    db.messages.insert_many([
        {"conversation_id": chat["_id"], "user_id": str(user_id), "role": "user",
         "content": question, "created_at": ts},
        {"conversation_id": chat["_id"], "user_id": str(user_id), "role": "assistant",
         "content": answer["text"], "sources": answer["sources"], "trace": answer.get("trace"),
         # a hair later so the order is stable when sorting by time
         "created_at": ts.replace(microsecond=min(ts.microsecond + 1, 999_999))},
    ])
    return chat


def remember_repo(user_id: str, meta: dict) -> None:
    db.repos.update_one(
        {"user_id": str(user_id), "source": meta["source"]},
        {"$set": {"n_files": meta.get("n_files"), "n_chunks": meta.get("n_chunks"),
                  "last_indexed_at": now()},
         "$setOnInsert": {"first_indexed_at": now()}},
        upsert=True,
    )


# ---------------------------------------------------------------- routes

@router.get("/me")
def me(user: models.User = Depends(auth.get_current_user)) -> dict:
    doc = db.users.find_one({"_id": ObjectId(user.id)}, {"created_at": 1}) or {}
    created = doc.get("created_at") or ObjectId(user.id).generation_time
    return {
        "email": user.email,
        "name": user.email.split("@")[0],
        "member_since": iso(created),
        "n_chats": db.conversations.count_documents({"user_id": user.id}),
        "n_repos": db.repos.count_documents({"user_id": user.id}),
    }


@router.get("/chats")
def list_chats(user: models.User = Depends(auth.get_current_user)) -> list[dict]:
    cur = (db.conversations.find({"user_id": user.id})
           .sort("updated_at", DESCENDING).limit(CHATS_LIMIT))
    return [chat_summary(c) for c in cur]


@router.get("/chats/{chat_id}")
def get_chat(chat_id: str, user: models.User = Depends(auth.get_current_user)) -> dict:
    chat = get_owned_chat(chat_id, user.id)
    msgs = db.messages.find({"conversation_id": chat["_id"]}).sort("created_at", ASCENDING)
    return {**chat_summary(chat), "messages": [message_out(m) for m in msgs]}


class RenameBody(BaseModel):
    title: str


@router.patch("/chats/{chat_id}")
def rename_chat(chat_id: str, body: RenameBody,
                user: models.User = Depends(auth.get_current_user)) -> dict:
    chat = get_owned_chat(chat_id, user.id)
    title = make_title(body.title)
    if not title:
        raise HTTPException(400, "Title can't be empty.")
    db.conversations.update_one({"_id": chat["_id"]}, {"$set": {"title": title}})
    return {**chat_summary(chat), "title": title}


@router.delete("/chats/{chat_id}")
def delete_chat(chat_id: str, user: models.User = Depends(auth.get_current_user)) -> dict:
    chat = get_owned_chat(chat_id, user.id)
    db.messages.delete_many({"conversation_id": chat["_id"]})
    db.conversations.delete_one({"_id": chat["_id"]})
    return {"deleted": True}


@router.get("/repos")
def list_repos(user: models.User = Depends(auth.get_current_user)) -> list[dict]:
    cur = db.repos.find({"user_id": user.id}).sort("last_indexed_at", DESCENDING).limit(50)
    return [{"source": r["source"], "n_files": r.get("n_files"), "n_chunks": r.get("n_chunks"),
             "last_indexed_at": iso(r.get("last_indexed_at"))} for r in cur]


class RepoBody(BaseModel):
    source: str


@router.post("/repos/forget")
def forget_repo(body: RepoBody, user: models.User = Depends(auth.get_current_user)) -> dict:
    db.repos.delete_one({"user_id": user.id, "source": body.source})
    return {"deleted": True}
