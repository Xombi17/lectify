"""Tests for shallow /healthz and DB_AUTO_CREATE lifespan gate."""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from server import app, lifespan
from core.config import Settings, get_settings


def test_healthz_shallow():
    """GET /healthz returns 200 ok without calling DB or storage."""
    with patch("core.sql_db.session_maker", side_effect=RuntimeError("DB must not be called")):
        with patch("services.storage_service.get_storage", side_effect=RuntimeError("Storage must not be called")):
            client = TestClient(app)
            response = client.get("/healthz")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}


def test_healthz_not_under_api():
    """Verify that /api/healthz does not exist, but /healthz does."""
    client = TestClient(app)
    response = client.get("/api/healthz")
    assert response.status_code == 404


def test_settings_db_auto_create(monkeypatch):
    """Settings.DB_AUTO_CREATE parses boolean from env correctly."""
    monkeypatch.setenv("DB_AUTO_CREATE", "false")
    s = Settings()
    assert s.DB_AUTO_CREATE is False

    monkeypatch.setenv("DB_AUTO_CREATE", "true")
    s2 = Settings()
    assert s2.DB_AUTO_CREATE is True

    monkeypatch.delenv("DB_AUTO_CREATE", raising=False)
    s3 = Settings()
    assert s3.DB_AUTO_CREATE is True


@pytest.mark.asyncio
async def test_lifespan_skips_init_models_when_db_auto_create_false(monkeypatch):
    """Lifespan skips init_models when DB_AUTO_CREATE=false."""
    mock_init = AsyncMock()
    with patch("server.init_models", mock_init):
        with patch("server.settings.DB_AUTO_CREATE", False):
            # Run lifespan context manager with background tasks cancelled cleanly
            with patch("server.asyncio.create_task") as mock_task:
                mock_task.return_value = MagicMock()
                with patch("server.close_sql", AsyncMock()):
                    async with lifespan(app):
                        pass
            mock_init.assert_not_called()


@pytest.mark.asyncio
async def test_lifespan_calls_init_models_when_db_auto_create_true():
    """Lifespan calls init_models when DB_AUTO_CREATE=true."""
    mock_init = AsyncMock()
    with patch("server.init_models", mock_init):
        with patch("server.settings.DB_AUTO_CREATE", True):
            with patch("server.UserRepository.ensure_indexes", AsyncMock()):
                with patch("server.LectureRepository.ensure_indexes", AsyncMock()):
                    with patch("server.ChatRepository.ensure_indexes", AsyncMock()):
                        with patch("server.AttemptRepository.ensure_indexes", AsyncMock()):
                            with patch("server.asyncio.create_task") as mock_task:
                                mock_task.return_value = MagicMock()
                                with patch("server.close_sql", AsyncMock()):
                                    async with lifespan(app):
                                        pass
            mock_init.assert_called_once()
