import pytest
from fastapi.testclient import TestClient
from server import app
import os
from core.config import Settings

client = TestClient(app)

def test_signup_role_admin_rejected():
    response = client.post(
        "/api/auth/signup",
        json={"email": "admin@example.com", "password": "password", "name": "Admin", "role": "admin"}
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Role not permitted for public signup"

from unittest.mock import patch

@patch("routes.auth.UserRepository")
def test_signup_role_student_allowed(mock_repo):
    mock_instance = mock_repo.return_value
    from unittest.mock import AsyncMock
    mock_instance.get_by_email = AsyncMock(return_value=None)
    mock_instance.create = AsyncMock()
    mock_instance.new_id.return_value = "usr_123"
    
    response = client.post(
        "/api/auth/signup",
        json={"email": "student123@example.com", "password": "password", "name": "Student", "role": "student"}
    )
    assert response.status_code == 201

def test_settings_validate_jwt_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "change-me")
    monkeypatch.setenv("ENV", "production")
    s = Settings()
    print("DEBUG:", s.ENV, s.JWT_SECRET)
    with pytest.raises(RuntimeError, match="JWT_SECRET must be set in production"):
        s.validate()

def test_settings_validate_jwt_secret_dev(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "change-me")
    monkeypatch.setenv("ENV", "dev")
    Settings().validate()

def test_settings_validate_cors(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://example.com,*")
    monkeypatch.setenv("ENV", "production")
    with pytest.raises(RuntimeError, match="CORS_ORIGINS cannot contain '\\*' in production"):
        Settings().validate()

def test_settings_validate_cors_dev(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://example.com,*")
    monkeypatch.setenv("ENV", "dev")
    Settings().validate()
