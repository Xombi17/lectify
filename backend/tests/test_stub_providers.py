"""StubProvider gating + canned output (VER-03)."""
import asyncio
import math
from pathlib import Path

import pytest

from services import ai_service
from services.ai_service import StubProvider, get_ai_service, reset_ai_service, stub_providers_enabled


@pytest.fixture(autouse=True)
def _reset():
    reset_ai_service()
    yield
    reset_ai_service()


@pytest.mark.parametrize("env", ["production", "prod", "dev", "test", "aws"])
def test_unset_flag_is_inert(monkeypatch, env):
    monkeypatch.delenv("STUB_PROVIDERS", raising=False)
    monkeypatch.setenv("ENV", env)
    assert stub_providers_enabled() is False


@pytest.mark.parametrize("env", ["production", "prod", "dev", "test"])
def test_flag_inert_outside_deploy_envs(monkeypatch, env):
    monkeypatch.setenv("STUB_PROVIDERS", "1")
    monkeypatch.setenv("ENV", env)
    assert stub_providers_enabled() is False
    reset_ai_service()
    try:
        # ai_service.StubProvider (not the imported name): test_gemini_failover reloads the module
        assert not isinstance(get_ai_service(), ai_service.StubProvider)
    except RuntimeError:
        pass  # no API key configured: real provider refused, stub not used


@pytest.mark.parametrize("env", ["aws", "demo", "staging", "AWS"])
def test_flag_active_in_deploy_envs(monkeypatch, env):
    monkeypatch.setenv("STUB_PROVIDERS", "1")
    monkeypatch.setenv("ENV", env)
    assert stub_providers_enabled() is True
    assert isinstance(get_ai_service(), ai_service.StubProvider)


def test_canned_output(monkeypatch):
    monkeypatch.setenv("STUB_DELAY_S", "0")
    p = StubProvider()

    async def run():
        t = await p.transcribe_audio(Path("x.wav"), "audio/wav")
        m = await p.generate_study_materials(t)
        v = await p.embed("hello")
        return t, m, v

    t, m, v = asyncio.run(run())
    assert t
    assert m.summary and m.key_concepts and m.flashcards
    assert m.quiz and len(m.quiz[0].options) == 4
    assert len(v) == 768 and math.isclose(math.sqrt(sum(x * x for x in v)), 1.0)


@pytest.mark.asyncio
async def test_worker_stub_path_never_calls_http(monkeypatch):
    from unittest.mock import AsyncMock, MagicMock, patch

    import httpx

    from core.config import get_settings
    from models.job import JobDB
    from services.transcription_service import build_transcription_chain
    from workers.base import JobContext
    from workers.transcription import TranscriptionWorker

    monkeypatch.setenv("STUB_PROVIDERS", "1")
    monkeypatch.setenv("ENV", "aws")
    monkeypatch.setenv("STUB_DELAY_S", "0")
    s = get_settings()
    monkeypatch.setattr(s, "DEEPGRAM_API_KEY", "dummy", raising=False)
    monkeypatch.setattr(s, "NAGA_AI_API_KEY", "dummy", raising=False)
    reset_ai_service()

    chain = build_transcription_chain(get_ai_service())
    assert [p.name for p in chain] == ["gemini"]

    expected = await ai_service.StubProvider().transcribe_audio(Path("x"), "audio/wav")

    class _ACM:
        async def __aenter__(self):
            return Path("x.mp3")

        async def __aexit__(self, *a):
            pass

    repo = AsyncMock()
    repo.get_by_id.return_value = MagicMock(audio_object_key="k", audio_mime="audio/mpeg")
    post = AsyncMock()
    job = JobDB(id="j", lecture_id="lec-1", stage="transcribe", version=1, status="processing")
    with patch("workers.transcription.LectureRepository", return_value=repo), \
         patch("workers.transcription.get_storage", return_value=MagicMock(open_local=lambda k: _ACM())), \
         patch("workers.transcription.get_duration_seconds", AsyncMock(return_value=10.0)), \
         patch.object(httpx.AsyncClient, "post", post):
        await TranscriptionWorker(max_jobs=1).process_job(job, JobContext("j", 1, None, "transcribe", "r", 300))
    stored = {k: v for c in repo.update_fields.call_args_list for k, v in c.args[1].items()}
    assert stored["transcript"] == expected
    post.assert_not_awaited()
