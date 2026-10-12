"""Deepgram / Naga providers + STT failover chain (all HTTP mocked)."""
import logging
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from core.config import get_settings
from services import ai_service, transcription_service as ts

pytestmark = pytest.mark.asyncio(loop_scope="function")

KEY = "dg-test-key"
URL = "https://example.test"

DG_PAYLOAD = {
    "metadata": {"duration": 600},
    "results": {
        "channels": [
            {
                "detected_language": "en-US-verylong",
                "alternatives": [
                    {
                        "transcript": "hello class today we learn graphs and trees",
                        "confidence": 0.9,
                        "paragraphs": {
                            "paragraphs": [
                                {"start": 0.0, "end": 5.0, "sentences": [{"text": "Hello class."}, {"text": "Today graphs."}]},
                                {"start": 65.0, "end": 70.0, "sentences": [{"text": "Now trees."}]},
                            ]
                        },
                    }
                ],
            }
        ],
        "utterances": [
            {"start": 0, "end": 2, "confidence": 0.9, "transcript": "Hello class."},
            {"start": 2, "end": 5, "confidence": 0.8, "transcript": "Today graphs."},
            {"start": 65, "end": 70, "confidence": 0.4, "transcript": "Now trees."},
        ],
    },
}


def _resp(status=200, json=None, text=None, headers=None):
    kw = {"json": json} if json is not None else {"text": text or ""}
    return httpx.Response(status, headers=headers, request=httpx.Request("POST", URL), **kw)


def _post(resp):
    return patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=resp)


@pytest.fixture
def audio(tmp_path: Path):
    f = tmp_path / "a.mp3"
    f.write_bytes(b"dummy audio")
    return f


@pytest.fixture(autouse=True)
def _cooldowns():
    ai_service.reset_cooldowns()
    yield
    ai_service.reset_cooldowns()


@pytest.fixture
def dg():
    return ts.DeepgramProvider(KEY, "nova-3", "multi", [], 30.0)


# ── Deepgram ──────────────────────────────────────────────────────────────────


async def test_deepgram_maps_response(audio, dg):
    with _post(_resp(json=DG_PAYLOAD)):
        r = await dg.transcribe(audio, "audio/mpeg")
    assert r.text.split("\n\n") == ["[00:00] Hello class. Today graphs.", "[01:05] Now trees."]
    assert [(s.start, s.end, s.confidence) for s in r.segments] == [(0, 2, 0.9), (2, 5, 0.8), (65, 70, 0.4)]
    assert r.confidence == round((0.9 + 0.8 + 0.4) / 3, 4)
    assert r.duration_seconds == 600
    assert r.provider == "deepgram"
    assert r.cost_usd == round(10 * get_settings().DEEPGRAM_COST_PER_MINUTE, 6)
    assert r.word_count == 8
    assert len(r.language) <= 10
    assert [f["index"] for f in ts.flag_low_confidence_segments(r)] == [2]


async def test_deepgram_without_paragraphs_uses_plain(audio, dg):
    payload = {
        "metadata": {"duration": 60},
        "results": {"channels": [{"alternatives": [{"transcript": "plain words here", "languages": ["hi"]}]}]},
    }
    with _post(_resp(json=payload)):
        r = await dg.transcribe(audio, "audio/mpeg", language="en")
    assert r.text == "plain words here"
    assert r.language == "hi"
    assert r.segments == []


async def test_deepgram_request_shape(audio):
    p = ts.DeepgramProvider(KEY, "nova-3", "multi", ["Dijkstra", "AVL"], 30.0)
    with _post(_resp(json=DG_PAYLOAD)) as m:
        await p.transcribe(audio, "audio/wav")
    kw = m.call_args.kwargs
    params = kw["params"]
    assert ("model", "nova-3") in params and ("language", "multi") in params
    for k in ("smart_format", "paragraphs", "utterances", "diarize"):
        assert (k, "true") in params
    assert [v for k, v in params if k == "keyterm"] == ["Dijkstra", "AVL"]
    assert kw["headers"]["Authorization"] == f"Token {KEY}"
    assert kw["headers"]["Content-Type"] == "audio/wav"
    assert kw["headers"]["Content-Length"] == str(audio.stat().st_size)


async def test_deepgram_no_keyterm_param_when_empty(audio, dg):
    with _post(_resp(json=DG_PAYLOAD)) as m:
        await dg.transcribe(audio, "audio/mpeg")
    assert not [k for k, _ in m.call_args.kwargs["params"] if k == "keyterm"]


async def test_deepgram_429(audio, dg):
    with _post(_resp(429, text="slow down", headers={"retry-after": "7"})):
        with pytest.raises(ai_service.ProviderRateLimited) as e:
            await dg.transcribe(audio, "audio/mpeg")
    assert e.value.retry_after == 7.0


async def test_deepgram_500_hides_key(audio, dg):
    with _post(_resp(500, text="boom")):
        with pytest.raises(RuntimeError) as e:
            await dg.transcribe(audio, "audio/mpeg")
    assert "500" in str(e.value) and KEY not in str(e.value)


async def test_deepgram_empty_transcript(audio, dg):
    empty = {"results": {"channels": [{"alternatives": [{"transcript": ""}]}]}}
    with _post(_resp(json=empty)):
        with pytest.raises(RuntimeError):
            await dg.transcribe(audio, "audio/mpeg")


# ── Naga ──────────────────────────────────────────────────────────────────────


@pytest.fixture
def naga():
    return ts.NagaWhisperProvider("naga-key", "https://naga.test/v1/", "whisper-large-v3:free")


async def test_naga_ok(audio, naga):
    with _post(_resp(json={"text": "namaste class"})) as m:
        r = await naga.transcribe(audio, "audio/mpeg")
    assert (r.provider, r.confidence, r.segments, r.cost_usd, r.text) == ("naga", 0.0, [], 0.0, "namaste class")
    assert m.call_args.args[0] == "https://naga.test/v1/audio/transcriptions"
    assert m.call_args.kwargs["data"]["model"] == "whisper-large-v3:free"


async def test_naga_too_large_no_http(tmp_path, naga):
    big = tmp_path / "big.mp3"
    with open(big, "wb") as f:
        f.truncate(20 * 1024 * 1024 + 1)
    with _post(_resp(json={"text": "x"})) as m:
        with pytest.raises(ValueError):
            await naga.transcribe(big, "audio/mpeg")
    m.assert_not_awaited()


async def test_naga_429_and_500(audio, naga):
    with _post(_resp(429, text="limit", headers={"retry-after": "2"})):
        with pytest.raises(ai_service.ProviderRateLimited):
            await naga.transcribe(audio, "audio/mpeg")
    with _post(_resp(500, text="boom")):
        with pytest.raises(RuntimeError) as e:
            await naga.transcribe(audio, "audio/mpeg")
    assert "naga-key" not in str(e.value)


# ── Failover ──────────────────────────────────────────────────────────────────


def _result(text="ok", provider="x"):
    return ts.TranscriptionResult(
        text=text, language="en", confidence=0.0, duration_seconds=60.0,
        word_count=len(text.split()), provider=provider, cost_usd=0.0,
    )


class Fake:
    whole_file = False

    def __init__(self, name, outcome):
        self.name = name
        self.outcome = outcome
        self.calls = 0

    async def transcribe(self, audio_path, mime_type, language=None):
        self.calls += 1
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


async def test_failover_first_ok_logs_cost(audio):
    a, b = Fake("a", _result("A text")), Fake("b", _result("B"))
    with patch.object(ts, "log_transcription_cost") as cost:
        r = await ts.transcribe_with_failover([a, b], audio, "audio/mpeg", "lec1")
    assert r.text == "A text" and b.calls == 0
    cost.assert_called_once()
    assert cost.call_args.args[:2] == ("lec1", "a")


@pytest.mark.parametrize(
    "bad",
    [RuntimeError("x"), _result("  "), httpx.TimeoutException("t"), ValueError("big")],
)
async def test_failover_on_failure(audio, bad):
    a, b = Fake("a", bad), Fake("b", _result("B text"))
    r = await ts.transcribe_with_failover([a, b], audio, "audio/mpeg", "l")
    assert r.text == "B text"


async def test_failover_rate_limited_all(audio):
    a = Fake("a", ai_service.ProviderRateLimited("rl", retry_after=30))
    b = Fake("b", RuntimeError("down"))
    with pytest.raises(ai_service.ProviderRateLimited) as e:
        await ts.transcribe_with_failover([a, b], audio, "audio/mpeg", "l")
    assert 0 < e.value.retry_after <= 30
    assert ai_service.cooldown_remaining("a") > 0


async def test_failover_skips_cooled_down(audio):
    ai_service.mark_cooldown("a", 60)
    a, b = Fake("a", _result("A")), Fake("b", _result("B"))
    r = await ts.transcribe_with_failover([a, b], audio, "audio/mpeg", "l")
    assert a.calls == 0 and r.text == "B"


async def test_failover_reraises_last(audio):
    a, b = Fake("a", RuntimeError("first")), Fake("b", RuntimeError("second"))
    with pytest.raises(RuntimeError, match="second"):
        await ts.transcribe_with_failover([a, b], audio, "audio/mpeg", "l")


async def test_failover_empty_list(audio):
    with pytest.raises(RuntimeError):
        await ts.transcribe_with_failover([], audio, "audio/mpeg", "l")


# ── Chain builder ─────────────────────────────────────────────────────────────


@pytest.fixture
def settings(monkeypatch):
    import core.config as cfg

    s = cfg.get_settings()
    monkeypatch.setattr(s, "DEEPGRAM_API_KEY", "dg")
    monkeypatch.setattr(s, "NAGA_AI_API_KEY", "ng")
    monkeypatch.setattr(s, "TRANSCRIPTION_PROVIDERS", ["deepgram", "naga", "gemini"])
    monkeypatch.delenv("STUB_PROVIDERS", raising=False)
    return s


def _types(chain):
    return [type(p) for p in chain]


def test_chain_full_order(settings):
    assert _types(ts.build_transcription_chain(object())) == [
        ts.DeepgramProvider, ts.NagaWhisperProvider, ts.GeminiFallbackProvider,
    ]


def test_chain_no_keys_is_gemini(settings, monkeypatch):
    monkeypatch.setattr(settings, "DEEPGRAM_API_KEY", "")
    monkeypatch.setattr(settings, "NAGA_AI_API_KEY", "")
    assert _types(ts.build_transcription_chain(object())) == [ts.GeminiFallbackProvider]


def test_chain_unknown_skipped_with_warning(settings, monkeypatch, caplog):
    monkeypatch.setattr(settings, "TRANSCRIPTION_PROVIDERS", ["foo", "naga"])
    with caplog.at_level(logging.WARNING):
        chain = ts.build_transcription_chain(object())
    assert _types(chain) == [ts.NagaWhisperProvider]
    assert "foo" in caplog.text


def test_chain_never_empty_without_gemini(settings, monkeypatch):
    monkeypatch.setattr(settings, "TRANSCRIPTION_PROVIDERS", ["deepgram"])
    monkeypatch.setattr(settings, "DEEPGRAM_API_KEY", "")
    assert _types(ts.build_transcription_chain(object())) == [ts.GeminiFallbackProvider]


async def test_chain_stub_mode_gemini_only(settings, monkeypatch, audio):
    monkeypatch.setenv("STUB_PROVIDERS", "1")
    monkeypatch.setenv("ENV", "aws")
    with _post(_resp(json=DG_PAYLOAD)) as m:
        chain = ts.build_transcription_chain(object())
    assert _types(chain) == [ts.GeminiFallbackProvider]
    m.assert_not_awaited()
