"""Lecture business logic — orchestrates storage + AI + repository."""
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from models.lecture import LectureDB, StudyMaterials
from repositories.lecture_repository import LectureRepository
from services.ai_service import get_ai_service
from services.storage_service import get_storage

logger = logging.getLogger(__name__)


ALLOWED_AUDIO_MIME = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/x-m4a",
    "audio/m4a",
    "audio/mp4",
    "audio/aac",
    "audio/ogg",
    "audio/webm",
    "audio/flac",
}


def normalize_mime(mime: str, filename: str) -> str | None:
    """Return a canonical audio MIME type or None if the input is not audio.

    Caller MUST treat None as 'reject this upload'.
    """
    mime = (mime or "").lower()
    if mime in ALLOWED_AUDIO_MIME:
        return mime
    ext = Path(filename).suffix.lower()
    mapping = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".aac": "audio/aac",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
        ".webm": "audio/webm",
    }
    return mapping.get(ext)


async def process_lecture_background(lecture_id: str) -> None:
    """Run the full AI pipeline. Catch errors and persist them on the doc."""
    repo = LectureRepository()
    storage = get_storage()

    lecture = await repo.get_by_id(lecture_id)
    if lecture is None:
        logger.error("Lecture %s not found in background task", lecture_id)
        return

    await repo.update_fields(lecture_id, {"status": "processing"})

    try:
        ai = get_ai_service()
        audio_path = storage.local_path(lecture.audio_object_key)
        logger.info("Transcribing %s ...", audio_path)
        transcript = await ai.transcribe_audio(audio_path, lecture.audio_mime)
        if not transcript:
            raise RuntimeError("Empty transcript from AI provider")

        logger.info("Generating study materials for %s ...", lecture_id)
        materials = await ai.generate_study_materials(transcript)

        # Best-effort embedding for semantic search (fail soft)
        embedding: list[float] | None = None
        try:
            seed = " ".join(filter(None, [
                lecture.title,
                materials.summary or "",
                " ".join(materials.key_concepts or []),
            ]))
            if seed.strip():
                embedding = await ai.embed(seed)
        except Exception:  # noqa: BLE001
            logger.exception("Embedding failed for %s; semantic search will use lexical only", lecture_id)

        await repo.update_fields(
            lecture_id,
            {
                "transcript": transcript,
                "materials": materials,
                "embedding": embedding,
                "status": "ready",
                "error_message": None,
            },
        )
        logger.info("Lecture %s processed", lecture_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to process lecture %s", lecture_id)
        await repo.update_fields(
            lecture_id,
            {"status": "error", "error_message": str(exc)[:500]},
        )
