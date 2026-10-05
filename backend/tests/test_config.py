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
