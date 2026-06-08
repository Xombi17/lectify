"""Base worker class for ARQ-based lecture processing workers."""
import logging
from abc import ABC, abstractmethod
from typing import Optional

from arq import create_pool
from arq.connections import RedisSettings

from core.config import get_settings
from core.queue import close_redis
from core.queue_config import QUEUE_PROCESS_LECTURE, DLQ_PROCESS_LECTURE

logger = logging.getLogger(__name__)


class BaseWorker(ABC):
    """Base class for lecture processing workers.

    Each worker type (transcription, ai, embedding) extends this class
    and implements `process_job()`.
    """

    worker_name: str = "base"
    max_jobs: int = 1  # ARQ 0.28 param name (was `concurrency` in older versions)
    queue_name: str = QUEUE_PROCESS_LECTURE
    dlq_name: str = DLQ_PROCESS_LECTURE

    def __init__(self, max_jobs: Optional[int] = None):
        if max_jobs is not None:
            self.max_jobs = max_jobs
        self._pool = None

    async def startup(self) -> None:
        """Initialize connections on worker start."""
        settings = get_settings()
        self._pool = await create_pool(
            RedisSettings.from_dsn(settings.REDIS_URL),
        )
        logger.info(
            "%s worker started (max_jobs=%d, queue=%s)",
            self.worker_name,
            self.max_jobs,
            self.queue_name,
        )

    async def shutdown(self) -> None:
        """Clean up connections on worker stop."""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
        await close_redis()
        logger.info("%s worker stopped", self.worker_name)

    @abstractmethod
    async def process_job(self, ctx: dict, job_data: dict) -> dict:
        """Process a single job. Must be implemented by subclasses.

        Args:
            ctx: ARQ context dict (includes 'redis' connection)
            job_data: Dictionary with job payload (lecture_id, stage, etc.)

        Returns:
            Dict with result info (next_stage, status, etc.)
        """
        ...

    async def health_check(self) -> dict:
        """Basic health check — Redis ping + processed count."""
        from core.queue import get_redis
        redis = get_redis()
        try:
            await redis.ping()
            redis_ok = True
        except Exception:
            redis_ok = False
        return {
            "worker": self.worker_name,
            "redis": "ok" if redis_ok else "error",
            "max_jobs": self.max_jobs,
        }

    def get_retry_delay(self, attempt: int) -> int:
        """Return retry delay in seconds for the given attempt number.

        Implements exponential backoff: 1m -> 5m -> 15m (max 3 attempts).
        After the 3rd attempt (attempt=2), moves to DLQ.
        """
        delays = [60, 300, 900]  # 1 min, 5 min, 15 min
        if attempt < len(delays):
            return delays[attempt]
        return 900  # cap at 15 min


async def worker_main(worker_cls: type[BaseWorker], **kwargs) -> None:
    """Entry point for running a worker as a standalone process.

    Retry strategy: ARQ's native retry is disabled (retry_jobs=False) so that
    workers manage retry manually via attempt counting, get_retry_delay(),
    and move_to_dlq() — giving us full control over the exponential backoff
    (1m → 5m → 15m) and DLQ routing. The workers' process_job() methods
    return {"status": "retrying"} for transient failures; the ARQ worker
    simply treats any exception / non-"completed" return as a signal to
    re-enqueue (handled by the manual loop below).

    Usage in docker-compose:
      command: python -c "from workers.base import worker_main; from workers.transcription import TranscriptionWorker; worker_main(TranscriptionWorker)"
    """
    worker = worker_cls(**kwargs)
    await worker.startup()

    # ARQ worker configuration
    from arq.worker import Worker as ArqWorker

    arq_worker = ArqWorker(
        pool=worker._pool,
        functions=[worker.process_job],
        queue_name=worker.queue_name,
        max_jobs=worker.max_jobs,
        on_startup=lambda ctx: None,
        on_shutdown=lambda ctx: None,
        # Manual retry — we control backoff and DLQ in process_job()
        retry_jobs=False,
    )

    try:
        await arq_worker.run()
    finally:
        await worker.shutdown()
