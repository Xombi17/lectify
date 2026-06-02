"""Bookmark repository — Mongo-backed implementation."""
import uuid
from datetime import datetime
from typing import List, Optional

from core.db import get_db
from models.bookmark import BookmarkDB


def _to_bm(doc: dict) -> BookmarkDB:
    doc.pop("_id", None)
    if isinstance(doc.get("created_at"), str):
        doc["created_at"] = datetime.fromisoformat(doc["created_at"])
    return BookmarkDB(**doc)


class BookmarkRepository:
    COLLECTION = "bookmarks"

    def __init__(self):
        self.col = get_db()[self.COLLECTION]

    async def ensure_indexes(self) -> None:
        await self.col.create_index([("user_id", 1), ("created_at", -1)])
        await self.col.create_index([("user_id", 1), ("lecture_id", 1), ("kind", 1), ("ref_index", 1)])

    async def add(self, bm: BookmarkDB) -> BookmarkDB:
        doc = bm.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        await self.col.insert_one(doc)
        return bm

    async def find_existing(self, user_id: str, lecture_id: str, kind: str, ref_index: Optional[int]) -> Optional[BookmarkDB]:
        q = {"user_id": user_id, "lecture_id": lecture_id, "kind": kind, "ref_index": ref_index}
        doc = await self.col.find_one(q, {"_id": 0})
        return _to_bm(doc) if doc else None

    async def list_for_user(self, user_id: str) -> List[BookmarkDB]:
        cursor = self.col.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1)
        return [_to_bm(d) async for d in cursor]

    async def list_for_user_lecture(self, user_id: str, lecture_id: str) -> List[BookmarkDB]:
        cursor = self.col.find({"user_id": user_id, "lecture_id": lecture_id}, {"_id": 0})
        return [_to_bm(d) async for d in cursor]

    async def delete(self, bookmark_id: str, user_id: str) -> bool:
        res = await self.col.delete_one({"id": bookmark_id, "user_id": user_id})
        return res.deleted_count > 0

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())
