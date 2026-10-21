"""LLM failover chain tests (fake clients, no network)."""
import asyncio
import json
import types

import pytest

import services.ai_service as m

VALID = json.dumps({"summary": "s", "smart_notes": ["n"], "key_concepts": ["c"],
                    "quiz": [], "flashcards": []})


def run(c):
    return asyncio.run(c)


@pytest.fixture(autouse=True)
def _reset():
    m.reset_ai_service()
    m.reset_cooldowns()
    yield
    m.reset_ai_service()
    m.reset_cooldowns()


class _HttpErr(Exception):
    def __init__(self, status, headers=None):
        super().__init__("http")
        self.status_code = status
        self.response = types.SimpleNamespace(headers=headers or {})


def _nim(content=None, exc=None, label="nim"):
    p = m.NIMProvider.__new__(m.NIMProvider)
    p.name, p._chat_model, p._embed_model, p._gemini = label, "model-x", "", None
    calls = []

    async def create(**kw):
        calls.append(kw)
        if exc:
            raise exc
        msg = types.SimpleNamespace(content=content)
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg, finish_reason="stop")])

    p._client = types.SimpleNamespace(
        chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=create))
    )
    p.calls = calls
    return p


# ── Task 1 ────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("content", [None, "   "])
def test_empty_content_raises(content):
    with pytest.raises(m.EmptyCompletion):
        run(_nim(content).generate_study_materials("t"))


def test_valid_json_parsed():
    assert run(_nim(VALID).generate_study_materials("t")).summary == "s"


def test_429_retry_after_both_paths():
    p = _nim(exc=_HttpErr(429, {"retry-after": "45"}))
    for coro in (p.generate_study_materials("t"), p.chat("t", [], "q")):
        with pytest.raises(m.ProviderRateLimited) as ei:
            run(coro)
        assert ei.value.retry_after == 45.0


def test_chat_messages_and_strip():
    p = _nim("  hi  ")
    assert run(p.chat("T", [{"role": "user", "content": "a"}], "q")) == "hi"
    kw = p.calls[0]
    assert [x["role"] for x in kw["messages"]] == ["system", "user", "user"]
    assert kw["max_tokens"] == 1024


def test_label_default_and_prompts():
    assert _nim(label="naga").name == "naga"
    for n in ("STUDY_PROMPT", "CHUNK_DIGEST_PROMPT", "HIERARCHICAL_MERGE_PROMPT",
              "CHEATSHEET_PROMPT", "PODCAST_SCRIPT_PROMPT", "QUIZ_V2_PROMPT", "CONCEPTS_V2_PROMPT"):
        assert "may mix Hindi" in getattr(m, n)


# ── Task 2 ────────────────────────────────────────────────────────────────
class _Fake(m.AIProvider):
    def __init__(self, exc=None, tag="x"):
        self.exc, self.tag, self.n = exc, tag, 0

    async def _go(self):
        self.n += 1
        if self.exc:
            raise self.exc
        return self.tag

    async def transcribe_audio(self, *a): return "T" + self.tag
    async def generate_study_materials(self, t): return await self._go()
    async def digest_chunk(self, t): return await self._go()
    async def merge_chunk_digests(self, d): return await self._go()
    async def chat(self, t, h, q): return await self._go()
    async def translate_pack(self, p, l): return await self._go()
    async def embed(self, t): return [self.tag]
    async def generate_cheatsheet(self, t): return await self._go()
    async def generate_podcast_script(self, t): return await self._go()
    async def generate_quiz_v2(self, t): return await self._go()
    async def generate_concepts_v2(self, t): return await self._go()


def _chain(a, b, c):
    return m.FailoverAIProvider([("naga", a), ("nim", b), ("gemini", c)], embedder=c)


def test_first_ok_only_first_used():
    a, b, c = _Fake(tag="a"), _Fake(tag="b"), _Fake(tag="c")
    assert run(_chain(a, b, c).digest_chunk("x")) == "a" and b.n == 0


def test_429_cooldown_skips_naga_next_call():
    a, b, c = _Fake(m.ProviderRateLimited("r", retry_after=30), "a"), _Fake(tag="b"), _Fake(tag="c")
    ch = _chain(a, b, c)
    assert run(ch.chat("t", [], "q")) == "b"
    assert m.cooldown_remaining("naga") > 0
    assert run(ch.chat("t", [], "q")) == "b" and a.n == 1


@pytest.mark.parametrize("exc", [m.EmptyCompletion("e"), json.JSONDecodeError("m", "d", 0),
                                 _HttpErr(503), NotImplementedError()])
def test_fall_through(exc):
    assert run(_chain(_Fake(exc, "a"), _Fake(tag="b"), _Fake(tag="c")).generate_cheatsheet("t")) == "b"


def test_all_methods_delegate():
    ch = _chain(_Fake(tag="a"), _Fake(tag="b"), _Fake(tag="c"))
    for coro in (ch.generate_study_materials("t"), ch.digest_chunk("t"), ch.merge_chunk_digests([]),
                 ch.chat("t", [], "q"), ch.translate_pack({}, "hi"), ch.generate_cheatsheet("t"),
                 ch.generate_podcast_script("t"), ch.generate_quiz_v2("t"), ch.generate_concepts_v2("t")):
        assert run(coro) == "a"


def test_all_rate_limited_min_retry_after():
    ch = _chain(*[_Fake(m.ProviderRateLimited("r", retry_after=r)) for r in (30, 10, 50)])
    with pytest.raises(m.ProviderRateLimited) as ei:
        run(ch.digest_chunk("t"))
    assert 0 < ei.value.retry_after <= 10


def test_all_runtime_error_reraises_last():
    ch = _chain(_Fake(RuntimeError("1")), _Fake(RuntimeError("2")), _Fake(RuntimeError("3")))
    with pytest.raises(RuntimeError, match="3"):
        run(ch.digest_chunk("t"))


def test_embed_transcribe_use_embedder():
    ch = _chain(_Fake(tag="a"), _Fake(tag="b"), _Fake(tag="c"))
    assert run(ch.embed("x")) == ["c"] and run(ch.transcribe_audio(None, "m")) == "Tc"


# factory
def _cfg(monkeypatch, **kw):
    base = dict(NAGA_AI_API_KEY="", NIM_API_KEY="", GEMINI_API_KEY="", AI_PROVIDER="nim",
                LLM_PROVIDERS=["naga", "nim", "gemini"], NAGA_BASE_URL="https://n/v1",
                NAGA_CHAT_MODEL="naga-model", NIM_BASE_URL="https://nim/v1",
                NIM_CHAT_MODEL="nim-model", NIM_EMBED_MODEL="e", LLM_TIMEOUT_S=5.0)
    base.update(kw)
    for k, v in base.items():
        monkeypatch.setattr(m.settings, k, v, raising=False)
    monkeypatch.delenv("STUB_PROVIDERS", raising=False)


def test_factory_chain(monkeypatch):
    _cfg(monkeypatch, NAGA_AI_API_KEY="k1", NIM_API_KEY="k2")
    p = m.get_ai_service()
    assert isinstance(p, m.FailoverAIProvider)
    assert [n for n, _ in p._members] == ["naga", "nim"]
    assert p._members[0][1]._chat_model == "naga-model"
    assert p._embedder is p._members[1][1]


def test_factory_radox_and_groq_join_chain_in_order(monkeypatch):
    _cfg(monkeypatch, NAGA_AI_API_KEY="k1", NIM_API_KEY="k2", RADOX_API_KEY="r",
         RADOX_CHAT_MODEL="radox-model", RADOX_BASE_URL="https://radoxai.com/v1",
         GROQ_API_KEY="g", GROQ_BASE_URL="https://groq/v1", GROQ_LLM_MODEL="groq-model",
         LLM_PROVIDERS=["naga", "radox", "groq", "nim"])
    p = m.get_ai_service()
    assert [n for n, _ in p._members] == ["naga", "radox", "groq", "nim"]
    models = {n: pr._chat_model for n, pr in p._members}
    assert models["radox"] == "radox-model" and models["groq"] == "groq-model"


def test_round_robin_spreads_calls_across_members():
    a, b, c = _Fake(tag="a"), _Fake(tag="b"), _Fake(tag="c")
    ch = m.FailoverAIProvider([("naga", a), ("nim", b), ("gemini", c)], embedder=c, rotate=True)
    assert [run(ch.chat("t", [], "q")) for _ in range(6)] == ["a", "b", "c", "a", "b", "c"]


def test_round_robin_still_fails_over(monkeypatch):
    a, c = _Fake(exc=RuntimeError("down"), tag="a"), _Fake(tag="c")
    ch = m.FailoverAIProvider([("naga", a), ("gemini", c)], embedder=c, rotate=True)
    assert [run(ch.chat("t", [], "q")) for _ in range(3)] == ["c", "c", "c"]


def test_priority_order_when_not_rotating():
    a, b = _Fake(tag="a"), _Fake(tag="b")
    ch = m.FailoverAIProvider([("naga", a), ("nim", b)], embedder=b)
    assert [run(ch.chat("t", [], "q")) for _ in range(3)] == ["a", "a", "a"]


def test_factory_openrouter_joins_chain(monkeypatch):
    _cfg(monkeypatch, NAGA_AI_API_KEY="k1", NIM_API_KEY="k2", OPENROUTER_API_KEY="o",
         OPENROUTER_BASE_URL="https://or/v1", OPENROUTER_CHAT_MODEL="or-model", GROQ_API_KEY="",
         LLM_PROVIDERS=["openrouter", "naga"])
    p = m.get_ai_service()
    assert [n for n, _ in p._members] == ["openrouter", "naga"]
    assert p._members[0][1]._chat_model == "or-model"


def test_factory_cloudflare_needs_token_and_account(monkeypatch):
    _cfg(monkeypatch, NAGA_AI_API_KEY="k1", NIM_API_KEY="k2", GROQ_API_KEY="", CLOUDFLARE_API_TOKEN="t",
         CLOUDFLARE_ACCOUNT_ID="", LLM_PROVIDERS=["cloudflare", "naga"])
    assert [n for n, _ in m.get_ai_service()._members] == ["naga"]
    m.reset_ai_service()
    _cfg(monkeypatch, NAGA_AI_API_KEY="k1", NIM_API_KEY="k2", GROQ_API_KEY="", CLOUDFLARE_API_TOKEN="t",
         CLOUDFLARE_ACCOUNT_ID="a", CLOUDFLARE_BASE_URL="https://cf/v1", CLOUDFLARE_CHAT_MODEL="@cf/x",
         CLOUDFLARE_CHAT_MODEL_2="@cf/y", LLM_PROVIDERS=["cloudflare", "cloudflare2", "naga"])
    p = m.get_ai_service()
    assert [n for n, _ in p._members] == ["cloudflare", "cloudflare2", "naga"]
    assert p._members[1][1]._chat_model == "@cf/y"
    assert p._members[0][1]._chat_model == "@cf/x"


def test_factory_radox_skipped_until_key_and_model_set(monkeypatch):
    # key without a model id must not build a provider that would fail on every call
    _cfg(monkeypatch, NAGA_AI_API_KEY="k1", NIM_API_KEY="k2", RADOX_API_KEY="r",
         RADOX_CHAT_MODEL="", GROQ_API_KEY="", LLM_PROVIDERS=["naga", "radox", "groq"])
    p = m.get_ai_service()
    assert [n for n, _ in p._members] == ["naga"]


def test_factory_single_unwrapped(monkeypatch):
    _cfg(monkeypatch, NIM_API_KEY="k2", LLM_PROVIDERS=["nim"])
    assert isinstance(m.get_ai_service(), m.NIMProvider)


def test_factory_stub_wins(monkeypatch):
    _cfg(monkeypatch, NAGA_AI_API_KEY="k1", NIM_API_KEY="k2")
    monkeypatch.setenv("STUB_PROVIDERS", "1")
    monkeypatch.setenv("ENV", "aws")
    assert isinstance(m.get_ai_service(), m.StubProvider)


def test_factory_missing_gemini_key(monkeypatch):
    _cfg(monkeypatch, AI_PROVIDER="gemini")
    with pytest.raises(RuntimeError, match="AI_PROVIDER=gemini but GEMINI_API_KEY is not set"):
        m.get_ai_service()
