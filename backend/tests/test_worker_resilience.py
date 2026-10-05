import asyncio
import signal
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from models.job import JobDB, JobCreate
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
    
    with patch.object(BaseWorker, 'run_forever', new_callable=AsyncMock) as mock_run_forever:
        callbacks = {}
        def mock_add_signal_handler(sig, cb):
            callbacks[sig] = cb
            
        mock_loop = MagicMock()
        mock_loop.add_signal_handler.side_effect = mock_add_signal_handler
        
        with patch('asyncio.get_running_loop', return_value=mock_loop):
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
async def test_rate_limit_backpressure():
    """Verify ProviderRateLimited triggers in-process backpressure sleep."""
    from services.ai_service import ProviderRateLimited
    
    class RateLimitedWorker(BaseWorker):
        stage = "transcribe"
        queue_name = "rl_q"
        
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.attempts = 0
            
        async def process_job(self, job: JobDB, ctx: JobContext) -> list[JobCreate]:
            self.attempts += 1
            if self.attempts == 1:
                raise ProviderRateLimited("Too Many Requests")
            return []

    worker = RateLimitedWorker()
    
    mock_sleep = AsyncMock()
    worker._sleep = mock_sleep
    
    with patch("workers.base.get_queue_backend") as MockBackend, \
         patch("workers.base.JobRepository") as MockRepo:
         
        class FakeMsg:
            body = {"job_id": "job-123"}
            receipt = "receipt-123"
            receive_count = 1
            
        backend = AsyncMock()
        backend.receive.return_value = [FakeMsg()]
        MockBackend.return_value = backend
        
        repo = AsyncMock()
        repo.claim.return_value = JobDB(id="job-123", lecture_id="lec-1", stage="transcribe", version=1, status="processing")
        MockRepo.return_value = repo
        
        await worker.run_once()
        
        assert worker.attempts == 2
        mock_sleep.assert_called_once()
        assert mock_sleep.call_args[0][0] == min(worker.settings.RATE_LIMIT_MAX_SLEEP_MARGIN_S, 60)
