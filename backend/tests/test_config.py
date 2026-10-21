import pytest
from core.config import Settings

def test_config_features_defaults():
    s = Settings()
    assert s.FEATURE_FLASHCARDS_ENABLED is True
    assert s.FEATURE_RATE_LIMIT is False
    assert s.WORKER_POOL_SIZE == 10

def test_config_features_overrides(monkeypatch):
    monkeypatch.setenv("FEATURE_FLASHCARDS_ENABLED", "false")
    monkeypatch.setenv("FEATURE_RATE_LIMIT", "true")
    monkeypatch.setenv("WORKER_POOL_SIZE", "20")
    s = Settings()
    assert s.FEATURE_FLASHCARDS_ENABLED is False
    assert s.FEATURE_RATE_LIMIT is True
    assert s.WORKER_POOL_SIZE == 20


_P19 = ["DEEPGRAM_MODEL", "DEEPGRAM_LANGUAGE", "DEEPGRAM_KEYTERMS", "NAGA_CHAT_MODEL",
        "NAGA_WHISPER_MODEL", "NAGA_BASE_URL", "NIM_CHAT_MODEL", "NIM_EMBED_MODEL",
        "PROVIDER_COOLDOWN_SECONDS", "TRANSCRIPTION_PROVIDERS", "LLM_PROVIDERS",
        "NAGA_AI_API_KEY", "NAGA_API_KEY"]


def _clean(monkeypatch):
    for k in _P19:
        monkeypatch.delenv(k, raising=False)


def test_phase19_defaults(monkeypatch):
    _clean(monkeypatch)
    s = Settings()
    assert s.TRANSCRIPTION_PROVIDERS == ["deepgram", "naga", "gemini"]
    assert s.LLM_PROVIDERS == ["groq", "cloudflare", "cloudflare2", "cloudflare3", "openrouter", "naga", "radox", "gemini", "nim"]
    assert (s.DEEPGRAM_MODEL, s.DEEPGRAM_LANGUAGE, s.DEEPGRAM_KEYTERMS) == ("nova-3", "multi", [])
    assert s.NAGA_CHAT_MODEL == "nemotron-3-super-120b-a12b:free"
    assert s.NAGA_WHISPER_MODEL == "whisper-large-v3:free"
    assert s.NAGA_BASE_URL == "https://api.naga.ac/v1"
    assert s.NIM_CHAT_MODEL == "nvidia/nemotron-3-super-120b-a12b"
    assert s.NIM_EMBED_MODEL == "nvidia/nv-embed-v1"
    assert s.PROVIDER_COOLDOWN_SECONDS == 60.0


def test_phase19_key_name_and_lists(monkeypatch):
    _clean(monkeypatch)
    monkeypatch.setenv("NAGA_API_KEY", "wrong")
    assert Settings().NAGA_AI_API_KEY == ""
    monkeypatch.setenv("NAGA_AI_API_KEY", "x")
    monkeypatch.setenv("TRANSCRIPTION_PROVIDERS", " gemini , deepgram ")
    monkeypatch.setenv("LLM_PROVIDERS", "nim")
    s = Settings()
    assert s.NAGA_AI_API_KEY == "x"
    assert s.TRANSCRIPTION_PROVIDERS == ["gemini", "deepgram"]
    assert s.LLM_PROVIDERS == ["nim"]
