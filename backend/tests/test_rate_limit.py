"""Unit tests for Retry-After parsing and 429 conversion in ai_service and transcription_service."""

import email.utils
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from services.ai_service import (
    ProviderRateLimited,
    handle_rate_limit,
    parse_retry_after,
)
from services.transcription_service import WhisperProvider


class DummyResponse:
    def __init__(self, headers: dict | None = None):
        self.headers = headers or {}


class FakeErrorWithStatus(Exception):
    def __init__(
        self, message: str, status_code: int | None = None, headers: dict | None = None
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response = DummyResponse(headers) if headers is not None else None


class FakeErrorWithCode(Exception):
    def __init__(self, message: str, code: int | None = None):
        super().__init__(message)
        self.code = code


class RateLimitError(Exception):
    pass


def test_parse_retry_after_numeric_and_invalid():
    assert parse_retry_after("12") == 12.0
    assert parse_retry_after("12.5") == 12.5
    assert parse_retry_after("0") == 0.0
    assert parse_retry_after(None) is None
    assert parse_retry_after("") is None
    assert parse_retry_after("   ") is None
    assert parse_retry_after("garbage") is None
    assert parse_retry_after("-5") == 0.0


def test_parse_retry_after_http_date():
    future = datetime.now(timezone.utc) + timedelta(seconds=5)
    future_str = email.utils.format_datetime(future)
    val = parse_retry_after(future_str)
    assert val is not None
    assert 3.0 <= val <= 6.5

    past = datetime.now(timezone.utc) - timedelta(seconds=10)
    past_str = email.utils.format_datetime(past)
    assert parse_retry_after(past_str) == 0.0


@pytest.mark.asyncio
async def test_handle_rate_limit_status_code_429():
    @handle_rate_limit
    async def failing_func():
        raise FakeErrorWithStatus(
            "rate limited", status_code=429, headers={"retry-after": "7"}
        )

    with pytest.raises(ProviderRateLimited) as exc_info:
        await failing_func()

    assert exc_info.value.retry_after == 7.0
    assert "Provider rate limited" in str(exc_info.value)
    assert exc_info.value.__cause__ is not None


@pytest.mark.asyncio
async def test_handle_rate_limit_code_429_no_response():
    @handle_rate_limit
    async def failing_func():
        raise FakeErrorWithCode("rate limited", code=429)

    with pytest.raises(ProviderRateLimited) as exc_info:
        await failing_func()

    assert exc_info.value.retry_after is None
    assert "Provider rate limited" in str(exc_info.value)


@pytest.mark.asyncio
async def test_handle_rate_limit_rate_limit_error_class():
    @handle_rate_limit
    async def failing_func():
        raise RateLimitError("rate limit reached")

    with pytest.raises(ProviderRateLimited) as exc_info:
        await failing_func()

    assert exc_info.value.retry_after is None


@pytest.mark.asyncio
async def test_handle_rate_limit_no_substring_matching_500():
    @handle_rate_limit
    async def failing_func():
        # Exception message has "429" but status is 500
        raise FakeErrorWithStatus("Error 429 in backend system", status_code=500)

    with pytest.raises(FakeErrorWithStatus):
        await failing_func()


@pytest.mark.asyncio
async def test_handle_rate_limit_passthrough_existing_provider_rate_limited():
    @handle_rate_limit
    async def failing_func():
        raise ProviderRateLimited("Already wrapped", retry_after=15.0)

    with pytest.raises(ProviderRateLimited) as exc_info:
        await failing_func()

    assert exc_info.value.retry_after == 15.0
    assert str(exc_info.value) == "Already wrapped"


@pytest.mark.asyncio
async def test_whisper_provider_429_raises_provider_rate_limited(tmp_path: Path):
    audio = tmp_path / "test.mp3"
    audio.write_bytes(b"dummy audio data")

    provider = WhisperProvider(api_key="test-key")

    mock_resp = httpx.Response(
        status_code=429,
        headers={"retry-after": "3"},
        text="Rate limit exceeded",
        request=httpx.Request("POST", "https://api.groq.com"),
    )

    with patch(
        "httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp
    ):
        with pytest.raises(ProviderRateLimited) as exc_info:
            await provider.transcribe(audio, "audio/mpeg")

        assert exc_info.value.retry_after == 3.0
        assert "Groq Whisper rate limited" in str(exc_info.value)


@pytest.mark.asyncio
async def test_whisper_provider_500_raises_runtime_error(tmp_path: Path):
    audio = tmp_path / "test.mp3"
    audio.write_bytes(b"dummy audio data")

    provider = WhisperProvider(api_key="test-key")

    mock_resp = httpx.Response(
        status_code=500,
        text="Internal Server Error",
        request=httpx.Request("POST", "https://api.groq.com"),
    )

    with patch(
        "httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp
    ):
        with pytest.raises(RuntimeError) as exc_info:
            await provider.transcribe(audio, "audio/mpeg")

        assert "Groq Whisper API error 500" in str(exc_info.value)
