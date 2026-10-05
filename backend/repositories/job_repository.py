"""Job repository for queue worker synchronization."""
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from core.sql_db import session_maker
from models.job import JobDB, JobStatus
from models.orm import JobORM


def now() -> datetime:
    """Injectable time source for testing."""
    return datetime.now(timezone.utc)


class JobRepository:
    def __init__(self, session_factory=None):
        self.session_factory = session_factory or session_maker()

    async def create_if_absent(
        self, lecture_id: str, stage: str, version: int = 1, priority_score: float = 0.0, max_attempts: int = 5
    ) -> tuple[JobDB, bool]:
        """Insert a job idempotently. Returns (Job, created_bool)."""
        job_id = str(uuid.uuid4())
        async with self.session_factory() as session:
            try:
                new_job = JobORM(
                    id=job_id,
                    lecture_id=lecture_id,
                    stage=stage,
                    version=version,
                    status="queued",
                    attempt=0,
                    max_attempts=max_attempts,
                    priority_score=priority_score,
                    created_at=now(),
                    updated_at=now(),
                )
                session.add(new_job)
                await session.commit()
                return JobDB.model_validate(new_job), True
            except IntegrityError:
                await session.rollback()
                stmt = select(JobORM).where(
                    JobORM.lecture_id == lecture_id, JobORM.stage == stage, JobORM.version == version
                )
                result = await session.execute(stmt)
                existing = result.scalar_one()
                return JobDB.model_validate(existing), False

    async def get(self, job_id: str) -> JobDB | None:
        async with self.session_factory() as session:
            stmt = select(JobORM).where(JobORM.id == job_id)
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()
            return JobDB.model_validate(job) if job else None

    async def claim(self, job_id: str, stale_after_s: int = 300) -> JobDB | None:
        """Atomically claim a job. Returns JobDB if won, None if lost/stale."""
        current_time = now()
        stale_cutoff = current_time - timedelta(seconds=stale_after_s)
        
        async with self.session_factory() as session:
            stmt = (
                update(JobORM)
                .where(
                    JobORM.id == job_id,
                    (JobORM.status.in_(["queued", "retrying"])) | 
                    ((JobORM.status == "processing") & (JobORM.updated_at < stale_cutoff))
                )
                .values(
                    status="processing",
                    attempt=JobORM.attempt + 1,
                    updated_at=current_time
                )
                .returning(JobORM)
            )
            
            result = await session.execute(stmt)
            claimed = result.scalar_one_or_none()
            if claimed:
                await session.commit()
                return JobDB.model_validate(claimed)
            else:
                await session.rollback()
                return None

    async def mark(self, job_id: str, status: JobStatus, error: str | None = None) -> None:
        if error:
            error = error[:500]
        async with self.session_factory() as session:
            stmt = (
                update(JobORM)
                .where(JobORM.id == job_id)
                .values(
                    status=status,
                    error_message=error,
                    updated_at=now()
                )
            )
            await session.execute(stmt)
            await session.commit()
