"""Quiz attempt repository — SQLAlchemy (async) implementation."""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select

from core.sql_db import session_maker
from models.chat import QuizAnswer, QuizAttemptRecord, QuizQuestionV2
from models.orm import QuizAttemptORM


def _to_rec(row: QuizAttemptORM) -> QuizAttemptRecord:
    qdata = row.question_data or {}
    questions_raw = qdata.get("questions", [])
    answers_raw = qdata.get("answers", [])
    return QuizAttemptRecord(
        id=row.id,
        lecture_id=row.lecture_id,
        user_id=row.user_id,
        score=row.score,
        total=row.total,
        percentage=row.percentage,
        questions=[QuizQuestionV2(**q) for q in questions_raw],
        answers=[QuizAnswer(**a) for a in answers_raw],
        topic_scores=qdata.get("topic_scores", {}),
        created_at=row.created_at,
    )


class AttemptRepository:
    async def ensure_indexes(self) -> None:
        return None

    async def add(self, rec: QuizAttemptRecord) -> QuizAttemptRecord:
        qdata = {
            "questions": [q.model_dump() for q in rec.questions],
            "answers": [a.model_dump() for a in rec.answers],
            "topic_scores": rec.topic_scores,
        }
        async with session_maker()() as s, s.begin():
            s.add(QuizAttemptORM(
                id=rec.id,
                lecture_id=rec.lecture_id,
                user_id=rec.user_id,
                score=rec.score,
                total=rec.total,
                percentage=rec.percentage,
                question_data=qdata,
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

    async def get_for_user_and_lecture(self, user_id: str, lecture_id: str) -> List[QuizAttemptRecord]:
        """Get all quiz attempts for a specific user + lecture."""
        async with session_maker()() as s:
            stmt = (
                select(QuizAttemptORM)
                .where(QuizAttemptORM.user_id == user_id)
                .where(QuizAttemptORM.lecture_id == lecture_id)
                .order_by(QuizAttemptORM.created_at.desc())
            )
            rows = (await s.execute(stmt)).scalars().all()
            return [_to_rec(r) for r in rows]

    async def get_recent_for_user(self, user_id: str, limit: int = 5) -> List[QuizAttemptRecord]:
        """Get the most recent N quiz attempts for a user."""
        async with session_maker()() as s:
            stmt = (
                select(QuizAttemptORM)
                .where(QuizAttemptORM.user_id == user_id)
                .order_by(QuizAttemptORM.created_at.desc())
                .limit(limit)
            )
            rows = (await s.execute(stmt)).scalars().all()
            return [_to_rec(r) for r in rows]

    async def get_for_user_since(self, user_id: str, since: datetime) -> List[QuizAttemptRecord]:
        """Get quiz attempts for a user since a given datetime."""
        async with session_maker()() as s:
            stmt = (
                select(QuizAttemptORM)
                .where(QuizAttemptORM.user_id == user_id)
                .where(QuizAttemptORM.created_at >= since)
                .order_by(QuizAttemptORM.created_at.desc())
            )
            rows = (await s.execute(stmt)).scalars().all()
            return [_to_rec(r) for r in rows]

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())
