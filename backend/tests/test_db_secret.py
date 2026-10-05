"""Unit tests for AWS Secrets Manager DB URL composition."""
import json
import os
from unittest.mock import MagicMock
import pytest

from core.db_secret import apply_db_secret_overlay


def test_overlay_returns_false_when_database_url_already_set(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://existing:5432/db")
    monkeypatch.setenv("DB_SECRET_ARN", "arn:aws:secretsmanager:us-east-1:123456789012:secret:db-123")
    monkeypatch.setenv("DB_HOST", "db.internal")
    mock_client = MagicMock()
    
    result = apply_db_secret_overlay(client=mock_client)
    
    assert result is False
    mock_client.get_secret_value.assert_not_called()
    assert os.environ["DATABASE_URL"] == "postgresql+asyncpg://existing:5432/db"


def test_overlay_returns_false_when_arn_unset(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DB_SECRET_ARN", raising=False)
    mock_client = MagicMock()

    result = apply_db_secret_overlay(client=mock_client)

    assert result is False
    mock_client.get_secret_value.assert_not_called()


def test_overlay_composes_database_url_with_defaults(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DB_SECRET_ARN", "arn:aws:secretsmanager:us-east-1:123:secret:rds")
    monkeypatch.setenv("DB_HOST", "rds.example.com")
    monkeypatch.delenv("DB_PORT", raising=False)
    monkeypatch.delenv("DATABASE_NAME", raising=False)

    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {
        "SecretString": json.dumps({"username": "lectify_user", "password": "supersecretpassword"})
    }

    result = apply_db_secret_overlay(client=mock_client)

    assert result is True
    assert os.environ["DATABASE_URL"] == "postgresql+asyncpg://lectify_user:supersecretpassword@rds.example.com:5432/postgres?ssl=require"


def test_overlay_encodes_special_characters_in_credentials(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DB_SECRET_ARN", "arn:aws:secretsmanager:us-east-1:123:secret:rds")
    monkeypatch.setenv("DB_HOST", "rds.example.com")
    monkeypatch.setenv("DB_PORT", "5433")
    monkeypatch.setenv("DATABASE_NAME", "lectify_prod")

    special_pass = "p@ss:w/o#rd?123"
    special_user = "user/admin@domain"

    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {
        "SecretString": json.dumps({"username": special_user, "password": special_pass})
    }

    result = apply_db_secret_overlay(client=mock_client)

    assert result is True
    # Verify percent encoding
    assert "@" not in os.environ["DATABASE_URL"].split("@rds.example.com")[0]
    expected_url = (
        "postgresql+asyncpg://user%2Fadmin%40domain:p%40ss%3Aw%2Fo%23rd%3F123@rds.example.com:5433/lectify_prod?ssl=require"
    )
    assert os.environ["DATABASE_URL"] == expected_url


def test_overlay_fails_without_db_host(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DB_SECRET_ARN", "arn:aws:secretsmanager:us-east-1:123:secret:rds")
    monkeypatch.delenv("DB_HOST", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        apply_db_secret_overlay(client=MagicMock())
    assert "DB_HOST environment variable is not set" in str(exc_info.value)


def test_overlay_redacts_password_on_error(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DB_SECRET_ARN", "arn:aws:secretsmanager:us-east-1:123:secret:rds")
    monkeypatch.setenv("DB_HOST", "rds.example.com")

    sensitive_pass = "ultra_sensitive_secret_phrase"
    mock_client = MagicMock()
    # Missing username key
    mock_client.get_secret_value.return_value = {
        "SecretString": json.dumps({"password": sensitive_pass})
    }

    with pytest.raises(RuntimeError) as exc_info:
        apply_db_secret_overlay(client=mock_client)
    
    err_str = str(exc_info.value)
    assert "DB secret overlay failed" in err_str
    assert sensitive_pass not in err_str


def test_overlay_propagates_client_error(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("DB_SECRET_ARN", "arn:aws:secretsmanager:us-east-1:123:secret:rds")
    monkeypatch.setenv("DB_HOST", "rds.example.com")

    mock_client = MagicMock()
    mock_client.get_secret_value.side_effect = Exception("AWS Service unavailable")

    with pytest.raises(RuntimeError) as exc_info:
        apply_db_secret_overlay(client=mock_client)
    assert "AWS Service unavailable" in str(exc_info.value)
