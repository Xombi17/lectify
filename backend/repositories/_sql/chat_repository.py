"""Chat repository — SQLAlchemy (async) implementation."""
import uuid
from typing import List

from sqlalchemy import select

from core.sql_db import session_maker
from models.chat import ChatMessageDB
from models.orm import ChatMessageORM


def _to_msg(row: ChatMessageORM) -> ChatMessageDB:
    return ChatMessageDB(
        id=row.id,
        lecture_id=row.lecture_id,
        user_id=row.user_id,
        role=row.role,
        content=row.content,
        created_at=row.created_at,
    )


class ChatRepository:
    async def ensure_indexes(self) -> None:
        return None

    async def add(self, msg: ChatMessageDB) -> ChatMessageDB:
        async with session_maker()() as s, s.begin():
            s.add(ChatMessageORM(
                id=msg.id,
                lecture_id=msg.lecture_id,
                user_id=msg.user_id,
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at,
            ))
        return msg

    async def list_for(self, lecture_id: str, user_id: str, limit: int = 50) -> List[ChatMessageDB]:
        async with session_maker()() as s:
            stmt = (
                select(ChatMessageORM)
                .where(
                    (ChatMessageORM.lecture_id == lecture_id)
                    & (ChatMessageORM.user_id == user_id)
                )
                .order_by(ChatMessageORM.created_at.asc())
                .limit(limit)
            )
            rows = (await s.execute(stmt)).scalars().all()
            return [_to_msg(r) for r in rows]

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())
