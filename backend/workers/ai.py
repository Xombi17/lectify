"""AI worker — generates study materials from transcripts."""
import logging
from datetime import datetime, timezone

from core.config import get_settings
from core.queue_config import compute_priority_score
from models.job import JobCreate, JobStage
from repositories.lecture_repository import LectureRepository
from services.ai_service import get_ai_service
from services.lecture_service import (
    _extract_and_store_knowledge_graph,
    CHUNK_LENGTH_SECONDS,
    CHUNK_THRESHOLD_SECONDS,
)
from services.queue_client import enqueue_job, move_to_dlq, update_job_status
from workers.base import BaseWorker

logger = logging.getLogger(__name__)


class AIWorker(BaseWorker):
    """Worker that generates study materials from lecture transcripts.

    - Takes transcript from LectureDB
    - Generates summary, smart notes, quiz, flashcards
    - Creates embeddings for semantic search
    - Syncs concepts to Neo4j knowledge graph
    - Enqueues final embedding/neo4j stage
    """

    worker_name = "ai"
    # Read max_jobs from Settings env var (default 5 for parallel API calls)
    max_jobs: int = 5

    def __init__(self, max_jobs: int | None = None):
        if max_jobs is None:
            max_jobs = get_settings().AI_CONCURRENCY
        super().__init__(max_jobs=max_jobs)

    async def process_job(self, ctx: dict, job_data: dict) -> dict:
        """Generate study materials from a lecture transcript.

        job_data fields:
          - lecture_id: str
          - stage: str (should be "generate_materials")
          - attempt: int
        """
        lecture_id = job_data["lecture_id"]
        repo = LectureRepository()
        ai = get_ai_service()

        try:
            lecture = await repo.get_by_id(lecture_id)
            if not lecture:
                raise ValueError(f"Lecture {lecture_id} not found")
            if not lecture.transcript:
                raise ValueError(f"Lecture {lecture_id} has no transcript")

            await repo.update_fields(lecture_id, {
                "progress_label": "Generating study materials",
                "progress_step": 2,
                "progress_total": 4,
                "updated_at": datetime.now(timezone.utc),
            })
            await update_job_status(ctx["job_id"], "processing")

            # ── Materials Generation ──────────────────────────────────────
            duration = lecture.duration_seconds or 0

            if duration and duration > CHUNK_THRESHOLD_SECONDS:
                materials = await self._generate_from_chunks(lecture, ai, repo)
            else:
                materials = await ai.generate_study_materials(lecture.transcript)

            if not materials:
                raise RuntimeError("Empty study materials from AI provider")
            if not materials.summary:
                logger.warning("Study materials for %s missing summary", lecture_id)

            await repo.update_fields(lecture_id, {
                "progress_label": "Creating embeddings",
                "progress_step": 3,
            })

            # ── Embeddings ───────────────────────────────────────────────
            embedding = await self._safe_embedding(ai, materials)
            if embedding:
                await repo.update_fields(lecture_id, {
                    "embedding": embedding,
                })

            # ── Knowledge Graph Sync ─────────────────────────────────────
            await repo.update_fields(lecture_id, {
                "progress_label": "Syncing knowledge graph",
            })
            await _extract_and_store_knowledge_graph(lecture_id, lecture, materials, repo)

            # ── Store Materials ──────────────────────────────────────────
            await repo.update_fields(lecture_id, {
                "materials": materials,
                "status": "ready",
                "error_message": None,
                "progress_step": 4,
                "progress_total": 4,
                "progress_label": "Done",
                "updated_at": datetime.now(timezone.utc),
            })

            # Enqueue final stage: embed + neo4j sync
            score = compute_priority_score(lecture.created_at)
            next_job = await enqueue_job(JobCreate(
                lecture_id=lecture_id,
                version=1,
                priority_score=score,
                stage="embed",
            ))

            logger.info(
                "Study materials generated for lecture %s, enqueued embed job %s",
                lecture_id, next_job.id,
            )
            return {"status": "completed", "next_stage": "embed"}

        except Exception as e:
            logger.exception("AI generation failed for lecture %s", lecture_id)
            await repo.update_fields(lecture_id, {
                "status": "retrying",
                "error_message": str(e)[:500],
            })
            await update_job_status(ctx["job_id"], "retrying", str(e)[:500])

            attempt = job_data.get("attempt", 0)
            if attempt >= 2:
                await move_to_dlq(ctx["job_id"], str(e)[:500])
                await repo.update_fields(lecture_id, {
                    "status": "dead_letter",
                    "error_message": f"Dead letter after {attempt + 1} attempts: {str(e)[:500]}",
                })
                return {"status": "dead_letter", "error": str(e)[:200]}

            from services.metrics_service import queue_retry_count
            queue_retry_count.labels(queue_type="process_lecture").inc()
            return {"status": "retrying", "error": str(e)[:200]}

    async def _generate_from_chunks(self, lecture, ai, repo) -> dict:
        """Generate materials from chunked transcript by digesting each chunk then merging."""
        import re

        # Parse transcripts with chunk markers
        chunk_pattern = re.compile(r"\[Chunk (\d+) · (.*?)\]\n(.*?)(?=\n\n\[Chunk|\Z)", re.DOTALL)
        matches = list(chunk_pattern.finditer(lecture.transcript or ""))

        if not matches:
            # No chunk markers found, treat as single shot
            return await ai.generate_study_materials(lecture.transcript or "")

        chunk_digests = []
        for match in matches:
            chunk_index = int(match.group(1)) - 1
            start_seconds = self._parse_timestamp(match.group(2))
            chunk_text = match.group(3).strip()

            digest = await ai.digest_chunk(chunk_text)
            digest["chunk_index"] = chunk_index
            digest["start_seconds"] = start_seconds or (chunk_index * CHUNK_LENGTH_SECONDS)
            chunk_digests.append(digest)

        return await ai.merge_chunk_digests(chunk_digests)

    @staticmethod
    def _parse_timestamp(ts: str) -> float:
        """Parse a timestamp string like '00:05:30' to seconds."""
        try:
            parts = list(map(int, ts.split(":")))
            if len(parts) == 3:
                return parts[0] * 3600 + parts[1] * 60 + parts[2]
            if len(parts) == 2:
                return parts[0] * 60 + parts[1]
            return float(parts[0])
        except (ValueError, IndexError):
            return 0.0

    @staticmethod
    async def _safe_embedding(ai, materials) -> list[float] | None:
        """Generate embedding from study materials with graceful fallback."""
        seed = " ".join(filter(None, [
            materials.summary or "",
            " ".join(materials.key_concepts or []),
        ]))
        if not seed.strip():
            return None
        try:
            return await ai.embed(seed)
        except Exception:
            logger.exception("Embedding failed; semantic search will use lexical only")
            return None
