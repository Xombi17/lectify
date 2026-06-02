"""Quiz attempt repository — SQLAlchemy (async) implementation."""
import uuid
from typing import List

from sqlalchemy import select

from core.sql_db import session_maker
from models.chat import QuizAttemptRecord
from models.orm import QuizAttemptORM


def _to_rec(row: QuizAttemptORM) -> QuizAttemptRecord:
    return QuizAttemptRecord(
        id=row.id,
        lecture_id=row.lecture_id,
        user_id=row.user_id,
        score=row.score,
        total=row.total,
        percentage=row.percentage,
        created_at=row.created_at,
    )


class AttemptRepository:
    async def ensure_indexes(self) -> None:
        return None

    async def add(self, rec: QuizAttemptRecord) -> QuizAttemptRecord:
        async with session_maker()() as s, s.begin():
            s.add(QuizAttemptORM(
                id=rec.id,
                lecture_id=rec.lecture_id,
                user_id=rec.user_id,
                score=rec.score,
                total=rec.total,
                percentage=rec.percentage,
                created_at=rec.created_at,
            ))
        return rec

    async def list_for_user(self, user_id: str) -> List[QuizAttemptRecord]:
        async with session_maker()() as s:
            stmt = (
                select(QuizAttemptORM)
                .where(QuizAttemptORM.user_id == user_id)
                .order_by(QuizAttemptORM.created_at.desc())
            )
            rows = (await s.execute(stmt)).scalars().all()
            return [_to_rec(r) for r in rows]

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())
