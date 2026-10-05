import os
from unittest.mock import AsyncMock, patch

import pytest
from core.config import Settings
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from server import app

    return TestClient(app)


def test_signup_role_admin_rejected(client):
    response = client.post(
        "/api/auth/signup",
        json={
            "email": "admin@example.com",
            "password": "password",
            "name": "Admin",
            "role": "admin",
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Role not permitted for public signup"


@patch("routes.auth.UserRepository")
def test_signup_role_student_allowed(mock_repo, client):
    mock_instance = mock_repo.return_value
    mock_instance.get_by_email = AsyncMock(return_value=None)
    mock_instance.create = AsyncMock()
    mock_instance.new_id.return_value = "usr_123"

    response = client.post(
        "/api/auth/signup",
        json={
            "email": "student123@example.com",
            "password": "password",
            "name": "Student",
            "role": "student",
        },
    )
    assert response.status_code == 201


def test_settings_validate_jwt_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "change-me")
    monkeypatch.setenv("ENV", "production")
    s = Settings()
    with pytest.raises(RuntimeError, match="JWT_SECRET must be set in production"):
        s.validate()


def test_settings_validate_jwt_secret_dev(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "change-me")
    monkeypatch.setenv("ENV", "dev")
    Settings().validate()


def test_settings_validate_cors(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://example.com,*")
    monkeypatch.setenv("ENV", "production")
    with pytest.raises(
        RuntimeError, match="CORS_ORIGINS cannot contain '\\*' in production"
    ):
        Settings().validate()


def test_settings_validate_cors_dev(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://example.com,*")
    monkeypatch.setenv("ENV", "dev")
    Settings().validate()


def test_settings_validate_env_unset_jwt_secret_fails(monkeypatch):
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="JWT_SECRET must be set in production"):
        Settings().validate()


def test_settings_validate_env_unset_cors_wildcard_fails(monkeypatch):
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.setenv("JWT_SECRET", "strong-secret-prod-12345")
    monkeypatch.setenv("CORS_ORIGINS", "*")
    with pytest.raises(
        RuntimeError, match="CORS_ORIGINS cannot contain '\\*' in production"
    ):
        Settings().validate()


def test_settings_validate_env_unset_strong_secret_passes(monkeypatch):
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.setenv("JWT_SECRET", "strong-secret-prod-12345")
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    s = Settings().validate()
    assert s.ENV == "production"


def test_settings_validate_local_and_dev_bypasses(monkeypatch):
    for env in ("local", "dev", "test"):
        monkeypatch.setenv("ENV", env)
        monkeypatch.setenv("JWT_SECRET", "change-me")
        monkeypatch.setenv("CORS_ORIGINS", "*")
        Settings().validate()


def test_settings_env_unset_neo4j_slack_defaults(monkeypatch):
    monkeypatch.delenv("ENV", raising=False)
    s = Settings()
    assert s.NEO4J_SYNC_ENABLED is False
    assert s.SLACK_SUMMARY_ENABLED is False
    monkeypatch.setenv("ENV", "dev")
    s_dev = Settings()
    assert s_dev.NEO4J_SYNC_ENABLED is True
    assert s_dev.SLACK_SUMMARY_ENABLED is True
