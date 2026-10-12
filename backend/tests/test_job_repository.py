"""Tests for JobRepository idempotency and atomic claim."""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from models.orm import JobORM, LectureORM, UserORM, Base
from repositories.job_repository import JobRepository
from core.sql_db import _engine as get_engine
from core.sql_db import session_maker

pytestmark = pytest.mark.asyncio



async def test_create_if_absent():
    repo = JobRepository()
    
    job1, created1 = await repo.create_if_absent("l1", "transcribe", version=1)
    assert created1 is True
    assert job1.lecture_id == "l1"
    
    job2, created2 = await repo.create_if_absent("l1", "transcribe", version=1)
    assert created2 is False
    assert job1.id == job2.id
    
    job3, created3 = await repo.create_if_absent("l1", "embed", version=1)
    assert created3 is True
    assert job1.id != job3.id

async def test_atomic_claim_and_mark(monkeypatch):
    repo = JobRepository()
    
    job, _ = await repo.create_if_absent("l1", "transcribe")
    
    claimed = await repo.claim(job.id)
    assert claimed is not None
    assert claimed.status == "processing"
    assert claimed.attempt == 1
    
    # Second claim fails
    claimed2 = await repo.claim(job.id)
    assert claimed2 is None
    
    # Mark as completed
    await repo.mark(job.id, "completed")
    
    job_db = await repo.get(job.id)
    assert job_db.status == "completed"

async def test_stale_claim(monkeypatch):
    import repositories.job_repository as jr
    repo = JobRepository()
    
    job, _ = await repo.create_if_absent("l1", "transcribe")
    claimed = await repo.claim(job.id)
    
    # fast forward time
    future = datetime.now(timezone.utc) + timedelta(seconds=400)
    monkeypatch.setattr(jr, "now", lambda: future)
    
    claimed2 = await repo.claim(job.id, stale_after_s=300)
    assert claimed2 is not None
    assert claimed2.attempt == 2

async def test_concurrent_claims():
    repo = JobRepository()
    job, _ = await repo.create_if_absent("l1", "transcribe")
    
    results = await asyncio.gather(*[repo.claim(job.id) for _ in range(5)])
    successes = [r for r in results if r is not None]
    assert len(successes) == 1


async def test_span_seconds():
    repo = JobRepository()
    assert await repo.span_seconds("nojobs") is None
    j1, _ = await repo.create_if_absent("lspan", "transcribe")
    j2, _ = await repo.create_if_absent("lspan", "embed")
    t0 = datetime.now(timezone.utc)
    async with session_maker()() as s:
        await s.execute(text("UPDATE jobs SET created_at=:c, updated_at=:c"), {"c": t0})
        await s.execute(text("UPDATE jobs SET updated_at=:u WHERE id=:i"), {"u": t0 + timedelta(seconds=12.5), "i": j2.id})
        await s.commit()
    assert await repo.span_seconds("lspan") == pytest.approx(12.5, abs=0.1)
