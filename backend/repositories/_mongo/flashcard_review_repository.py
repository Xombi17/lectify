"""Flashcard review state repository — Mongo."""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from core.db import get_db
from models.bookmark import FlashcardReviewDB


def _to_rev(doc: dict) -> FlashcardReviewDB:
    doc.pop("_id", None)
    for f in ("due_at", "last_reviewed_at"):
        v = doc.get(f)
        if isinstance(v, str):
            doc[f] = datetime.fromisoformat(v)
    return FlashcardReviewDB(**doc)


class FlashcardReviewRepository:
    COLLECTION = "flashcard_reviews"

    def __init__(self):
        self.col = get_db()[self.COLLECTION]

    async def ensure_indexes(self) -> None:
        await self.col.create_index([("user_id", 1), ("due_at", 1)])
        await self.col.create_index(
            [("user_id", 1), ("lecture_id", 1), ("card_index", 1)],
            unique=True,
        )

    async def get(self, user_id: str, lecture_id: str, card_index: int) -> Optional[FlashcardReviewDB]:
        doc = await self.col.find_one(
            {"user_id": user_id, "lecture_id": lecture_id, "card_index": card_index},
            {"_id": 0},
        )
        return _to_rev(doc) if doc else None

    async def upsert(self, rev: FlashcardReviewDB) -> FlashcardReviewDB:
        doc = rev.model_dump()
        for f in ("due_at", "last_reviewed_at"):
            v = doc.get(f)
            if isinstance(v, datetime):
                doc[f] = v.isoformat()
        await self.col.update_one(
            {"user_id": rev.user_id, "lecture_id": rev.lecture_id, "card_index": rev.card_index},
            {"$set": doc},
            upsert=True,
        )
        return rev

    async def list_due_for_user(self, user_id: str, now: Optional[datetime] = None, limit: int = 100) -> List[FlashcardReviewDB]:
        now = now or datetime.now(timezone.utc)
        cursor = self.col.find(
            {"user_id": user_id, "due_at": {"$lte": now.isoformat()}},
            {"_id": 0},
        ).sort("due_at", 1).limit(limit)
        return [_to_rev(d) async for d in cursor]

    async def list_all_for_user(self, user_id: str) -> List[FlashcardReviewDB]:
        cursor = self.col.find({"user_id": user_id}, {"_id": 0})
        return [_to_rev(d) async for d in cursor]

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())
