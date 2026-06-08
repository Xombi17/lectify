"""Transcription service — speech-to-text with confidence scoring.

Separate from AI service (LLM tasks). Handles Whisper API integration,
parallel chunk transcription, confidence scoring, and cost tracking.
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TranscriptionSegment(BaseModel):
    """A single segment of a transcription."""
    start: float  # start time in seconds
    end: float  # end time in seconds
    text: str
    confidence: float  # 0.0-1.0


class TranscriptionResult(BaseModel):
    """Full transcription result with metadata."""
    text: str
    language: str  # detected language code (e.g., "en", "hi", "es")
    confidence: float  # 0.0-1.0 average confidence across segments
    duration_seconds: float  # total duration of transcribed audio
    word_count: int
    segments: list[TranscriptionSegment] = Field(default_factory=list)
    provider: str  # "groq" or "gemini"
    cost_usd: float  # cost of this transcription


class TranscriptionProvider(ABC):
    """Abstract interface for speech-to-text providers."""

    @abstractmethod
    async def transcribe(
        self,
        audio_path: Path,
        mime_type: str,
        language: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe a single audio file."""
        ...

    @abstractmethod
    async def transcribe_chunks(
        self,
        chunks: list[tuple[Path, str]],  # (path, mime_type) pairs
        language: str | None = None,
        max_concurrent: int = 5,
    ) -> list[TranscriptionResult]:
        """Transcribe multiple audio chunks in parallel."""
        ...

    @abstractmethod
    def estimate_cost(self, duration_seconds: float) -> float:
        """Estimate cost in USD for transcribing audio of given duration."""
        ...


class WhisperProvider(TranscriptionProvider):
    """Groq Whisper API integration for speech-to-text.

    Uses Groq's OpenAI-compatible endpoint for fast, cheap transcription.
    Endpoint: https://api.groq.com/openai/v1/audio/transcriptions
    Models: whisper-large-v3 ($0.00185/min) or whisper-large-v3-turbo ($0.00067/min, default)
    """

    _API_BASE = "https://api.groq.com/openai/v1"
    _WHISPER_ENDPOINT = f"{_API_BASE}/audio/transcriptions"

    def __init__(self, api_key: str, model: str = "whisper-large-v3-turbo", language: str = "en"):
        self._api_key = api_key
        self._model = model
        self._default_language = language

    async def transcribe(
        self,
        audio_path: Path,
        mime_type: str,
        language: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe a single audio file using Groq Whisper API (OpenAI-compatible)."""
        import httpx

        lang = language or self._default_language
        file_size = audio_path.stat().st_size

        # Groq/Whisper API limit: 25 MB
        if file_size > 25 * 1024 * 1024:
            raise ValueError(
                f"Audio file too large for Whisper API ({file_size / 1024 / 1024:.1f} MB). "
                "Use chunked transcription for files >25 MB."
            )

        logger.info("Transcribing %s with Groq Whisper (%.1f MB, lang=%s, model=%s)",
                    audio_path.name, file_size / 1024 / 1024, lang, self._model)

        async with httpx.AsyncClient(timeout=300.0) as client:
            with open(audio_path, "rb") as f:
                response = await client.post(
                    self._WHISPER_ENDPOINT,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    files={"file": (audio_path.name, f, mime_type)},
                    data={
                        "model": self._model,
                        "language": lang,
                        "response_format": "verbose_json",
                        "timestamp_granularities[]": ["segment"],
                    },
                )

            if response.status_code != 200:
                error_detail = response.text[:500]
                raise RuntimeError(f"Groq Whisper API error {response.status_code}: {error_detail}")

            result = response.json()

        # Parse segments
        segments = []
        for seg in result.get("segments", []):
            # Whisper returns no_speech_prob, invert for confidence
            confidence = 1.0 - seg.get("no_speech_prob", 0.0)
            segments.append(TranscriptionSegment(
                start=seg.get("start", 0.0),
                end=seg.get("end", 0.0),
                text=seg.get("text", "").strip(),
                confidence=round(confidence, 4),
            ))

        # Calculate average confidence
        avg_confidence = (
            sum(s.confidence for s in segments) / len(segments)
            if segments
            else 0.0
        )

        # Estimate cost
        duration = result.get("duration", 0.0)
        cost = self.estimate_cost(duration)

        return TranscriptionResult(
            text=result.get("text", "").strip(),
            language=result.get("language", lang),
            confidence=round(avg_confidence, 4),
            duration_seconds=duration,
            word_count=len(result.get("text", "").split()),
            segments=segments,
            provider="groq",
            cost_usd=round(cost, 6),
        )

    async def transcribe_chunks(
        self,
        chunks: list[tuple[Path, str]],
        language: str | None = None,
        max_concurrent: int = 5,
    ) -> list[TranscriptionResult]:
        """Transcribe multiple chunks in parallel with concurrency limit."""
        semaphore = asyncio.Semaphore(max_concurrent)
        lang = language or self._default_language

        async def transcribe_with_limit(path: Path, mime: str) -> TranscriptionResult:
            async with semaphore:
                return await self.transcribe(path, mime, lang)

        tasks = [transcribe_with_limit(p, m) for p, m in chunks]
        return await asyncio.gather(*tasks)

    def estimate_cost(self, duration_seconds: float) -> float:
        """Estimate cost in USD.

        Groq pricing (2026):
        - whisper-large-v3-turbo: $0.04/hour = $0.00067/minute
        - whisper-large-v3: $0.111/hour = $0.00185/minute
        """
        from core.config import get_settings
        settings = get_settings()
        minutes = duration_seconds / 60.0
        return minutes * settings.WHISPER_COST_PER_MINUTE


# Default threshold for flagging low-confidence segments
DEFAULT_CONFIDENCE_THRESHOLD = 0.7


def flag_low_confidence_segments(
    result: TranscriptionResult,
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> list[dict]:
    """Identify segments with confidence below threshold.

    Returns list of flagged segment dicts for storage on LectureDB.
    """
    flagged = []
    for i, seg in enumerate(result.segments):
        if seg.confidence < threshold:
            flagged.append({
                "index": i,
                "start": seg.start,
                "end": seg.end,
                "text": seg.text,
                "confidence": seg.confidence,
                "threshold": threshold,
            })
    return flagged


def overall_confidence_ok(
    result: TranscriptionResult,
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> bool:
    """Check if overall transcription confidence meets threshold."""
    return result.confidence >= threshold


def log_transcription_cost(
    lecture_id: str,
    provider: str,
    duration_seconds: float,
    cost_usd: float,
    chunks: int = 1,
) -> None:
    """Log transcription cost for monitoring and analytics."""
    minutes = duration_seconds / 60.0
    logger.info(
        "Transcription cost | lecture=%s provider=%s duration=%.1fs chunks=%d cost=$%.6f ($%.4f/min)",
        lecture_id,
        provider,
        duration_seconds,
        chunks,
        cost_usd,
        cost_usd / minutes if minutes > 0 else 0,
    )


def aggregate_daily_costs() -> dict:
    """Aggregate transcription costs for the day.

    Returns dict with total_cost, total_minutes, lecture_count.
    Note: This is a placeholder — real implementation would query
    the database for today's transcriptions.
    """
    # TODO: Implement with database query in Phase 7 (Monitoring)
    return {
        "total_cost_usd": 0.0,
        "total_minutes": 0.0,
        "lecture_count": 0,
    }


class GeminiFallbackProvider(TranscriptionProvider):
    """Fallback transcription using Gemini (existing implementation)."""

    def __init__(self, ai_service):
        self._ai = ai_service

    async def transcribe(
        self,
        audio_path: Path,
        mime_type: str,
        language: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe using Gemini as fallback. No confidence/segments data."""
        text = await self._ai.transcribe_audio(audio_path, mime_type)

        return TranscriptionResult(
            text=text,
            language=language or "unknown",
            confidence=0.0,  # Gemini doesn't provide confidence
            duration_seconds=0.0,  # Not available from Gemini
            word_count=len(text.split()),
            segments=[],  # Not available from Gemini
            provider="gemini",
            cost_usd=0.0,  # Cost tracked separately for Gemini
        )

    async def transcribe_chunks(
        self,
        chunks: list[tuple[Path, str]],
        language: str | None = None,
        max_concurrent: int = 5,
    ) -> list[TranscriptionResult]:
        """Sequential fallback (Gemini doesn't support parallel)."""
        results = []
        for path, mime in chunks:
            result = await self.transcribe(path, mime, language)
            results.append(result)
        return results

    def estimate_cost(self, duration_seconds: float) -> float:
        return 0.0  # Gemini cost tracked separately
