"""Tests for bounded SIGTERM worker drain and in-flight release."""

import asyncio
import time

import pytest
from core.queue_backend import get_queue_backend
from models.job import JobCreate, JobDB
from repositories.job_repository import JobRepository
from services.queue_client import enqueue_job
from workers.base import BaseWorker, JobContext

pytestmark = pytest.mark.asyncio


class TestWorker(BaseWorker):
    stage = "transcribe"
    queue_name = "transcribe"
    visibility_timeout = 300

    def __init__(self, process_coro=None):
        super().__init__()
        self.process_coro = process_coro
        self.process_calls = 0

    async def process_job(self, job: JobDB, ctx: JobContext) -> list[JobCreate]:
        self.process_calls += 1
        if self.process_coro:
            return await self.process_coro(job, ctx)
        return []


async def test_idle_worker_shutdown_fast():
    """Idle worker: run_forever on empty queue exits quickly upon shutdown_event."""
    worker = TestWorker()
    event = asyncio.Event()

    task = asyncio.create_task(worker.run_forever(event))
    # Give run_forever time to enter long poll
    await asyncio.sleep(0.05)

    start = time.monotonic()
    event.set()
    await asyncio.wait_for(task, timeout=2.0)
    elapsed = time.monotonic() - start

    assert elapsed < 1.0
    assert worker.process_calls == 0


async def test_drain_finishes_in_flight_job(monkeypatch):
    """Job finishes within drain timeout: completes normally, queue depth 0."""
    worker = TestWorker()
    monkeypatch.setattr(worker.settings, "DRAIN_TIMEOUT_SECONDS", 2.0)
    event = asyncio.Event()

    job_barrier = asyncio.Event()

    async def slow_process(job, ctx):
        await job_barrier.wait()
        return []

    worker.process_coro = slow_process

    job = await enqueue_job(JobCreate(lecture_id="l1", stage="transcribe", version=1))

    task = asyncio.create_task(worker.run_forever(event))

    # Wait until worker begins processing
    while worker.process_calls == 0:
        await asyncio.sleep(0.02)

    # Trigger shutdown while job is in-flight
    event.set()
    # Let job finish 0.05s later
    await asyncio.sleep(0.05)
    job_barrier.set()

    await asyncio.wait_for(task, timeout=3.0)

    repo = JobRepository()
    job_db = await repo.get(job.id)
    assert job_db.status == "completed"
    backend = get_queue_backend()
    assert await backend.depth("transcribe") == 0


async def test_drain_timeout_releases_visibility(monkeypatch):
    """Drain timeout exceeded: job cancelled, marked retrying, visibility set to 0."""
    worker = TestWorker()
    monkeypatch.setattr(worker.settings, "DRAIN_TIMEOUT_SECONDS", 0.2)
    event = asyncio.Event()

    hang_event = asyncio.Event()

    async def hanging_process(job, ctx):
        await hang_event.wait()
        return []

    worker.process_coro = hanging_process

    job = await enqueue_job(JobCreate(lecture_id="l1", stage="transcribe", version=1))

    task = asyncio.create_task(worker.run_forever(event))

    while worker.process_calls == 0:
        await asyncio.sleep(0.02)

    event.set()

    # Worker should timeout and exit within 2s
    start = time.monotonic()
    await asyncio.wait_for(task, timeout=2.0)
    elapsed = time.monotonic() - start
    assert elapsed < 2.0

    repo = JobRepository()
    job_db = await repo.get(job.id)
    assert job_db.status == "retrying"
    assert "drain" in (job_db.error_message or "").lower()

    backend = get_queue_backend()
    msgs = await backend.receive("transcribe", wait_seconds=0)
    assert len(msgs) == 1
    assert msgs[0].receive_count == 2
    assert msgs[0].body["job_id"] == job.id


async def test_no_new_receives_after_shutdown(monkeypatch):
    """After shutdown is set, no additional messages are received."""
    worker = TestWorker()
    event = asyncio.Event()
    backend = get_queue_backend()

    receive_calls = 0
    orig_receive = backend.receive

    async def tracking_receive(*args, **kwargs):
        nonlocal receive_calls
        receive_calls += 1
        return await orig_receive(*args, **kwargs)

    monkeypatch.setattr(backend, "receive", tracking_receive)

    task = asyncio.create_task(worker.run_forever(event))
    await asyncio.sleep(0.05)

    calls_before = receive_calls
    event.set()
    await asyncio.wait_for(task, timeout=2.0)

    # After shutdown was set, no further receives should occur
    assert receive_calls <= calls_before + 1
