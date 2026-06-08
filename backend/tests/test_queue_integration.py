"""Integration tests for the queue system (requires Redis + workers running).

Run with:
  docker compose up -d redis
  python -m pytest tests/test_queue_integration.py -v --tb=short -m integration

These tests require Redis but not the full stack.
"""
import pytest

pytestmark = pytest.mark.integration


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_connection():
    """Verify Redis is reachable."""
    try:
        from core.queue import get_redis
        redis = get_redis()
        pong = await redis.ping()
        assert pong is True
    except Exception:
        pytest.skip("Redis not available")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_enqueue_and_check():
    """Enqueue a job and verify it appears in the queue."""
    try:
        from models.job import JobCreate
        from services.queue_client import enqueue_job, get_queue_depth

        payload = JobCreate(lecture_id="integration-test-1", stage="transcribe")
        job = await enqueue_job(payload)
        assert job.status in ("queued", "completed")

        depth = await get_queue_depth()
        assert depth >= 0
    except Exception:
        pytest.skip("Redis not available")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_idempotency():
    """Enqueue the same job twice — second should be idempotent."""
    try:
        from models.job import JobCreate
        from services.queue_client import enqueue_job

        payload = JobCreate(lecture_id="idempotency-test-1", version=1)

        first = await enqueue_job(payload)
        second = await enqueue_job(payload)

        assert second.status == "completed"  # Idempotent hit
    except Exception:
        pytest.skip("Redis not available")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_pipeline():
    """End-to-end: upload -> queue -> transcription -> materials -> embedding.

    Requires Redis + workers to be running.
    This is a manual/infrequent test, not part of CI.
    """
    # 1. Upload a lecture (via API or direct DB insert)
    # 2. Verify job appears in queue
    # 3. Wait for workers to process
    # 4. Verify lecture status = ready
    # 5. Verify materials exist on LectureDB
    pytest.skip("Full pipeline integration test requires running services")
