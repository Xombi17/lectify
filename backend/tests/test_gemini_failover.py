"""Gemini model-failover tests (mocked client, no network)."""
import asyncio
import sys
import types as pytypes

import pytest

sys.path.insert(0, "/app/backend")


def _load_ai_service():
    """Import ai_service with a stubbed google.genai (lazy import inside methods)."""
    import importlib
    import services.ai_service as m

    importlib.reload(m)
    return m


class _FakeResponse:
    def __init__(self, text):
        self.text = text


class _ApiError(Exception):
    def __init__(self, code, message="boom"):
        super().__init__(message)
        self.code = code


class _FakeModels:
    def __init__(self, behaviors):
        # behaviors: {model_name: ("ok", text) | ("fail", code)}
        self.behaviors = behaviors
        self.calls = []

    def generate_content(self, model, contents, config=None):
        self.calls.append(model)
        kind, payload = self.behaviors[model]
        if kind == "ok":
            return _FakeResponse(payload)
        raise _ApiError(payload)


class _FakeClient:
    def __init__(self, behaviors):
        self.models = _FakeModels(behaviors)


def _arun(coro):
    return asyncio.run(coro)


class TestModelFailover:
    def test_falls_over_on_503_then_succeeds(self):
        m = _load_ai_service()
        provider = m.GeminiProvider.__new__(m.GeminiProvider)
        provider._client = _FakeClient({
            "primary": ("fail", 503),
            "fallback": ("ok", "hello"),
        })
        provider._model = "primary"
        provider._models = ["primary", "fallback"]

        async def go():
            resp = provider._generate(contents="hi")
            assert resp.text == "hello"
        _arun(go())
        assert provider._client.models.calls == ["primary", "fallback"]

    def test_unknown_model_id_skipped(self):
        m = _load_ai_service()
        provider = m.GeminiProvider.__new__(m.GeminiProvider)
        provider._client = _FakeClient({
            "nope": ("fail", 404),
            "fallback": ("ok", "hi"),
        })
        provider._model = "nope"
        provider._models = ["nope", "fallback"]

        async def go():
            assert provider._generate(contents="hi").text == "hi"
        _arun(go())

    def test_all_overloaded_raises_rate_limited(self):
        m = _load_ai_service()
        provider = m.GeminiProvider.__new__(m.GeminiProvider)
        provider._client = _FakeClient({
            "a": ("fail", 503),
            "b": ("fail", 429),
        })
        provider._model = "a"
        provider._models = ["a", "b"]

        async def go():
            with pytest.raises(m.ProviderRateLimited):
                provider._generate(contents="hi")
        _arun(go())

    def test_non_retryable_fails_fast_without_fallback(self):
        m = _load_ai_service()
        provider = m.GeminiProvider.__new__(m.GeminiProvider)
        provider._client = _FakeClient({
            "a": ("fail", 400),
            "b": ("ok", "hi"),
        })
        provider._model = "a"
        provider._models = ["a", "b"]

        async def go():
            with pytest.raises(_ApiError):
                provider._generate(contents="hi")
        _arun(go())
        assert provider._client.models.calls == ["a"]

    def test_single_model_unchanged(self):
        m = _load_ai_service()
        provider = m.GeminiProvider.__new__(m.GeminiProvider)
        provider._client = _FakeClient({"only": ("ok", "yo")})
        provider._model = "only"
        provider._models = ["only"]

        async def go():
            assert provider._generate(contents="hi").text == "yo"
        _arun(go())
