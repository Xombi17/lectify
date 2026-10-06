"""Embedding worker — generates embeddings and syncs to Neo4j knowledge graph."""

import logging
from datetime import datetime, timezone

from core.config import get_settings
from models.job import JobCreate, JobDB
from repositories.lecture_repository import LectureRepository
from services.ai_service import get_ai_service
from services.neo4j_service import get_neo4j_service

from workers.base import BaseWorker, JobContext

logger = logging.getLogger(__name__)


class EmbeddingWorker(BaseWorker):
    """Worker that handles embedding generation and Neo4j knowledge graph sync.

    This is the final stage in the lecture processing pipeline.
    - Generates embeddings for semantic search (if not already done)
    - Ensures Neo4j knowledge graph is synced
    - Marks lecture as ready if the AI worker hasn't already
    """

    stage = "embed"
    # Backends resolve the stage key (SqsQueueBackend._resolve -> queue URL), matching enqueue_job.
    queue_name = "embed"

    def __init__(self, max_jobs: int | None = None):
        if max_jobs is None:
            max_jobs = get_settings().EMBEDDING_CONCURRENCY
        super().__init__(max_jobs=max_jobs)

    async def process_job(self, job: JobDB, ctx: JobContext) -> list[JobCreate]:
        """Generate embeddings and sync knowledge graph."""
        lecture_id = job.lecture_id
        repo = LectureRepository()
        ai = get_ai_service()

        lecture = await repo.get_by_id(lecture_id)
        if not lecture:
            raise ValueError(f"Lecture {lecture_id} not found")

        await repo.update_fields(
            lecture_id,
            {
                "progress_label": "Finalizing embeddings",
            },
        )

        # ── Embeddings (if not already set by AI worker) ─────────────
        if not lecture.embedding and lecture.materials:
            seed = " ".join(
                filter(
                    None,
                    [
                        lecture.materials.summary or "",
                        " ".join(lecture.materials.key_concepts or []),
                    ],
                )
            )
            if seed.strip():
                try:
                    embedding = await ai.embed(seed)
                    await repo.update_fields(lecture_id, {"embedding": embedding})
                    logger.info("Generated embedding for lecture %s", lecture_id)
                except Exception as e:
                    logger.warning(
                        "Embedding failed for %s: %s (lexical search fallback)",
                        lecture_id,
                        e,
                    )

        # ── Neo4j Knowledge Graph Sync ──────────────────────────────
        if lecture.materials:
            await self._sync_knowledge_graph(lecture_id, lecture, repo)

        # ── Final Status ─────────────────────────────────────────────
        if lecture.status != "ready":
            await repo.update_fields(
                lecture_id,
                {
                    "status": "ready",
                    "error_message": None,
                    "progress_step": 4,
                    "progress_total": 4,
                    "progress_label": "Done",
                },
            )

        logger.info("Embedding stage complete for lecture %s", lecture_id)
        return []

    async def _sync_knowledge_graph(
        self, lecture_id: str, lecture, repo: LectureRepository
    ) -> None:
        """Sync lecture concepts and relationships to Neo4j."""
        try:
            neo4j = get_neo4j_service()

            # Add lecture node
            neo4j.add_lecture_node(
                lecture_id=lecture.id,
                title=lecture.title,
                subject=lecture.subject or "",
                semester=lecture.semester or "",
            )

            # Add concept nodes and connect to lecture
            for concept in lecture.materials.key_concepts or []:
                if concept and concept.strip():
                    neo4j.add_concept_node(
                        lecture_id=lecture.id,
                        concept=concept.strip(),
                    )

            # Add relationships between co-occurring concepts
            concepts = [
                c.strip()
                for c in (lecture.materials.key_concepts or [])
                if c and c.strip()
            ]
            for i, concept1 in enumerate(concepts):
                for concept2 in concepts[i + 1 :]:
                    neo4j.add_relationship_between_concepts(
                        lecture_id=lecture.id,
                        concept1=concept1,
                        concept2=concept2,
                        relationship_type="RELATED_TO",
                    )

            logger.info(
                "Synced knowledge graph for lecture %s (%d concepts)",
                lecture_id,
                len(concepts),
            )
        except Exception as e:
            logger.warning("Neo4j sync failed for %s: %s (non-fatal)", lecture_id, e)
            # Non-fatal: lecture processing continues without knowledge graph
