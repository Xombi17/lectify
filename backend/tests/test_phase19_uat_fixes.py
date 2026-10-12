"""Phase 19 UAT gap fixes: embed model config + Neo4j outage cooldown."""
import logging
from types import SimpleNamespace

import pytest

from services import neo4j_service as n4


def test_gemini_embed_uses_configured_model_and_768_dims(monkeypatch):
    import asyncio
    from services import ai_service
    calls = {}

    class Models:
        def embed_content(self, **kw):
            calls.update(kw)
            return SimpleNamespace(embeddings=[SimpleNamespace(values=[0.1] * 768)])

    p = ai_service.GeminiProvider.__new__(ai_service.GeminiProvider)
    p._client = SimpleNamespace(models=Models())
    out = asyncio.run(p.embed("hi"))
    assert len(out) == 768
    assert calls["model"] == ai_service.get_settings().GEMINI_EMBED_MODEL == "gemini-embedding-001"
    assert calls["config"].output_dimensionality == 768


def test_neo4j_unreachable_warns_once_then_fast_fails(monkeypatch, caplog):
    attempts = []

    class Boom:
        def __new__(cls):
            attempts.append(1)
            raise ConnectionError("no route")

    monkeypatch.setattr(n4, "Neo4jService", Boom)
    Boom._instance = None
    monkeypatch.setattr(n4, "_down_until", 0.0)
    with caplog.at_level(logging.WARNING, logger=n4.logger.name):
        for _ in range(3):
            with pytest.raises(n4.Neo4jUnavailable):
                n4.get_neo4j_service()
    assert len(attempts) == 1
    assert len([r for r in caplog.records if r.levelno >= logging.WARNING]) == 1
    assert not any(r.exc_info for r in caplog.records)


@pytest.mark.asyncio
async def test_gemini_upload_uses_ascii_path_for_unicode_filename(tmp_path):
    """SDK puts the file name in an HTTP header (ASCII only); unicode names must be symlinked."""
    from types import SimpleNamespace
    from services.ai_service import GeminiProvider

    real = tmp_path / "L-3.9： Semaphore ｜ x.mp3"
    real.write_bytes(b"x")
    seen = {}

    def fake_upload(file, config):
        seen["name"] = file
        return SimpleNamespace()

    p = GeminiProvider.__new__(GeminiProvider)
    p._client = SimpleNamespace(files=SimpleNamespace(upload=fake_upload))
    p._generate = lambda contents, **kw: SimpleNamespace(text="ok")
    assert await p.transcribe_audio(real, "audio/mpeg") == "ok"
    assert seen["name"].isascii()
