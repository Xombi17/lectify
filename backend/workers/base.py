"""Base worker class for SQS-style lecture processing workers."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional

from core.config import get_settings
from core.queue_backend import get_queue_backend
from models.job import JobCreate, JobDB
from repositories.job_repository import JobRepository
from repositories.lecture_repository import LectureRepository

logger = logging.getLogger(__name__)


class JobContext:
    def __init__(
        self,
        job_id: str,
        receive_count: int,
        backend,
        queue_name: str,
        receipt: str,
        visibility_timeout: int,
    ):
        self.job_id = job_id
        self.receive_count = receive_count
        self._backend = backend
        self._queue_name = queue_name
        self._receipt = receipt
        self._visibility_timeout = visibility_timeout

    async def touch(self):
        await self._backend.change_visibility(
            self._queue_name, self._receipt, self._visibility_timeout
        )


class BaseWorker(ABC):
    stage: str = "base"
    queue_name: str = "default"
    visibility_timeout: int = 300
    BACKOFF = (60, 300, 900, 900)

    def __init__(self, max_jobs: Optional[int] = None):
        self.settings = get_settings()
        self.max_jobs = max_jobs or 1
        self._in_flight = False

        # Injectable sleeper for tests
        self._sleep = asyncio.sleep

    @abstractmethod
    async def process_job(self, job: JobDB, ctx: JobContext) -> list[JobCreate]: ...

    async def run_once(self, wait_seconds: int = 20) -> bool:
        backend = get_queue_backend()
        messages = await backend.receive(
            self.queue_name,
            max_messages=1,
            wait_seconds=wait_seconds,
            visibility_timeout=self.visibility_timeout,
        )
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

        self._in_flight = True
        ctx = JobContext(
            job_id,
            msg.receive_count,
            backend,
            self.queue_name,
            msg.receipt,
            self.visibility_timeout,
        )
        ctx = JobContext(
            job_id,
            msg.receive_count,
            backend,
            self.queue_name,
            msg.receipt,
            self.visibility_timeout,
        )

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

            completed = False
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
                        logger.error(
                            f"Exceeded RATE_LIMIT_MAX_WAITS ({self.settings.RATE_LIMIT_MAX_WAITS}) for job {job_id}"
                        )
                        raise

                    cap = max(
                        1,
                        self.visibility_timeout
                        - self.settings.RATE_LIMIT_MAX_SLEEP_MARGIN_S,
                    )
                    delay = (
                        e.retry_after
                        if e.retry_after is not None
                        else self.BACKOFF[
                            min(rate_limit_attempts - 1, len(self.BACKOFF) - 1)
                        ]
                    )
                    delay = min(max(delay, 1), cap)
                    logger.warning(
                        f"Rate limited by provider (attempt {rate_limit_attempts}). "
                        f"Backing off in-process for {delay}s (retry_after={e.retry_after}) for job {job_id}"
                    )
                    await self._sleep(delay)

            # Enqueue next stage jobs before marking completed
            if next_jobs:
                from services.queue_client import enqueue_job

                for nj in next_jobs:
                    await enqueue_job(nj, resend_if_queued=msg.receive_count > 1)

            # Complete
            await repo.mark(job_id, "completed")
            completed = True

            # Delete message last
            await backend.delete(self.queue_name, msg.receipt)

        except asyncio.CancelledError:
            if not completed:
                try:
                    await backend.change_visibility(self.queue_name, msg.receipt, 0)
                except Exception as ex:
                    logger.warning(
                        f"Failed to reset visibility on cancel for job {job_id}: {ex}"
                    )
                try:
                    await repo.mark(job_id, "retrying", "released on shutdown drain")
                except Exception as ex:
                    logger.warning(
                        f"Failed to mark retrying on cancel for job {job_id}: {ex}"
                    )
            raise

        except Exception as e:
            if completed:
                logger.warning(
                    f"Post-completion error for job {job_id}, message will redeliver and be dropped by claim: {e}"
                )
                return True

            # Failure path
            rc = msg.receive_count
            error_message = str(e)[:500]

            if rc >= self.settings.QUEUE_MAX_RECEIVES:
                # Dead letter
                await repo.mark(job_id, "dead_letter", error_message)
                logger.error(
                    "JOB_DEAD_LETTER job_id=%s lecture_id=%s stage=%s receive_count=%s error=%s",
                    job_id, claimed.lecture_id, self.stage, rc, error_message,
                )
                lec_repo = LectureRepository()
                await lec_repo.update_fields(
                    claimed.lecture_id,
                    {"status": "dead_letter", "error_message": error_message},
                )
                # message NOT deleted, broker moves to DLQ
            else:
                # Retry
                delay = self.BACKOFF[min(rc - 1, len(self.BACKOFF) - 1)]
                await repo.mark(job_id, "retrying", error_message)
                lec_repo = LectureRepository()
                await lec_repo.update_fields(
                    claimed.lecture_id,
                    {"status": "retrying", "error_message": error_message},
                )
                await backend.change_visibility(self.queue_name, msg.receipt, delay)

        finally:
            self._in_flight = False
            if heartbeat_task:
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

        return True

    async def run_forever(self, shutdown_event: asyncio.Event) -> None:
        logger.info(
            f"Worker {self.__class__.__name__} starting (max_jobs={self.max_jobs})"
        )
        while not shutdown_event.is_set():
            task = asyncio.create_task(self.run_once(wait_seconds=20))
            stop = asyncio.create_task(shutdown_event.wait())
            done, pending = await asyncio.wait(
                {task, stop}, return_when=asyncio.FIRST_COMPLETED
            )
            if task in done:
                stop.cancel()
                try:
                    processed = task.result()
                except Exception as e:
                    logger.error(f"Error in run_once: {e}")
                    processed = False
                if not processed and not shutdown_event.is_set():
                    try:
                        await asyncio.wait_for(shutdown_event.wait(), 1.0)
                    except (asyncio.TimeoutError, TimeoutError):
                        pass
            else:
                stop.cancel()
                if not self._in_flight:
                    task.cancel()
                else:
                    try:
                        await asyncio.wait_for(
                            asyncio.shield(task),
                            self.settings.DRAIN_TIMEOUT_SECONDS,
                        )
                    except (asyncio.TimeoutError, TimeoutError):
                        logger.warning(
                            f"Drain timeout ({self.settings.DRAIN_TIMEOUT_SECONDS}s) exceeded; cancelling in-flight task"
                        )
                        task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                break

        logger.info(
            f"Worker {self.__class__.__name__} drained and shut down gracefully"
        )


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
