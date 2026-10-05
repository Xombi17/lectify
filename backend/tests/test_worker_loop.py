"""Tests for the SQS-style worker poll/claim/commit/enqueue/delete loop."""
import asyncio
import pytest
from unittest.mock import AsyncMock

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
        return [JobCreate(lecture_id=job.lecture_id, stage="generate_materials", version=job.version)]


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
    async def fake_enqueue(job):
        worker.calls.append("enqueue_next")
        return await original_enqueue(job)
    monkeypatch.setattr(qc, "enqueue_job", fake_enqueue)
    
    await enqueue_job(JobCreate(lecture_id="l1", stage="transcribe", version=1))
    
    handled = await worker.run_once(wait_seconds=0)
    assert handled is True
    
    assert worker.calls == ["claim", "process", "mark_completed", "enqueue_next", "delete"]

async def test_duplicate_delivery(monkeypatch):
    backend = get_queue_backend()
    repo = JobRepository()
    worker = RecordingWorker()
    
    job = await enqueue_job(JobCreate(lecture_id="l1", stage="transcribe", version=1))
    
    handled = await worker.run_once(wait_seconds=0)
    assert handled is True
    assert worker.calls == ["process"]
    
    # manually send a message for the completed job (simulating broker duplicate delivery)
    await backend.send("transcribe", {"job_id": job.id, "lecture_id": "l1", "stage": "transcribe", "version": 1})
    
    worker.calls.clear()
    handled = await worker.run_once(wait_seconds=0)
    assert handled is True
    assert worker.calls == []
    assert await backend.depth("transcribe") == 0

async def test_crash_simulation_redelivery(monkeypatch):
    backend = get_queue_backend()
    repo = JobRepository()
    worker = RecordingWorker()
    
    original_delete = backend.delete
    delete_calls = 0
    async def fake_delete(q, r):
        nonlocal delete_calls
        delete_calls += 1
        if delete_calls == 1:
            raise RuntimeError("Crash before delete")
        await original_delete(q, r)
    monkeypatch.setattr(backend, "delete", fake_delete)
    
    await enqueue_job(JobCreate(lecture_id="l1", stage="transcribe", version=1))
    
    # In base.py we catch all exceptions and mark as retrying, so it won't raise out of run_once
    handled = await worker.run_once(wait_seconds=0)
    assert handled is True
        
    assert worker.calls == ["process"]
    
    import time
    for q in backend._queues.values():
        for m in q:
            m["visible_at"] = time.monotonic() - 1
            
    worker.calls.clear()
    handled = await worker.run_once(wait_seconds=0)
    assert handled is True
    # The job was marked retrying due to the Exception block in run_once
    # So the second time it is claimed successfully and processed again!
    assert worker.calls == ["process"]
    assert delete_calls == 2

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
