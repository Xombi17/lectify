"""Transcription worker — handles the 'transcribe' stage of lecture processing."""
import logging
from datetime import datetime, timezone
from pathlib import Path

from core.config import get_settings
from core.queue_config import compute_priority_score
from models.job import JobCreate, JobStage
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
from services.queue_client import update_job_status, move_to_dlq, enqueue_job
from services.storage_service import get_storage
from workers.base import BaseWorker

logger = logging.getLogger(__name__)


class TranscriptionWorker(BaseWorker):
    """Worker that handles the transcription stage of lecture processing.

    - Downloads audio from storage
    - Probes duration, routes to single-shot or chunked path
    - Transcribes using AI provider
    - Stores transcript on LectureDB
    - Enqueues next stage (generate_materials)
    """

    worker_name = "transcription"
    # Read max_jobs from Settings env var (default 3 for API rate limits)
    max_jobs: int = 3

    def __init__(self, max_jobs: int | None = None):
        if max_jobs is None:
            max_jobs = get_settings().TRANSCRIPTION_CONCURRENCY
        super().__init__(max_jobs=max_jobs)

    async def process_job(self, ctx: dict, job_data: dict) -> dict:
        """Transcribe a lecture.

        job_data fields:
          - lecture_id: str
          - stage: str (should be "transcribe")
          - attempt: int
        """
        lecture_id = job_data["lecture_id"]
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
                "updated_at": datetime.now(timezone.utc),
            })
            await update_job_status(ctx["job_id"], "processing")

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

            # Enqueue next stage: generate study materials
            score = compute_priority_score(lecture.created_at)
            next_job = await enqueue_job(JobCreate(
                lecture_id=lecture_id,
                version=1,
                priority_score=score,
                stage="generate_materials",
            ))

            logger.info(
                "Transcription complete for lecture %s, enqueued materials job %s",
                lecture_id, next_job.id,
            )
            return {"status": "completed", "next_stage": "generate_materials"}

        except Exception as e:
            logger.exception("Transcription failed for lecture %s", lecture_id)
            await repo.update_fields(lecture_id, {
                "status": "retrying",
                "error_message": str(e)[:500],
            })
            await update_job_status(ctx["job_id"], "retrying", str(e)[:500])

            # Check attempt count for DLQ
            attempt = job_data.get("attempt", 0)
            if attempt >= 2:  # max 3 attempts (0-indexed)
                await move_to_dlq(ctx["job_id"], str(e)[:500])
                await repo.update_fields(lecture_id, {
                    "status": "dead_letter",
                    "error_message": f"Dead letter after {attempt + 1} attempts: {str(e)[:500]}",
                })
                return {"status": "dead_letter", "error": str(e)[:200]}

            from services.metrics_service import queue_retry_count
            queue_retry_count.labels(queue_type="process_lecture").inc()
            return {"status": "retrying", "error": str(e)[:200]}

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
