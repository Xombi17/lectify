"""Chat history repository — Mongo-backed."""
import uuid
from datetime import datetime
from typing import List

from core.db import get_db
from models.chat import ChatMessageDB


def _to_msg(doc: dict) -> ChatMessageDB:
    doc.pop("_id", None)
    if isinstance(doc.get("created_at"), str):
        doc["created_at"] = datetime.fromisoformat(doc["created_at"])
    return ChatMessageDB(**doc)


class ChatRepository:
    COLLECTION = "chat_messages"

    def __init__(self):
        self.col = get_db()[self.COLLECTION]

    async def ensure_indexes(self) -> None:
        await self.col.create_index([("lecture_id", 1), ("user_id", 1), ("created_at", 1)])

    async def add(self, msg: ChatMessageDB) -> ChatMessageDB:
        doc = msg.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        await self.col.insert_one(doc)
        return msg

    async def list_for(self, lecture_id: str, user_id: str, limit: int = 50) -> List[ChatMessageDB]:
        cursor = self.col.find(
            {"lecture_id": lecture_id, "user_id": user_id},
            {"_id": 0},
        ).sort("created_at", 1).limit(limit)
        return [_to_msg(d) async for d in cursor]

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())
