"""Transcription worker — handles the 'transcribe' stage of lecture processing."""
import logging
from datetime import datetime, timezone
from pathlib import Path

from core.config import get_settings
from core.queue_config import queue_for_stage
from models.job import JobCreate, JobDB, JobStage
from repositories.lecture_repository import LectureRepository
from services.ai_service import get_ai_service
from services.audio_chunker import (
    cleanup_chunks,
    format_timestamp,
    get_duration_seconds,
    split_into_chunks,
)
from services.lecture_service import (
    CHUNK_THRESHOLD_SECONDS,
    CHUNK_LENGTH_SECONDS,
    CHUNK_MIME,
)
from services.storage_service import get_storage
from workers.base import BaseWorker, JobContext

logger = logging.getLogger(__name__)


class TranscriptionWorker(BaseWorker):
    """Worker that handles the transcription stage of lecture processing.

    - Downloads audio from storage
    - Probes duration, routes to single-shot or chunked path
    - Transcribes using AI provider
    - Stores transcript on LectureDB
    - Returns next stage (generate_materials) to be enqueued
    """

    stage = "transcribe"
    queue_name = queue_for_stage("transcribe")

    def __init__(self, max_jobs: int | None = None):
        if max_jobs is None:
            max_jobs = get_settings().TRANSCRIPTION_CONCURRENCY
        super().__init__(max_jobs=max_jobs)

    async def process_job(self, job: JobDB, ctx: JobContext) -> list[JobCreate]:
        """Transcribe a lecture."""
        lecture_id = job.lecture_id
        repo = LectureRepository()
        storage = get_storage()
        chunks_made: list[Path] = []

        try:
            # Update status to processing
            await repo.update_fields(lecture_id, {
                "status": "processing",
                "progress_step": 1,
                "progress_total": 3,
                "progress_label": "Transcribing audio",
            })

            lecture = await repo.get_by_id(lecture_id)
            if not lecture:
                raise ValueError(f"Lecture {lecture_id} not found")

            ai = get_ai_service()

            # Download audio locally for processing
            async with storage.open_local(lecture.audio_object_key) as audio_path:
                # Probe duration
                try:
                    duration = await get_duration_seconds(audio_path)
                except Exception:
                    logger.exception("Could not probe duration; falling back to single-shot")
                    duration = 0.0

                await repo.update_fields(lecture_id, {"duration_seconds": duration})

                if duration and duration > CHUNK_THRESHOLD_SECONDS:
                    transcript = await self._transcribe_chunked(
                        lecture_id, audio_path, duration, ai, repo, chunks_made,
                    )
                else:
                    transcript = await self._transcribe_single(
                        lecture_id, audio_path, lecture.audio_mime, ai, repo,
                    )

            if not transcript:
                raise RuntimeError("Empty transcript from AI provider")

            # Store transcript on lecture
            await repo.update_fields(lecture_id, {
                "transcript": transcript,
                "progress_step": 2,
                "progress_label": "Transcription complete",
            })

            logger.info("Transcription complete for lecture %s", lecture_id)
            
            # Return next stage to enqueue
            return [JobCreate(
                lecture_id=lecture_id,
                version=1,
                stage="generate_materials",
            )]

        finally:
            if chunks_made:
                cleanup_chunks(chunks_made)

    async def _transcribe_single(
        self, lecture_id: str, audio_path: Path, mime: str, ai, repo,
    ) -> str:
        """Transcribe a short lecture in a single pass."""
        logger.info("Single-shot transcription for lecture %s", lecture_id)
        transcript = await ai.transcribe_audio(audio_path, mime)
        return transcript

    async def _transcribe_chunked(
        self, lecture_id: str, audio_path: Path, duration: float, ai, repo,
        chunks_sink: list[Path],
    ) -> str:
        """Split a long lecture into chunks, transcribe each, stitch."""
        logger.info("Chunked transcription for lecture %s (%.1fs)", lecture_id, duration)

        # Split
        chunk_paths = await split_into_chunks(audio_path, CHUNK_LENGTH_SECONDS)
        chunks_sink.extend(chunk_paths)
        chunk_count = len(chunk_paths)

        await repo.update_fields(lecture_id, {
            "chunk_count": chunk_count,
            "progress_label": f"Transcribing {chunk_count} chunks",
        })

        # Transcribe each chunk sequentially (respects API rate limits)
        chunk_texts: list[str] = []
        for idx, chunk_path in enumerate(chunk_paths):
            offset = idx * CHUNK_LENGTH_SECONDS
            await repo.update_fields(lecture_id, {
                "progress_label": f"Transcribing chunk {idx + 1}/{chunk_count} ({format_timestamp(offset)})",
            })
            chunk_text = await ai.transcribe_audio(chunk_path, CHUNK_MIME)
            chunk_texts.append(chunk_text)

        # Stitch with timestamps
        return "\n\n".join(
            f"[Chunk {i + 1} · {format_timestamp(i * CHUNK_LENGTH_SECONDS)}]\n{t.strip()}"
            for i, t in enumerate(chunk_texts)
        )
