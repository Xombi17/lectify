"""Tests for transcription service — Whisper provider, confidence scoring, cost tracking.

All real API calls are mocked. Tests verify:
- TranscriptionResult model construction
- WhisperProvider initialization and configuration
- Confidence scoring and low-confidence flagging
- Cost estimation
- GeminiFallbackProvider behavior
- Integration with lecture pipeline
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path


class TestTranscriptionResult:
    """Test TranscriptionResult model."""

    def test_create_result_with_segments(self):
        from services.transcription_service import TranscriptionResult, TranscriptionSegment

        segments = [
            TranscriptionSegment(start=0.0, end=2.5, text="Hello world", confidence=0.95),
            TranscriptionSegment(start=2.5, end=5.0, text="Test lecture", confidence=0.88),
        ]
        result = TranscriptionResult(
            text="Hello world Test lecture",
            language="en",
            confidence=0.915,
            duration_seconds=5.0,
            word_count=4,
            segments=segments,
            provider="whisper",
            cost_usd=0.0005,
        )
        assert result.text == "Hello world Test lecture"
        assert result.language == "en"
        assert result.confidence == 0.915
        assert len(result.segments) == 2
        assert result.provider == "whisper"

    def test_result_defaults(self):
        from services.transcription_service import TranscriptionResult

        result = TranscriptionResult(
            text="test",
            language="en",
            confidence=0.9,
            duration_seconds=1.0,
            word_count=1,
            provider="whisper",
            cost_usd=0.0,
        )
        assert result.segments == []


class TestConfidenceScoring:
    """Test confidence threshold flagging."""

    def test_flag_low_confidence_segments(self):
        from services.transcription_service import (
            TranscriptionResult,
            TranscriptionSegment,
            flag_low_confidence_segments,
        )

        segments = [
            TranscriptionSegment(start=0, end=1, text="clear", confidence=0.95),
            TranscriptionSegment(start=1, end=2, text="unclear", confidence=0.5),
            TranscriptionSegment(start=2, end=3, text="clear again", confidence=0.92),
        ]
        result = TranscriptionResult(
            text="clear unclear clear again",
            language="en",
            confidence=0.79,
            duration_seconds=3.0,
            word_count=4,
            segments=segments,
            provider="whisper",
            cost_usd=0.0,
        )

        flagged = flag_low_confidence_segments(result, threshold=0.7)
        assert len(flagged) == 1
        assert flagged[0]["index"] == 1
        assert flagged[0]["confidence"] == 0.5

    def test_no_flagging_when_all_confident(self):
        from services.transcription_service import (
            TranscriptionResult,
            TranscriptionSegment,
            flag_low_confidence_segments,
        )

        segments = [
            TranscriptionSegment(start=0, end=1, text="clear", confidence=0.95),
        ]
        result = TranscriptionResult(
            text="clear",
            language="en",
            confidence=0.95,
            duration_seconds=1.0,
            word_count=1,
            segments=segments,
            provider="whisper",
            cost_usd=0.0,
        )

        flagged = flag_low_confidence_segments(result)
        assert len(flagged) == 0


class TestCostEstimation:
    """Test cost calculation."""

    def test_whisper_cost_estimation(self):
        from services.transcription_service import WhisperProvider

        provider = WhisperProvider(api_key="test-key")

        # 60 seconds = 1 minute at $0.00067/min (whisper-large-v3-turbo default)
        cost = provider.estimate_cost(60.0)
        assert abs(cost - 0.00067) < 0.0001

        # 30 minutes = $0.0201
        cost = provider.estimate_cost(30 * 60)
        assert abs(cost - 0.0201) < 0.001

    def test_gemini_fallback_cost_zero(self):
        from services.transcription_service import GeminiFallbackProvider

        mock_ai = MagicMock()
        provider = GeminiFallbackProvider(mock_ai)

        cost = provider.estimate_cost(60.0)
        assert cost == 0.0


class TestWhisperProvider:
    """Test WhisperProvider initialization."""

    def test_init_with_defaults(self):
        from services.transcription_service import WhisperProvider

        provider = WhisperProvider(api_key="test-key")
        assert provider._api_key == "test-key"
        assert provider._model == "whisper-large-v3-turbo"  # Default: fastest/cheapest Groq model
        assert provider._default_language == "en"

    def test_init_with_custom_config(self):
        from services.transcription_service import WhisperProvider

        provider = WhisperProvider(
            api_key="custom-key",
            model="whisper-large-v3",  # Alternative to the default turbo
            language="hi",
        )
        assert provider._model == "whisper-large-v3"
        assert provider._default_language == "hi"


class TestGeminiFallback:
    """Test Gemini fallback provider."""

    @pytest.mark.asyncio
    async def test_fallback_returns_transcription_result(self):
        from services.transcription_service import GeminiFallbackProvider

        mock_ai = AsyncMock()
        mock_ai.transcribe_audio.return_value = "Hello from Gemini"

        provider = GeminiFallbackProvider(mock_ai)
        result = await provider.transcribe(
            Path("/tmp/test.mp3"),
            "audio/mpeg",
            language="en",
        )

        assert result.text == "Hello from Gemini"
        assert result.provider == "gemini"
        assert result.confidence == 0.0
        assert result.language == "en"


class TestLecturePipelineIntegration:
    """Test integration with lecture processing pipeline."""

    def test_lecture_model_has_new_fields(self):
        from models.lecture import LectureDB

        lecture = LectureDB(
            id="test-id",
            teacher_id="teacher-id",
            title="Test Lecture",
            audio_object_key="lectures/test/audio.mp3",
            audio_filename="audio.mp3",
            audio_mime="audio/mpeg",
        )
        # New fields should have defaults
        assert lecture.transcription_confidence is None
        assert lecture.transcription_language is None
        assert lecture.transcription_cost_usd is None
        assert lecture.low_confidence_segments == []

    def test_lecture_model_with_transcription_data(self):
        from models.lecture import LectureDB

        lecture = LectureDB(
            id="test-id",
            teacher_id="teacher-id",
            title="Test Lecture",
            audio_object_key="lectures/test/audio.mp3",
            audio_filename="audio.mp3",
            audio_mime="audio/mpeg",
            transcript="Hello world",
            transcription_confidence=0.92,
            transcription_language="en",
            transcription_cost_usd=0.00067,  # Groq whisper-large-v3-turbo: $0.00067/min
            low_confidence_segments=[{"index": 2, "confidence": 0.5}],
        )
        assert lecture.transcription_confidence == 0.92
        assert lecture.transcription_language == "en"
        assert len(lecture.low_confidence_segments) == 1
