"""AI worker — generates study materials from transcripts."""
import logging
from datetime import datetime, timezone

from core.config import get_settings
from core.queue_config import queue_for_stage
from models.job import JobCreate, JobDB
from repositories.lecture_repository import LectureRepository
from services.ai_service import get_ai_service
from services.lecture_service import (
    _extract_and_store_knowledge_graph,
    CHUNK_LENGTH_SECONDS,
    CHUNK_THRESHOLD_SECONDS,
)
from services.notification_service import publish_lecture_ready
from workers.base import BaseWorker, JobContext

logger = logging.getLogger(__name__)


class AIWorker(BaseWorker):
    """Worker that generates study materials from lecture transcripts.

    - Takes transcript from LectureDB
    - Generates summary, smart notes, quiz, flashcards
    - Creates embeddings for semantic search
    - Syncs concepts to Neo4j knowledge graph
    - Enqueues final embedding/neo4j stage
    """

    stage = "generate_materials"
    queue_name = queue_for_stage("generate_materials")

    def __init__(self, max_jobs: int | None = None):
        if max_jobs is None:
            max_jobs = get_settings().AI_CONCURRENCY
        super().__init__(max_jobs=max_jobs)

    async def process_job(self, job: JobDB, ctx: JobContext) -> list[JobCreate]:
        """Generate study materials from a lecture transcript."""
        lecture_id = job.lecture_id
        repo = LectureRepository()
        ai = get_ai_service()

        lecture = await repo.get_by_id(lecture_id)
        if not lecture:
            raise ValueError(f"Lecture {lecture_id} not found")
        if not lecture.transcript:
            raise ValueError(f"Lecture {lecture_id} has no transcript")

        await repo.update_fields(lecture_id, {
            "progress_label": "Generating study materials",
            "progress_step": 2,
            "progress_total": 4,
        })

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
        })

        # ── Notify ───────────────────────────────────────────────────
        try:
            await publish_lecture_ready(lecture_id, getattr(lecture, "class_id", None))
        except Exception:
            logger.warning("Unexpected error calling publish_lecture_ready", exc_info=False)

        logger.info("Study materials generated for lecture %s", lecture_id)
        
        return [JobCreate(
            lecture_id=lecture_id,
            version=1,
            stage="embed",
        )]

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
