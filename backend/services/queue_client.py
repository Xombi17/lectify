"""Queue client — enqueue, status, retry, DLQ, idempotency."""
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from core.queue import get_redis
from core.queue_config import (
    DLQ_PROCESS_LECTURE,
    IDEMPOTENCY_SET,
    QUEUE_PROCESS_LECTURE,
    compute_priority_score,
)
from models.job import JobCreate, JobDB, JobPublic, JobStatus

logger = logging.getLogger(__name__)

IDEMPOTENCY_TTL = 86400  # 24 hours


async def enqueue_job(payload: JobCreate) -> JobDB:
    """Enqueue a lecture processing job with idempotency check.

    Returns the existing JobDB if this lecture+version was already enqueued.
    """
    redis = get_redis()
    idempotency_key = f"lecture:{payload.lecture_id}:v{payload.version}"

    # Idempotency check: use individual key with TTL so each entry expires independently
    # Using SET NX (only set if key doesn't exist) with per-key 24h expiry avoids the
    # shared-SET-EXPIRE leak where every new entry resets TTL for ALL entries.
    individual_key = f"{IDEMPOTENCY_SET}:{idempotency_key}"
    existed = await redis.set(individual_key, "1", ex=IDEMPOTENCY_TTL, nx=True)
    if existed is None:
        # Key already existed — this is a duplicate
        logger.info("Duplicate job detected for %s, skipping enqueue", idempotency_key)
        # Return a placeholder JobDB with status completed
        return JobDB(
            id=idempotency_key,
            lecture_id=payload.lecture_id,
            status="completed",
            version=payload.version,
        )

    # Compute priority score
    score = payload.priority_score or compute_priority_score()

    # Create job record
    job_id = str(uuid.uuid4())
    job = JobDB(
        id=job_id,
        lecture_id=payload.lecture_id,
        stage=payload.stage,
        status="queued",
        version=payload.version,
        priority_score=score,
        attempt=0,
    )

    # Push to the priority queue (Redis sorted set)
    await redis.zadd(QUEUE_PROCESS_LECTURE, {job_id: score})
    # Store job metadata in a hash for quick lookup
    await redis.hset(
        f"job:{job_id}",
        mapping={
            "lecture_id": payload.lecture_id,
            "stage": payload.stage,
            "status": "queued",
            "version": str(payload.version),
            "attempt": "0",
            "max_attempts": "3",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    logger.info("Enqueued job %s for lecture %s (score=%.1f)", job_id, payload.lecture_id, score)
    return job


async def get_job_status(job_id: str) -> Optional[JobPublic]:
    """Get the current status of a job from its hash."""
    redis = get_redis()
    data = await redis.hgetall(f"job:{job_id}")
    if not data:
        return None

    return JobPublic(
        id=job_id,
        lecture_id=data.get(b"lecture_id", b"").decode(),
        stage=data.get(b"stage", b"transcribe").decode(),
        status=data.get(b"status", b"queued").decode(),
        attempt=int(data.get(b"attempt", b"0")),
        error_message=data.get(b"error_message", b"").decode() or None,
        created_at=datetime.fromisoformat(data.get(b"created_at", datetime.now(timezone.utc).isoformat()).decode()),
        updated_at=datetime.fromisoformat(data.get(b"updated_at", datetime.now(timezone.utc).isoformat()).decode()),
    )


async def update_job_status(job_id: str, status: JobStatus, error_message: Optional[str] = None) -> None:
    """Update the status of a job."""
    redis = get_redis()
    mapping = {
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if error_message:
        mapping["error_message"] = error_message[:500]
    await redis.hset(f"job:{job_id}", mapping=mapping)


async def move_to_dlq(job_id: str, error_message: str) -> None:
    """Move a failed job to the dead-letter queue."""
    redis = get_redis()
    dlq_entry = {
        "job_id": job_id,
        "error": error_message[:500],
        "moved_at": datetime.now(timezone.utc).isoformat(),
    }
    await redis.lpush(DLQ_PROCESS_LECTURE, json.dumps(dlq_entry))
    await update_job_status(job_id, "dead_letter", error_message)
    logger.warning("Job %s moved to DLQ: %s", job_id, error_message[:100])


async def get_queue_depth() -> int:
    """Get the number of jobs waiting in the priority queue."""
    redis = get_redis()
    return await redis.zcard(QUEUE_PROCESS_LECTURE)
