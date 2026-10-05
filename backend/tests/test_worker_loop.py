"""Tests for the SQS-style worker poll/claim/commit/enqueue/delete loop."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from core.queue_backend import get_queue_backend
from models.job import JobCreate, JobDB
from repositories.job_repository import JobRepository
from repositories.lecture_repository import LectureRepository
from services.queue_client import enqueue_job
from workers.base import BaseWorker, JobContext

pytestmark = pytest.mark.asyncio


class RecordingWorker(BaseWorker):
    stage = "transcribe"
    queue_name = "transcribe"
    visibility_timeout = 300

    def __init__(self):
        super().__init__()
        self.calls = []
        self.raise_on_process = None

    async def process_job(self, job: JobDB, ctx: JobContext) -> list[JobCreate]:
        self.calls.append("process")
        if self.raise_on_process:
            raise self.raise_on_process
        return [
            JobCreate(
                lecture_id=job.lecture_id,
                stage="generate_materials",
                version=job.version,
            )
        ]


class MaterialsRecorder(BaseWorker):
    stage = "generate_materials"
    queue_name = "generate_materials"
    visibility_timeout = 300

    def __init__(self):
        super().__init__()
        self.calls = []

    async def process_job(self, job: JobDB, ctx: JobContext) -> list[JobCreate]:
        self.calls.append("process_materials")
        return []


class _Crash(BaseException):
    pass


async def test_run_once_happy_path_ordering(monkeypatch):
    """enqueue + run_once → process_job called once, job completed, next-stage job enqueued, original message deleted; recorded call order is [claim, process, mark_completed, enqueue_next, delete]"""
    backend = get_queue_backend()
    repo = JobRepository()

    worker = RecordingWorker()

    original_delete = backend.delete

    async def fake_delete(q, r):
        worker.calls.append("delete")
        await original_delete(q, r)

    monkeypatch.setattr(backend, "delete", fake_delete)

    original_claim = JobRepository.claim

    async def fake_claim(self, job_id, stale_after_s=300):
        worker.calls.append("claim")
        return await original_claim(self, job_id, stale_after_s=stale_after_s)

    monkeypatch.setattr(JobRepository, "claim", fake_claim)

    original_mark = JobRepository.mark

    async def fake_mark(self, job_id, status, error=None):
        worker.calls.append(f"mark_{status}")
        return await original_mark(self, job_id, status, error)

    monkeypatch.setattr(JobRepository, "mark", fake_mark)

    import services.queue_client as qc

    original_enqueue = qc.enqueue_job

    async def fake_enqueue(job, **kwargs):
        worker.calls.append("enqueue_next")
        return await original_enqueue(job, **kwargs)

    monkeypatch.setattr(qc, "enqueue_job", fake_enqueue)

    await enqueue_job(JobCreate(lecture_id="l1", stage="transcribe", version=1))

    handled = await worker.run_once(wait_seconds=0)
    assert handled is True

    assert worker.calls == [
        "claim",
        "process",
        "enqueue_next",
        "mark_completed",
        "delete",
    ]


async def test_duplicate_delivery(monkeypatch):
    backend = get_queue_backend()
    repo = JobRepository()
    worker = RecordingWorker()

    job = await enqueue_job(JobCreate(lecture_id="l1", stage="transcribe", version=1))

    handled = await worker.run_once(wait_seconds=0)
    assert handled is True
    assert worker.calls == ["process"]

    # manually send a message for the completed job (simulating broker duplicate delivery)
    await backend.send(
        "transcribe",
        {"job_id": job.id, "lecture_id": "l1", "stage": "transcribe", "version": 1},
    )

    worker.calls.clear()
    handled = await worker.run_once(wait_seconds=0)
    assert handled is True
    assert worker.calls == []
    assert await backend.depth("transcribe") == 0


async def test_crash_simulation_window_a(monkeypatch):
    """Window A: crash inside enqueue_job on backend.send."""
    import time
    from datetime import datetime, timedelta, timezone

    import repositories.job_repository as jr
    from core.sql_db import session_maker
    from models.orm import JobORM
    from sqlalchemy import select

    backend = get_queue_backend()
    worker = RecordingWorker()

    original_send = backend.send
    crashed = False

    async def send_crash(queue, body):
        nonlocal crashed
        if queue == "generate_materials" and not crashed:
            crashed = True
            raise _Crash("Crash inside enqueue_job backend.send")
        return await original_send(queue, body)

    monkeypatch.setattr(backend, "send", send_crash)

    job = await enqueue_job(JobCreate(lecture_id="l1", stage="transcribe", version=1))

    with pytest.raises(_Crash):
        await worker.run_once(wait_seconds=0)

    # Force redelivery
    for q in backend._queues.values():
        for m in q:
            m["visible_at"] = time.monotonic() - 1

    future = datetime.now(timezone.utc) + timedelta(
        seconds=worker.visibility_timeout + 1
    )
    monkeypatch.setattr(jr, "now", lambda: future)

    handled = await worker.run_once(wait_seconds=0)
    assert handled is True

    repo = JobRepository()
    transcribe_job = await repo.get(job.id)
    assert transcribe_job.status == "completed"
    assert await backend.depth("transcribe") == 0

    async with session_maker()() as session:
        result = await session.execute(
            select(JobORM).where(
                JobORM.lecture_id == "l1",
                JobORM.stage == "generate_materials",
                JobORM.version == 1,
            )
        )
        rows = result.scalars().all()
        assert len(rows) == 1

    assert await backend.depth("generate_materials") == 1


async def test_crash_simulation_window_b(monkeypatch):
    """Window B: crash after enqueue before completion mark."""
    import time
    from datetime import datetime, timedelta, timezone

    import repositories.job_repository as jr
    from core.sql_db import session_maker
    from models.orm import JobORM
    from sqlalchemy import select

    backend = get_queue_backend()
    worker = RecordingWorker()

    original_mark = JobRepository.mark
    crashed = False

    async def mark_crash(self, job_id, status, error=None):
        nonlocal crashed
        if status == "completed" and not crashed:
            crashed = True
            raise _Crash("Crash on mark completed")
        return await original_mark(self, job_id, status, error)

    monkeypatch.setattr(JobRepository, "mark", mark_crash)

    await enqueue_job(JobCreate(lecture_id="l1", stage="transcribe", version=1))

    with pytest.raises(_Crash):
        await worker.run_once(wait_seconds=0)

    # Force redelivery
    for q in backend._queues.values():
        for m in q:
            m["visible_at"] = time.monotonic() - 1

    future = datetime.now(timezone.utc) + timedelta(
        seconds=worker.visibility_timeout + 1
    )
    monkeypatch.setattr(jr, "now", lambda: future)

    handled = await worker.run_once(wait_seconds=0)
    assert handled is True

    async with session_maker()() as session:
        result = await session.execute(
            select(JobORM).where(
                JobORM.lecture_id == "l1",
                JobORM.stage == "generate_materials",
                JobORM.version == 1,
            )
        )
        rows = result.scalars().all()
        assert len(rows) == 1

    # Drain with MaterialsRecorder
    mat_worker = MaterialsRecorder()
    while await backend.depth("generate_materials") > 0:
        mat_handled = await mat_worker.run_once(wait_seconds=0)
        assert mat_handled is True
    assert mat_worker.calls == ["process_materials"]
    assert await backend.depth("generate_materials") == 0


async def test_crash_simulation_window_c(monkeypatch):
    """Window C: crash after mark completed before delete."""
    import time
    from datetime import datetime, timedelta, timezone

    import repositories.job_repository as jr
    from core.sql_db import session_maker
    from models.orm import JobORM
    from sqlalchemy import select

    backend = get_queue_backend()
    worker = RecordingWorker()

    original_delete = backend.delete
    crashed = False

    async def delete_crash(queue, receipt):
        nonlocal crashed
        if queue == "transcribe" and not crashed:
            crashed = True
            raise _Crash("Crash on delete")
        return await original_delete(queue, receipt)

    monkeypatch.setattr(backend, "delete", delete_crash)

    await enqueue_job(JobCreate(lecture_id="l1", stage="transcribe", version=1))

    with pytest.raises(_Crash):
        await worker.run_once(wait_seconds=0)

    # Force redelivery
    for q in backend._queues.values():
        for m in q:
            m["visible_at"] = time.monotonic() - 1

    future = datetime.now(timezone.utc) + timedelta(
        seconds=worker.visibility_timeout + 1
    )
    monkeypatch.setattr(jr, "now", lambda: future)

    handled = await worker.run_once(wait_seconds=0)
    assert handled is True

    # Total process_job calls across both runs should be exactly 1
    assert worker.calls == ["process"]
    assert await backend.depth("transcribe") == 0
    assert await backend.depth("generate_materials") == 1

    async with session_maker()() as session:
        result = await session.execute(
            select(JobORM).where(
                JobORM.lecture_id == "l1",
                JobORM.stage == "generate_materials",
                JobORM.version == 1,
            )
        )
        rows = result.scalars().all()
        assert len(rows) == 1


async def test_crash_simulation_window_d(monkeypatch):
    """Window D: ordinary RuntimeError from delete after completion does not downgrade job."""
    backend = get_queue_backend()
    repo = JobRepository()
    worker = RecordingWorker()

    async def delete_error(queue, receipt):
        raise RuntimeError("Transient broker error on delete")

    monkeypatch.setattr(backend, "delete", delete_error)

    job = await enqueue_job(JobCreate(lecture_id="l1", stage="transcribe", version=1))

    handled = await worker.run_once(wait_seconds=0)
    assert handled is True

    job_db = await repo.get(job.id)
    assert job_db.status == "completed"

    lec_repo = LectureRepository()
    lecture = await lec_repo.get_by_id("l1")
    assert lecture.status != "retrying"


async def test_failure_path_backoff():
    backend = get_queue_backend()
    repo = JobRepository()
    worker = RecordingWorker()
    worker.raise_on_process = ValueError("Something failed")

    job = await enqueue_job(JobCreate(lecture_id="l1", stage="transcribe", version=1))

    handled = await worker.run_once(wait_seconds=0)
    assert handled is True

    job_db = await repo.get(job.id)
    assert job_db.status == "retrying"

    q = backend._queues.get("transcribe", [])
    assert len(q) == 1
    assert q[0]["receive_count"] == 1

    import time

    q[0]["visible_at"] = time.monotonic() - 1

    handled = await worker.run_once(wait_seconds=0)
    assert q[0]["receive_count"] == 2
    job_db = await repo.get(job.id)
    assert job_db.status == "retrying"


async def test_dead_letter():
    backend = get_queue_backend()
    repo = JobRepository()
    worker = RecordingWorker()
    worker.raise_on_process = ValueError("Terminal failure")

    job = await enqueue_job(JobCreate(lecture_id="l1", stage="transcribe", version=1))

    q = backend._queues.get("transcribe", [])
    q[0]["receive_count"] = 4

    handled = await worker.run_once(wait_seconds=0)
    assert handled is True

    job_db = await repo.get(job.id)
    assert job_db.status == "dead_letter"
    assert "Terminal failure" in job_db.error_message

    lec_repo = LectureRepository()
    lec = await lec_repo.get_by_id(job.lecture_id)
    assert lec.status == "dead_letter"


async def test_heartbeat_loop():
    backend = get_queue_backend()
    worker = RecordingWorker()

    sleeps = []

    async def fake_sleep(d):
        sleeps.append(d)
        await asyncio.sleep(0.001)

    worker._sleep = fake_sleep

    async def slow_process(*args):
        await asyncio.sleep(0.01)
        return []

    worker.process_job = AsyncMock(side_effect=slow_process)

    await enqueue_job(JobCreate(lecture_id="l1", stage="transcribe", version=1))
    await worker.run_once(wait_seconds=0)

    assert len(sleeps) > 0
    assert sleeps[0] == 100.0
