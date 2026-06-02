"""Quiz attempt repository — persists every quiz submission for analytics."""
import uuid
from datetime import datetime, timezone
from typing import List

from core.db import get_db
from models.chat import QuizAttemptRecord


def _to_rec(doc: dict) -> QuizAttemptRecord:
    doc.pop("_id", None)
    if isinstance(doc.get("created_at"), str):
        doc["created_at"] = datetime.fromisoformat(doc["created_at"])
    return QuizAttemptRecord(**doc)


class AttemptRepository:
    COLLECTION = "quiz_attempts"

    def __init__(self):
        self.col = get_db()[self.COLLECTION]

    async def ensure_indexes(self) -> None:
        await self.col.create_index([("user_id", 1), ("created_at", -1)])
        await self.col.create_index("lecture_id")

    async def add(self, rec: QuizAttemptRecord) -> QuizAttemptRecord:
        doc = rec.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        await self.col.insert_one(doc)
        return rec

    async def list_for_user(self, user_id: str) -> List[QuizAttemptRecord]:
        cursor = self.col.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1)
        return [_to_rec(d) async for d in cursor]

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())
