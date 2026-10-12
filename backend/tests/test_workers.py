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


# --- Phase 19: Deepgram-first whole-file path + chain fallback ---------------

from pathlib import Path as _P

from models.job import JobDB as _JobDB
from services.ai_service import ProviderRateLimited
from services.transcription_service import TranscriptionResult, TranscriptionSegment


class _Fake:
    def __init__(self, name, whole_file, exc=None):
        self.name, self.whole_file, self.exc, self.calls = name, whole_file, exc, 0

    async def transcribe(self, path, mime, language=None):
        self.calls += 1
        if self.exc:
            raise self.exc
        return TranscriptionResult(
            text=f"{self.name} text", language="en-US-long-code", confidence=0.9,
            duration_seconds=42.0, word_count=2, segments=[], provider=self.name, cost_usd=0.01,
        )


class _ACM:
    async def __aenter__(self):
        return _P("x.mp3")

    async def __aexit__(self, *a):
        pass


async def _run(chain, duration, chunks=None):
    from workers.transcription import TranscriptionWorker

    job = _JobDB(id="j", lecture_id="lec-1", stage="transcribe", version=1, status="processing")
    ctx = JobContext("j", 1, None, "transcribe", "r", 300)
    lecture = MagicMock(audio_object_key="k", audio_mime="audio/mpeg")
    repo = AsyncMock()
    repo.get_by_id.return_value = lecture
    storage = MagicMock(open_local=lambda k: _ACM())
    dur = AsyncMock(side_effect=RuntimeError("x")) if duration is None else AsyncMock(return_value=duration)
    split = AsyncMock(return_value=chunks or [])
    chunk_repo = AsyncMock()
    chunk_repo.pending.return_value = list(range(len(chunks or [])))
    chunk_repo.merged_text.return_value = "merged"
    with patch("workers.transcription.LectureRepository", return_value=repo), \
         patch("workers.transcription.get_ai_service"), \
         patch("workers.transcription.get_storage", return_value=storage), \
         patch("workers.transcription.build_transcription_chain", return_value=chain), \
         patch("workers.transcription.get_duration_seconds", dur), \
         patch("workers.transcription.split_into_chunks", split), \
         patch("workers.transcription.cleanup_chunks"), \
         patch("repositories.job_chunk_repository.JobChunkRepository", return_value=chunk_repo):
        out = await TranscriptionWorker(max_jobs=1).process_job(job, ctx)
    return out, repo, split, chunk_repo


def _fields(repo):
    d = {}
    for c in repo.update_fields.call_args_list:
        d.update(c.args[1])
    return d


@pytest.mark.asyncio
async def test_deepgram_whole_file_no_chunking():
    dg, naga = _Fake("deepgram", True), _Fake("naga", False)
    out, repo, split, _ = await _run([dg, naga], 7200)
    split.assert_not_called()
    assert naga.calls == 0 and out[0].stage == "generate_materials"
    f = _fields(repo)
    assert f["transcript"] == "deepgram text"
    assert f["transcription_confidence"] == 0.9
    assert f["transcription_language"] == "en-US-long"
    assert f["transcription_cost_usd"] == 0.01
    assert "low_confidence_segments" in f


@pytest.mark.asyncio
async def test_duration_from_result_when_probe_fails():
    _, repo, _, _ = await _run([_Fake("deepgram", True)], None)
    assert _fields(repo)["duration_seconds"] == 42.0


@pytest.mark.asyncio
async def test_fallback_single_path():
    naga = _Fake("naga", False)
    await _run([_Fake("deepgram", True, RuntimeError("boom")), naga], 60)
    assert naga.calls == 1


@pytest.mark.asyncio
async def test_fallback_chunked_path():
    naga = _Fake("naga", False)
    _, _, split, chunk_repo = await _run(
        [_Fake("deepgram", True, RuntimeError("boom")), naga], 7200, [_P("a"), _P("b")]
    )
    split.assert_awaited_once()
    assert naga.calls == 2
    assert chunk_repo.mark_done.call_args_list[0].args[3].startswith("[Chunk 1 · ")


@pytest.mark.asyncio
async def test_rate_limit_propagates_when_no_fallback():
    with pytest.raises(ProviderRateLimited):
        await _run([_Fake("deepgram", True, ProviderRateLimited("slow", retry_after=5))], 60)
