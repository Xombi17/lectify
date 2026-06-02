"""AI service — single point of contact with the LLM provider.

Today: Google Gemini 2.5 Flash via google-genai SDK.
Tomorrow: swap to Ollama / vLLM by writing a new `AIProvider` subclass
and changing one line in `get_ai_service()`.
"""
import json
import logging
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from core.config import get_settings
from models.lecture import Flashcard, QuizQuestion, StudyMaterials

logger = logging.getLogger(__name__)
settings = get_settings()


STUDY_PROMPT = """You are an expert academic assistant. Read this lecture transcript and produce a comprehensive study pack.

Return ONLY valid JSON (no markdown fences) matching this exact schema:
{
  "summary": "2-4 sentence overview of the lecture",
  "smart_notes": ["bullet-style cleaned note", "..."],
  "key_concepts": ["concept 1", "concept 2", "..."],
  "quiz": [
    {"question": "...", "options": ["A","B","C","D"], "answer_index": 0, "explanation": "..."}
  ],
  "flashcards": [
    {"front": "question or term", "back": "answer or definition"}
  ]
}

Rules:
- Generate 8-15 smart_notes covering definitions, key explanations, examples.
- Strip filler words, jokes, off-topic chatter; preserve academic depth.
- Generate exactly 5 quiz questions (mix of easy/medium/hard) with 4 options each.
- answer_index is the 0-based index into options.
- Generate 8-12 flashcards covering core terms.
- Use clear, student-friendly language.

TRANSCRIPT:
"""


class AIProvider(ABC):
    @abstractmethod
    async def transcribe_audio(self, audio_path: Path, mime_type: str) -> str: ...

    @abstractmethod
    async def generate_study_materials(self, transcript: str) -> StudyMaterials: ...


class GeminiProvider(AIProvider):
    def __init__(self, api_key: str, model: str):
        from google import genai  # imported lazily so the app boots without a key
        self._client = genai.Client(api_key=api_key)
        self._model = model

    async def transcribe_audio(self, audio_path: Path, mime_type: str) -> str:
        from google.genai import types
        logger.info("Uploading audio to Gemini: %s (%s)", audio_path, mime_type)
        uploaded = self._client.files.upload(
            file=str(audio_path),
            config=types.UploadFileConfig(mime_type=mime_type),
        )
        prompt = (
            "Transcribe this lecture audio verbatim into clean readable English text. "
            "Use proper punctuation and paragraph breaks. Do NOT include timestamps."
        )
        response = self._client.models.generate_content(
            model=self._model,
            contents=[prompt, uploaded],
        )
        return (response.text or "").strip()

    async def generate_study_materials(self, transcript: str) -> StudyMaterials:
        from google.genai import types
        prompt = STUDY_PROMPT + transcript[:120_000]  # safety guard
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        raw = (response.text or "").strip()
        data = _parse_json_lenient(raw)
        return StudyMaterials(
            summary=data.get("summary"),
            smart_notes=list(data.get("smart_notes") or []),
            key_concepts=list(data.get("key_concepts") or []),
            quiz=[QuizQuestion(**q) for q in (data.get("quiz") or []) if _valid_quiz(q)],
            flashcards=[Flashcard(**c) for c in (data.get("flashcards") or []) if _valid_card(c)],
        )


def _parse_json_lenient(raw: str) -> dict:
    """Parse JSON even if the model wraps it in code fences or trailing text."""
    raw = raw.strip()
    # strip markdown code fences
    fence = re.match(r"^```(?:json)?\s*(.+?)\s*```$", raw, re.DOTALL)
    if fence:
        raw = fence.group(1)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # find first { ... last }
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1:
            return json.loads(raw[start : end + 1])
        raise


def _valid_quiz(q: dict) -> bool:
    return (
        isinstance(q, dict)
        and isinstance(q.get("question"), str)
        and isinstance(q.get("options"), list)
        and len(q["options"]) >= 2
        and isinstance(q.get("answer_index"), int)
        and 0 <= q["answer_index"] < len(q["options"])
    )


def _valid_card(c: dict) -> bool:
    return isinstance(c, dict) and isinstance(c.get("front"), str) and isinstance(c.get("back"), str)


_provider: Optional[AIProvider] = None


def get_ai_service() -> AIProvider:
    """Lazy singleton so the app can boot before a key is provided."""
    global _provider
    if _provider is None:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Set it in backend/.env to enable AI processing."
            )
        _provider = GeminiProvider(settings.GEMINI_API_KEY, settings.GEMINI_MODEL)
    return _provider


def reset_ai_service() -> None:
    global _provider
    _provider = None
