"""Queue client — enqueue, status, retry, DLQ, idempotency."""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from core.queue_backend import get_queue_backend
from core.queue_config import compute_priority_score
from models.job import JobCreate, JobDB, JobPublic, JobStatus
from repositories.job_repository import JobRepository

logger = logging.getLogger(__name__)


async def enqueue_job(payload: JobCreate) -> JobDB:
    """Enqueue a lecture processing job with idempotency check.

    Returns the existing JobDB if this lecture+version was already enqueued.
    """
    repo = JobRepository()
    score = payload.priority_score or compute_priority_score()
    
    job, created = await repo.create_if_absent(
        lecture_id=payload.lecture_id,
        stage=payload.stage,
        version=payload.version,
        priority_score=score,
        max_attempts=5,
    )
    
    if not created:
        logger.info("Duplicate job detected for %s v%s, skipping enqueue", payload.lecture_id, payload.version)
        return job

    backend = get_queue_backend()
    body = {
        "job_id": job.id,
        "lecture_id": job.lecture_id,
        "stage": job.stage,
        "version": job.version,
    }
    
    target_queue = job.stage
    try:
        await backend.send(target_queue, body)
    except Exception as e:
        from core.sql_db import session_maker
        from models.orm import JobORM
        from sqlalchemy import delete
        async with session_maker()() as session:
            await session.execute(delete(JobORM).where(JobORM.id == job.id))
            await session.commit()
        raise e

    from services.metrics_service import queue_depth as _qd
    depth = await backend.depth(target_queue)
    _qd.labels(queue_type="process_lecture").set(depth)

    logger.info("Enqueued job %s for lecture %s (score=%.1f)", job.id, payload.lecture_id, score)
    return job


async def get_job_status(job_id: str) -> Optional[JobPublic]:
    """Get the current status of a job from the DB."""
    repo = JobRepository()
    job = await repo.get(job_id)
    if not job:
        return None

    return JobPublic(
        id=job.id,
        lecture_id=job.lecture_id,
        stage=job.stage,
        status=job.status,
        attempt=job.attempt,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


async def update_job_status(job_id: str, status: JobStatus, error_message: Optional[str] = None) -> None:
    """Update the status of a job."""
    repo = JobRepository()
    await repo.mark(job_id, status, error_message)

    from services.metrics_service import queue_processing_duration

    if status in ("completed", "failed"):
        job = await repo.get(job_id)
        if job and job.created_at:
            duration = (datetime.now(timezone.utc) - job.created_at).total_seconds()
            queue_processing_duration.labels(
                queue_type="process_lecture",
                status="success" if status == "completed" else "failed",
            ).observe(duration)


async def move_to_dlq(job_id: str, error_message: str) -> None:
    """Move a failed job to the dead-letter queue."""
    backend = get_queue_backend()
    body = {
        "job_id": job_id,
        "error": error_message[:500],
        "moved_at": datetime.now(timezone.utc).isoformat(),
    }
    await backend.send("dlq", body)
    
    await update_job_status(job_id, "dead_letter", error_message)
    
    from services.metrics_service import dead_letter_depth as _dld
    dlq_len = await backend.dlq_depth()
    _dld.labels(queue_type="process_lecture").set(dlq_len)
    logger.warning("Job %s moved to DLQ: %s", job_id, error_message[:100])


async def get_queue_depth() -> int:
    """Get the number of jobs waiting in the primary queues."""
    backend = get_queue_backend()
    depth = await backend.depth("transcribe")
    from services.metrics_service import queue_depth as _qd
    _qd.labels(queue_type="process_lecture").set(depth)
    return depth
