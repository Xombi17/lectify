"""Tests for workers CLI entrypoint and stage-keyed queue polling."""

import os
import signal
import subprocess
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from core.config import get_settings
from core.queue_backend import MemoryQueueBackend, SqsQueueBackend, get_queue_backend
from models.job import JobCreate
from services.queue_client import enqueue_job
from workers import __main__ as wm
from workers.ai import AIWorker
from workers.embedding import EmbeddingWorker
from workers.transcription import TranscriptionWorker


def test_stage_workers_mapping():
    assert wm.STAGE_WORKERS["transcribe"] is TranscriptionWorker
    assert wm.STAGE_WORKERS["generate_materials"] is AIWorker
    assert wm.STAGE_WORKERS["materials"] is AIWorker
    assert wm.STAGE_WORKERS["embed"] is EmbeddingWorker


def test_main_usage_on_invalid_args():
    stderr = StringIO()
    with patch("sys.stderr", stderr):
        assert wm.main([]) == 2
        assert wm.main(["bogus"]) == 2
        assert wm.main(["transcribe", "extra"]) == 2

    output = stderr.getvalue()
    assert "usage: python -m workers" in output
    assert "transcribe" in output
    assert "generate_materials" in output
    assert "embed" in output


def test_workers_queue_names():
    assert TranscriptionWorker.queue_name == "transcribe"
    assert AIWorker.queue_name == "generate_materials"
    assert EmbeddingWorker.queue_name == "embed"


@pytest.mark.asyncio
async def test_memory_backend_stage_key_matching():
    backend = get_queue_backend()
    await enqueue_job(JobCreate(lecture_id="l1", stage="generate_materials", version=1))
    msgs = await backend.receive(AIWorker.queue_name, wait_seconds=0)
    assert len(msgs) == 1
    assert msgs[0].body["stage"] == "generate_materials"


def test_sqs_backend_resolves_stage_key(monkeypatch):
    import core.config
    import core.queue_config

    settings = core.config.get_settings()
    monkeypatch.setattr(
        settings,
        "QUEUE_URL_MATERIALS",
        "https://sqs.us-east-1.amazonaws.com/123/materials",
    )
    # Also patch core.config.get_settings to return the same settings instance
    monkeypatch.setattr(core.config, "get_settings", lambda: settings)
    sqs = SqsQueueBackend()
    assert (
        sqs._resolve(AIWorker.queue_name)
        == "https://sqs.us-east-1.amazonaws.com/123/materials"
    )


def test_subprocess_entrypoint_bogus():
    backend_dir = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    env["ENV"] = "test"
    env["QUEUE_BACKEND"] = "memory"
    env["JWT_SECRET"] = "test-secret"

    result = subprocess.run(
        [sys.executable, "-m", "workers", "bogus"],
        cwd=backend_dir,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 2
    assert "usage: python -m workers" in result.stderr


def test_subprocess_entrypoint_sigterm():
    backend_dir = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    env["ENV"] = "test"
    env["QUEUE_BACKEND"] = "memory"
    env["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
    env["JWT_SECRET"] = "test-secret-at-least-32-chars-long"
    env.pop("SSM_PREFIX", None)

    proc = subprocess.Popen(
        [sys.executable, "-m", "workers", "transcribe"],
        cwd=backend_dir,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        env=env,
    )

    started = False
    try:
        # Read output until "starting" appears or timeout
        import time

        start_time = time.monotonic()
        while time.monotonic() - start_time < 30.0:
            line = proc.stderr.readline()
            if "starting" in line.lower():
                started = True
                break
            if proc.poll() is not None:
                break

        assert started, f"Worker did not start in time. stderr: {proc.stderr.read()}"
        proc.send_signal(signal.SIGTERM)
        ret = proc.wait(timeout=10.0)
        assert ret == 0
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
