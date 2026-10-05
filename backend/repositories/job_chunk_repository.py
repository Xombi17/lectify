import logging
import uuid
from typing import List

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.sql_db import session_maker
from models.orm import JobChunkORM

logger = logging.getLogger(__name__)

class JobChunkRepository:
    async def ensure(self, lecture_id: str, version: int, count: int) -> None:
        """Idempotently create pending rows for all chunk indexes 0 to count-1."""
        async with session_maker()() as session:
            for i in range(count):
                row = JobChunkORM(
                    id=str(uuid.uuid4()),
                    lecture_id=lecture_id,
                    version=version,
                    chunk_index=i,
                    status="pending"
                )
                session.add(row)
                try:
                    await session.commit()
                except IntegrityError:
                    await session.rollback()

    async def mark_done(self, lecture_id: str, version: int, index: int, text: str) -> None:
        """Idempotent update to done."""
        async with session_maker()() as session:
            stmt = select(JobChunkORM).where(
                JobChunkORM.lecture_id == lecture_id,
                JobChunkORM.version == version,
                JobChunkORM.chunk_index == index
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row:
                if row.status != "done":
                    row.status = "done"
                    row.text = text
                    row.error = None
                    await session.commit()

    async def mark_failed(self, lecture_id: str, version: int, index: int, err: str) -> None:
        """Idempotent update to failed, incrementing attempts."""
        async with session_maker()() as session:
            stmt = select(JobChunkORM).where(
                JobChunkORM.lecture_id == lecture_id,
                JobChunkORM.version == version,
                JobChunkORM.chunk_index == index
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row:
                if row.status != "done":
                    row.status = "failed"
                    row.error = err
                    row.attempts += 1
                    await session.commit()

    async def pending(self, lecture_id: str, version: int) -> List[int]:
        """Return list of indexes that are not 'done'."""
        async with session_maker()() as session:
            stmt = select(JobChunkORM.chunk_index).where(
                JobChunkORM.lecture_id == lecture_id,
                JobChunkORM.version == version,
                JobChunkORM.status != "done"
            ).order_by(JobChunkORM.chunk_index)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def merged_text(self, lecture_id: str, version: int) -> str:
        """Return joined text of all 'done' chunks, ordered by index."""
        async with session_maker()() as session:
            stmt = select(JobChunkORM.text).where(
                JobChunkORM.lecture_id == lecture_id,
                JobChunkORM.version == version,
                JobChunkORM.status == "done"
            ).order_by(JobChunkORM.chunk_index)
            result = await session.execute(stmt)
            texts = result.scalars().all()
            return "\n\n".join(t for t in texts if t)
