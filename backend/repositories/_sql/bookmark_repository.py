"""Bookmark repository — SQL (SQLAlchemy async) implementation."""
import uuid
from typing import List, Optional

from sqlalchemy import select

from core.sql_db import session_maker
from models.bookmark import BookmarkDB
from models.orm import BookmarkORM


def _to_bm(row: BookmarkORM) -> BookmarkDB:
    return BookmarkDB(
        id=row.id,
        user_id=row.user_id,
        lecture_id=row.lecture_id,
        kind=row.kind,
        text=row.text,
        ref_index=row.ref_index,
        created_at=row.created_at,
    )


class BookmarkRepository:
    async def ensure_indexes(self) -> None:
        return None  # ORM indexes do it

    async def add(self, bm: BookmarkDB) -> BookmarkDB:
        async with session_maker()() as s, s.begin():
            s.add(BookmarkORM(
                id=bm.id,
                user_id=bm.user_id,
                lecture_id=bm.lecture_id,
                kind=bm.kind,
                text=bm.text,
                ref_index=bm.ref_index,
                created_at=bm.created_at,
            ))
        return bm

    async def find_existing(self, user_id: str, lecture_id: str, kind: str, ref_index: Optional[int]) -> Optional[BookmarkDB]:
        async with session_maker()() as s:
            stmt = select(BookmarkORM).where(
                (BookmarkORM.user_id == user_id)
                & (BookmarkORM.lecture_id == lecture_id)
                & (BookmarkORM.kind == kind)
                & (BookmarkORM.ref_index.is_(ref_index) if ref_index is None else BookmarkORM.ref_index == ref_index)
            )
            row = (await s.execute(stmt)).scalar_one_or_none()
            return _to_bm(row) if row else None

    async def list_for_user(self, user_id: str) -> List[BookmarkDB]:
        async with session_maker()() as s:
            stmt = select(BookmarkORM).where(BookmarkORM.user_id == user_id).order_by(BookmarkORM.created_at.desc())
            rows = (await s.execute(stmt)).scalars().all()
            return [_to_bm(r) for r in rows]

    async def list_for_user_lecture(self, user_id: str, lecture_id: str) -> List[BookmarkDB]:
        async with session_maker()() as s:
            stmt = select(BookmarkORM).where(
                (BookmarkORM.user_id == user_id) & (BookmarkORM.lecture_id == lecture_id)
            )
            rows = (await s.execute(stmt)).scalars().all()
            return [_to_bm(r) for r in rows]

    async def delete(self, bookmark_id: str, user_id: str) -> bool:
        async with session_maker()() as s, s.begin():
            row = await s.get(BookmarkORM, bookmark_id)
            if row and row.user_id == user_id:
                await s.delete(row)
                return True
            return False

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())
