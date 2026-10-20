"""Which repo each user has indexed.

Stored in MongoDB when MONGO_URI is set (the server's disk is wiped on restart on
free hosts), otherwise in data/index_<user>.json for local CLI runs.
"""
from __future__ import annotations

import json
import os
from functools import lru_cache

from config import INDEX_META_DIR


@lru_cache(maxsize=1)
def _collection():
    uri = os.environ.get("MONGO_URI", "")
    if not uri:
        return None
    from pymongo import MongoClient

    client = MongoClient(uri, serverSelectionTimeoutMS=10_000)
    return client.get_database("reposage").index_meta


def _path(user_id):
    return INDEX_META_DIR / f"index_{user_id}.json"


def read_index_meta(user_id) -> dict | None:
    col = _collection()
    if col is not None:
        doc = col.find_one({"_id": str(user_id)}, {"_id": 0})
        return doc or None
    path = _path(user_id)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return None


def write_index_meta(user_id, meta: dict) -> None:
    col = _collection()
    if col is not None:
        col.replace_one({"_id": str(user_id)}, dict(meta), upsert=True)
        return
    path = _path(user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)


def delete_index_meta(user_id) -> None:
    col = _collection()
    if col is not None:
        col.delete_one({"_id": str(user_id)})
        return
    _path(user_id).unlink(missing_ok=True)
