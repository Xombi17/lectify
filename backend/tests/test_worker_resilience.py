import asyncio
import signal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from models.job import JobCreate, JobDB
from workers.base import BaseWorker, JobContext, worker_main


class DummyWorker(BaseWorker):
    stage = "transcribe"
    queue_name = "dummy_queue"

    async def process_job(self, job: JobDB, ctx: JobContext) -> list[JobCreate]:
        return []


@pytest.mark.asyncio
async def test_worker_main_sigterm():
    """Verify worker_main sets shutdown event on SIGTERM."""
    worker_class = DummyWorker

    with patch.object(
        BaseWorker, "run_forever", new_callable=AsyncMock
    ) as mock_run_forever:
        callbacks = {}

        def mock_add_signal_handler(sig, cb):
            callbacks[sig] = cb

        mock_loop = MagicMock()
        mock_loop.add_signal_handler.side_effect = mock_add_signal_handler

        with patch("asyncio.get_running_loop", return_value=mock_loop):
            task = asyncio.create_task(worker_main(worker_class))
            await asyncio.sleep(0.01)

            assert signal.SIGTERM in callbacks
            assert signal.SIGINT in callbacks

            callbacks[signal.SIGTERM]()
            await task

            mock_run_forever.assert_called_once()
            shutdown_event = mock_run_forever.call_args[0][0]
            assert shutdown_event.is_set()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "retry_after_val, expected_sleep",
    [
        (7.0, 7.0),
        (10000.0, 270.0),  # clamped to vt(300) - margin(30) = 270
        (None, 60.0),  # fallback to BACKOFF[0]=60, capped by 270
        (0.0, 1.0),  # floor of 1.0
    ],
)
async def test_rate_limit_backpressure_retry_after(retry_after_val, expected_sleep):
    """Verify ProviderRateLimited honors Retry-After header with clamping."""
    from services.ai_service import ProviderRateLimited

    class RateLimitedWorker(BaseWorker):
        stage = "transcribe"
        queue_name = "rl_q"
        visibility_timeout = 300

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.attempts = 0

        async def process_job(self, job: JobDB, ctx: JobContext) -> list[JobCreate]:
            self.attempts += 1
            if self.attempts == 1:
                raise ProviderRateLimited(
                    "Too Many Requests", retry_after=retry_after_val
                )
            return []

    worker = RateLimitedWorker()
    worker.settings.RATE_LIMIT_MAX_SLEEP_MARGIN_S = 30

    mock_sleep = AsyncMock()
    worker._sleep = mock_sleep

    with (
        patch("workers.base.get_queue_backend") as MockBackend,
        patch("workers.base.JobRepository") as MockRepo,
    ):

        class FakeMsg:
            body = {"job_id": "job-123"}
            receipt = "receipt-123"
            receive_count = 1

        backend = AsyncMock()
        backend.receive.return_value = [FakeMsg()]
        MockBackend.return_value = backend

        repo = AsyncMock()
        repo.claim.return_value = JobDB(
            id="job-123",
            lecture_id="lec-1",
            stage="transcribe",
            version=1,
            status="processing",
        )
        MockRepo.return_value = repo

        await worker.run_once()

        assert worker.attempts == 2
        slept_delays = [c.args[0] for c in mock_sleep.call_args_list]
        assert expected_sleep in slept_delays
        assert backend.receive.await_count == 1
        backend.change_visibility.assert_not_called()
        repo.mark.assert_awaited_with("job-123", "completed")


@pytest.mark.asyncio
async def test_rate_limit_max_waits_exceeded():
    """Verify exceeding RATE_LIMIT_MAX_WAITS falls into normal failure path."""
    from services.ai_service import ProviderRateLimited

    class AlwaysRateLimitedWorker(BaseWorker):
        stage = "transcribe"
        queue_name = "rl_q"
        visibility_timeout = 300

        async def process_job(self, job: JobDB, ctx: JobContext) -> list[JobCreate]:
            raise ProviderRateLimited("Rate limited", retry_after=2.0)

    worker = AlwaysRateLimitedWorker()
    worker.settings.RATE_LIMIT_MAX_WAITS = 3
    worker.settings.RATE_LIMIT_MAX_SLEEP_MARGIN_S = 30

    mock_sleep = AsyncMock()
    worker._sleep = mock_sleep

    with (
        patch("workers.base.get_queue_backend") as MockBackend,
        patch("workers.base.JobRepository") as MockRepo,
        patch("workers.base.LectureRepository") as MockLecRepo,
    ):

        class FakeMsg:
            body = {"job_id": "job-123"}
            receipt = "receipt-123"
            receive_count = 1

        backend = AsyncMock()
        backend.receive.return_value = [FakeMsg()]
        MockBackend.return_value = backend

        repo = AsyncMock()
        repo.claim.return_value = JobDB(
            id="job-123",
            lecture_id="lec-1",
            stage="transcribe",
            version=1,
            status="processing",
        )
        MockRepo.return_value = repo

        lec_repo = AsyncMock()
        MockLecRepo.return_value = lec_repo

        await worker.run_once()

        repo.mark.assert_awaited_with("job-123", "retrying", "Rate limited")
        backend.change_visibility.assert_awaited_once()
