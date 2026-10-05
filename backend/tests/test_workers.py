"""Tests for worker implementations — status transitions, error handling, stage progression."""
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.job import JobCreate, JobDB
from workers.base import JobContext


class TestTranscriptionWorker:
    """Tests for the TranscriptionWorker."""

    @pytest.mark.asyncio
    async def test_worker_instantiation(self):
        """Verify TranscriptionWorker can be instantiated."""
        from workers.transcription import TranscriptionWorker
        worker = TranscriptionWorker(max_jobs=3)
        assert worker.stage == "transcribe"
        assert worker.max_jobs == 3

    @pytest.mark.asyncio
    async def test_process_job_success_single_shot(self):
        """Verify successful single-shot transcription flow."""
        from workers.transcription import TranscriptionWorker

        worker = TranscriptionWorker(max_jobs=3)

        # Mock job
        job = JobDB(id="job-test-1", lecture_id="lec-test-1", stage="transcribe", version=1, status="processing")
        ctx = JobContext("job-test-1", 1, None, "transcribe", "receipt", 300)

        with patch("workers.transcription.LectureRepository") as MockRepo, \
             patch("workers.transcription.get_ai_service") as MockAI, \
             patch("workers.transcription.get_storage") as MockStorage:

            # Mock lecture
            mock_lecture = MagicMock()
            mock_lecture.id = "lec-test-1"
            mock_lecture.audio_object_key = "lectures/lec-test-1/test.mp3"
            mock_lecture.audio_mime = "audio/mpeg"
            mock_lecture.created_at = datetime.now(timezone.utc)

            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_lecture
            MockRepo.return_value = mock_repo

            # Mock AI
            mock_ai = AsyncMock()
            mock_ai.transcribe_audio.return_value = "Test transcript"
            MockAI.return_value = mock_ai

            # Mock storage
            class _FakeACM:
                async def __aenter__(self):
                    return MagicMock()
                async def __aexit__(self, *args):
                    pass

            mock_storage = MagicMock()
            mock_storage.open_local = lambda key: _FakeACM()
            MockStorage.return_value = mock_storage

            result = await worker.process_job(job, ctx)

            assert len(result) == 1
            assert result[0].stage == "generate_materials"

    @pytest.mark.asyncio
    async def test_process_job_lecture_not_found(self):
        """Verify error handling when lecture doesn't exist."""
        from workers.transcription import TranscriptionWorker

        worker = TranscriptionWorker(max_jobs=3)
        job = JobDB(id="job-missing-1", lecture_id="lec-missing-1", stage="transcribe", version=1, status="processing")
        ctx = JobContext("job-missing-1", 1, None, "transcribe", "receipt", 300)

        with patch("workers.transcription.LectureRepository") as MockRepo:
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = None
            MockRepo.return_value = mock_repo

            with pytest.raises(ValueError, match="not found"):
                await worker.process_job(job, ctx)


class TestAIWorker:
    """Tests for the AIWorker."""

    @pytest.mark.asyncio
    async def test_worker_instantiation(self):
        """Verify AIWorker can be instantiated."""
        from workers.ai import AIWorker
        worker = AIWorker(max_jobs=5)
        assert worker.stage == "generate_materials"
        assert worker.max_jobs == 5


class TestEmbeddingWorker:
    """Tests for the EmbeddingWorker."""

    @pytest.mark.asyncio
    async def test_worker_instantiation(self):
        """Verify EmbeddingWorker can be instantiated."""
        from workers.embedding import EmbeddingWorker
        worker = EmbeddingWorker(max_jobs=10)
        assert worker.stage == "embed"
        assert worker.max_jobs == 10

    @pytest.mark.asyncio
    async def test_neo4j_failure_non_fatal(self):
        """Verify Neo4j failures don't prevent lecture from being marked ready."""
        from workers.embedding import EmbeddingWorker

        worker = EmbeddingWorker(max_jobs=10)
        job = JobDB(id="job-embed-1", lecture_id="lec-embed-1", stage="embed", version=1, status="processing")
        ctx = JobContext("job-embed-1", 1, None, "embed", "receipt", 300)

        with patch("workers.embedding.LectureRepository") as MockRepo, \
             patch("workers.embedding.get_ai_service") as MockAI, \
             patch("workers.embedding.get_neo4j_service") as MockNeo4j:

            mock_lecture = MagicMock()
            mock_lecture.embedding = None
            mock_lecture.status = "processing"
            mock_lecture.materials.summary = "Test summary"
            mock_lecture.materials.key_concepts = ["concept1", "concept2"]

            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_lecture
            MockRepo.return_value = mock_repo

            # Neo4j fails
            mock_neo4j = MagicMock()
            mock_neo4j.add_lecture_node.side_effect = RuntimeError("Neo4j unavailable")
            MockNeo4j.return_value = mock_neo4j

            # AI succeeds
            mock_ai = AsyncMock()
            mock_ai.embed.return_value = [0.1, 0.2, 0.3]
            MockAI.return_value = mock_ai

            result = await worker.process_job(job, ctx)

            assert len(result) == 0
            mock_repo.update_fields.assert_any_call(
                "lec-embed-1", {"status": "ready", "error_message": None, "progress_step": 4, "progress_total": 4, "progress_label": "Done"}
            )
