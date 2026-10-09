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
