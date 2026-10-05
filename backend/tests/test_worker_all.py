"""Tests for combined 3-loop worker entrypoint ('python -m workers all')."""
import asyncio
from unittest.mock import MagicMock, patch
import pytest

from workers import __main__ as wm


class FakeWorker:
    def __init__(self, name="fake", fail_times=0):
        self.name = name
        self.fail_times = fail_times
        self.runs = 0
        self.drained = False

    async def run_forever(self, shutdown_event: asyncio.Event):
        self.runs += 1
        if self.runs <= self.fail_times:
            raise RuntimeError(f"{self.name} intentional crash {self.runs}")
        # Wait until shutdown
        await shutdown_event.wait()
        self.drained = True


@pytest.mark.asyncio
async def test_run_all_gathers_three_workers_and_shares_shutdown():
    w1 = FakeWorker("w1")
    w2 = FakeWorker("w2")
    w3 = FakeWorker("w3")

    run_task = asyncio.create_task(wm.run_all(worker_classes=[w1, w2, w3]))

    # Allow workers to start
    await asyncio.sleep(0.01)
    assert w1.runs == 1
    assert w2.runs == 1
    assert w3.runs == 1
    assert not w1.drained

    # Trigger signal or simulate shutdown_event by sending SIGINT/SIGTERM to handler
    # We can inspect the signal handlers installed or patch loop.add_signal_handler
    # For now trigger shutdown via the signal handler
    loop = asyncio.get_running_loop()
    # Find signal handler or invoke SIGTERM handler
    # Since run_all installs handlers, let's trigger the registered handler or call it
    # We can test shutdown via a small helper task:
    with patch.object(loop, "add_signal_handler") as mock_add_sig:
        # Test directly with run_all passing classes
        pass

    # Cancel or set shutdown:
    # Let's inspect how run_all sets shutdown:
    # Let's run a test where signal handler is called
    handlers = {}
    def mock_add(sig, handler):
        handlers[sig] = handler

    with patch.object(loop, "add_signal_handler", side_effect=mock_add):
        run_task2 = asyncio.create_task(wm.run_all(worker_classes=[w1, w2, w3]))
        await asyncio.sleep(0.01)
        # Call the installed handler
        import signal
        assert signal.SIGTERM in handlers
        handlers[signal.SIGTERM]()
        await run_task2

    assert w1.drained is True
    assert w2.drained is True
    assert w3.drained is True
    run_task.cancel()
    try:
        await run_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_run_all_supervises_and_restarts_crashed_worker():
    slept_delays = []

    async def fake_sleep(d):
        slept_delays.append(d)

    w_crash = FakeWorker("crasher", fail_times=2)
    w_steady = FakeWorker("steady", fail_times=0)

    loop = asyncio.get_running_loop()
    handlers = {}
    with patch.object(loop, "add_signal_handler", side_effect=lambda s, h: handlers.update({s: h})):
        task = asyncio.create_task(
            wm.run_all(
                worker_classes=[w_crash, w_steady],
                restart_delay=5.0,
                sleep=fake_sleep,
            )
        )
        # Yield to let w_crash fail twice and recover
        for _ in range(5):
            await asyncio.sleep(0.01)

        assert w_crash.runs == 3  # Failed twice, restarted twice, now running 3rd time
        assert w_steady.runs == 1  # Never crashed
        assert slept_delays == [5.0, 5.0]

        import signal
        handlers[signal.SIGTERM]()
        await task

    assert w_crash.drained is True
    assert w_steady.drained is True


def test_main_accepts_all_stage():
    with patch("workers.__main__.asyncio.run") as mock_run:
        def close_coro(coro):
            coro.close()
            return None

        mock_run.side_effect = close_coro
        ret = wm.main(["all"])
        assert ret == 0
        mock_run.assert_called_once()
