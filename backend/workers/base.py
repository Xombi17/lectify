"""Base worker class for SQS-style lecture processing workers."""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional

from core.queue_backend import get_queue_backend
from models.job import JobCreate, JobDB
from repositories.job_repository import JobRepository
from repositories.lecture_repository import LectureRepository
from core.config import get_settings

logger = logging.getLogger(__name__)


class JobContext:
    def __init__(self, job_id: str, receive_count: int, backend, queue_name: str, receipt: str, visibility_timeout: int):
        self.job_id = job_id
        self.receive_count = receive_count
        self._backend = backend
        self._queue_name = queue_name
        self._receipt = receipt
        self._visibility_timeout = visibility_timeout

    async def touch(self):
        await self._backend.change_visibility(self._queue_name, self._receipt, self._visibility_timeout)


class BaseWorker(ABC):
    stage: str = "base"
    queue_name: str = "default"
    visibility_timeout: int = 300
    BACKOFF = (60, 300, 900, 900)

    def __init__(self, max_jobs: Optional[int] = None):
        self.settings = get_settings()
        self.max_jobs = max_jobs or 1
        
        # Injectable sleeper for tests
        self._sleep = asyncio.sleep

    @abstractmethod
    async def process_job(self, job: JobDB, ctx: JobContext) -> list[JobCreate]:
        ...

    async def run_once(self, wait_seconds: int = 20) -> bool:
        backend = get_queue_backend()
        messages = await backend.receive(self.queue_name, max_messages=1, wait_seconds=wait_seconds, visibility_timeout=self.visibility_timeout)
        if not messages:
            return False
            
        msg = messages[0]
        job_id = msg.body.get("job_id")
        if not job_id:
            await backend.delete(self.queue_name, msg.receipt)
            return True

        repo = JobRepository()
        claimed = await repo.claim(job_id, stale_after_s=self.visibility_timeout)
        if not claimed:
            # duplicate or stale delivery, ignore
            await backend.delete(self.queue_name, msg.receipt)
            return True

        ctx = JobContext(job_id, msg.receive_count, backend, self.queue_name, msg.receipt, self.visibility_timeout)
        
        heartbeat_task = None
        async def heartbeat_loop():
            try:
                while True:
                    await self._sleep(self.visibility_timeout / 3.0)
                    await ctx.touch()
            except asyncio.CancelledError:
                pass

        try:
            heartbeat_task = asyncio.create_task(heartbeat_loop())
            
            from services.ai_service import ProviderRateLimited
            
            next_jobs = None
            rate_limit_attempts = 0
            while True:
                try:
                    # Run processing
                    next_jobs = await self.process_job(claimed, ctx)
                    break
                except ProviderRateLimited as e:
                    rate_limit_attempts += 1
                    if rate_limit_attempts > self.settings.RATE_LIMIT_MAX_WAITS:
                        logger.error(f"Exceeded RATE_LIMIT_MAX_WAITS ({self.settings.RATE_LIMIT_MAX_WAITS}) for job {job_id}")
                        raise
                    
                    delay = self.BACKOFF[min(rate_limit_attempts - 1, len(self.BACKOFF) - 1)]
                    delay = min(delay, self.settings.RATE_LIMIT_MAX_SLEEP_MARGIN_S)
                    logger.warning(f"Rate limited by provider (attempt {rate_limit_attempts}). Backing off in-process for {delay}s for job {job_id}")
                    await self._sleep(delay)
            
            # Complete
            await repo.mark(job_id, "completed")
            
            # Enqueue next stage jobs
            if next_jobs:
                from services.queue_client import enqueue_job
                for nj in next_jobs:
                    await enqueue_job(nj)
                    
            # Delete message last
            await backend.delete(self.queue_name, msg.receipt)
            
        except Exception as e:
            # Failure path
            rc = msg.receive_count
            error_message = str(e)[:500]
            
            if rc >= self.settings.QUEUE_MAX_RECEIVES:
                # Dead letter
                await repo.mark(job_id, "dead_letter", error_message)
                lec_repo = LectureRepository()
                await lec_repo.update_fields(claimed.lecture_id, {"status": "dead_letter", "error_message": error_message})
                # message NOT deleted, broker moves to DLQ
            else:
                # Retry
                delay = self.BACKOFF[min(rc - 1, len(self.BACKOFF) - 1)]
                await repo.mark(job_id, "retrying", error_message)
                lec_repo = LectureRepository()
                await lec_repo.update_fields(claimed.lecture_id, {"status": "retrying", "error_message": error_message})
                await backend.change_visibility(self.queue_name, msg.receipt, delay)
                
        finally:
            if heartbeat_task:
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass
                
        return True

    async def run_forever(self, shutdown_event: asyncio.Event) -> None:
        logger.info(f"Worker {self.__class__.__name__} starting (max_jobs={self.max_jobs})")
        while not shutdown_event.is_set():
            processed = await self.run_once(wait_seconds=20)
            if not processed and not shutdown_event.is_set():
                await asyncio.sleep(1)
                
        logger.info(f"Worker {self.__class__.__name__} shutting down gracefully")


async def worker_main(worker_class):
    import signal
    logging.basicConfig(level=logging.INFO)
    
    shutdown_event = asyncio.Event()
    
    def _signal_handler():
        logger.info("Received termination signal, draining active jobs...")
        shutdown_event.set()
        
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _signal_handler)
        
    worker = worker_class()
    await worker.run_forever(shutdown_event)
