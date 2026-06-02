"""Flashcard review repository — SQL (SQLAlchemy async) implementation."""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert

from core.sql_db import session_maker
from models.bookmark import FlashcardReviewDB
from models.orm import FlashcardReviewORM


def _to_rev(row: FlashcardReviewORM) -> FlashcardReviewDB:
    return FlashcardReviewDB(
        id=row.id,
        user_id=row.user_id,
        lecture_id=row.lecture_id,
        card_index=row.card_index,
        ease_factor=row.ease_factor,
        interval_days=row.interval_days,
        repetitions=row.repetitions,
        last_reviewed_at=row.last_reviewed_at,
        due_at=row.due_at,
        total_reviews=row.total_reviews,
    )


class FlashcardReviewRepository:
    async def ensure_indexes(self) -> None:
        return None

    async def get(self, user_id: str, lecture_id: str, card_index: int) -> Optional[FlashcardReviewDB]:
        async with session_maker()() as s:
            stmt = select(FlashcardReviewORM).where(
                (FlashcardReviewORM.user_id == user_id)
                & (FlashcardReviewORM.lecture_id == lecture_id)
                & (FlashcardReviewORM.card_index == card_index)
            )
            row = (await s.execute(stmt)).scalar_one_or_none()
            return _to_rev(row) if row else None

    async def upsert(self, rev: FlashcardReviewDB) -> FlashcardReviewDB:
        async with session_maker()() as s, s.begin():
            existing = (await s.execute(
                select(FlashcardReviewORM).where(
                    (FlashcardReviewORM.user_id == rev.user_id)
                    & (FlashcardReviewORM.lecture_id == rev.lecture_id)
                    & (FlashcardReviewORM.card_index == rev.card_index)
                )
            )).scalar_one_or_none()
            if existing:
                existing.ease_factor = rev.ease_factor
                existing.interval_days = rev.interval_days
                existing.repetitions = rev.repetitions
                existing.last_reviewed_at = rev.last_reviewed_at
                existing.due_at = rev.due_at
                existing.total_reviews = rev.total_reviews
            else:
                s.add(FlashcardReviewORM(
                    id=rev.id,
                    user_id=rev.user_id,
                    lecture_id=rev.lecture_id,
                    card_index=rev.card_index,
                    ease_factor=rev.ease_factor,
                    interval_days=rev.interval_days,
                    repetitions=rev.repetitions,
                    last_reviewed_at=rev.last_reviewed_at,
                    due_at=rev.due_at,
                    total_reviews=rev.total_reviews,
                ))
        return rev

    async def list_due_for_user(self, user_id: str, now: Optional[datetime] = None, limit: int = 100) -> List[FlashcardReviewDB]:
        now = now or datetime.now(timezone.utc)
        async with session_maker()() as s:
            stmt = (
                select(FlashcardReviewORM)
                .where((FlashcardReviewORM.user_id == user_id) & (FlashcardReviewORM.due_at <= now))
                .order_by(FlashcardReviewORM.due_at.asc())
                .limit(limit)
            )
            rows = (await s.execute(stmt)).scalars().all()
            return [_to_rev(r) for r in rows]

    async def list_all_for_user(self, user_id: str) -> List[FlashcardReviewDB]:
        async with session_maker()() as s:
            stmt = select(FlashcardReviewORM).where(FlashcardReviewORM.user_id == user_id)
            rows = (await s.execute(stmt)).scalars().all()
            return [_to_rev(r) for r in rows]

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())
