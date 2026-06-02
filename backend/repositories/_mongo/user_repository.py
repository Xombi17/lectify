"""User repository — Mongo-backed implementation.

Swap this single file with a Postgres impl when self-hosting; routes/services
never import a Mongo driver directly.
"""
import uuid
from typing import Optional

from core.db import get_db
from models.user import UserDB


def _to_user(doc: dict) -> UserDB:
    doc.pop("_id", None)
    if isinstance(doc.get("created_at"), str):
        from datetime import datetime
        doc["created_at"] = datetime.fromisoformat(doc["created_at"])
    return UserDB(**doc)


class UserRepository:
    COLLECTION = "users"

    def __init__(self):
        self.db = get_db()
        self.col = self.db[self.COLLECTION]

    async def ensure_indexes(self) -> None:
        await self.col.create_index("email", unique=True)

    async def create(self, user: UserDB) -> UserDB:
        doc = user.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        await self.col.insert_one(doc)
        return user

    async def get_by_id(self, user_id: str) -> Optional[UserDB]:
        doc = await self.col.find_one({"id": user_id}, {"_id": 0})
        return _to_user(doc) if doc else None

    async def get_by_email(self, email: str) -> Optional[UserDB]:
        doc = await self.col.find_one({"email": email.lower()}, {"_id": 0})
        return _to_user(doc) if doc else None

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())
