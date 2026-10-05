import pytest
from sqlalchemy import select
from repositories.job_chunk_repository import JobChunkRepository
from models.orm import JobChunkORM
from core.sql_db import session_maker

@pytest.mark.asyncio
async def test_job_chunk_repository_parity_and_idempotency():
    """
    Test behavior:
    - ensure(L,1,5) twice -> 5 rows
    - mark_done(2,"x") twice -> one row, status done, attempts unchanged on the second call
    - mark_failed on a done chunk is ignored (done is terminal)
    - pending() after done {0,1} -> [2,3,4]
    - merged_text with done rows inserted out of order -> ordered by chunk_index
    """
    repo = JobChunkRepository()
    lecture_id = "lec-1"
    version = 1
    
    # 1. ensure(L,1,5) twice
    await repo.ensure(lecture_id, version, 5)
    await repo.ensure(lecture_id, version, 5) # idempotent
    
    async with session_maker()() as session:
        result = await session.execute(select(JobChunkORM).filter_by(lecture_id=lecture_id, version=version))
        count = len(result.scalars().all())
        assert count == 5
        
    # 2. mark_done(0, "text0") twice
    await repo.mark_done(lecture_id, version, 0, "text0")
    await repo.mark_done(lecture_id, version, 0, "text0_again") # ignored because it's already done
    
    async with session_maker()() as session:
        result = await session.execute(select(JobChunkORM).filter_by(lecture_id=lecture_id, version=version, chunk_index=0))
        row = result.scalar_one()
        assert row.status == "done"
        assert row.text == "text0" # Should not be updated to text0_again if already done
        
    # 3. mark_failed on a done chunk is ignored
    await repo.mark_failed(lecture_id, version, 0, "some error")
    async with session_maker()() as session:
        result = await session.execute(select(JobChunkORM).filter_by(lecture_id=lecture_id, version=version, chunk_index=0))
        row = result.scalar_one()
        assert row.status == "done" # remains done
        assert row.attempts == 0 # attempts shouldn't increment
        
    # 4. mark_done 1
    await repo.mark_done(lecture_id, version, 1, "text1")
    
    # pending() after done {0,1} -> [2,3,4]
    pending_list = await repo.pending(lecture_id, version)
    assert pending_list == [2, 3, 4]
    
    # 5. merged_text with done rows out of order
    # Let's mark 4, then 2, then 3
    await repo.mark_done(lecture_id, version, 4, "text4")
    await repo.mark_done(lecture_id, version, 2, "text2")
    await repo.mark_done(lecture_id, version, 3, "text3")
    
    merged = await repo.merged_text(lecture_id, version)
    assert merged == "text0\n\ntext1\n\ntext2\n\ntext3\n\ntext4"

@pytest.mark.asyncio
async def test_chunked_redelivery(tmp_path, monkeypatch):
    """
    Simulate a TranscriptionWorker that fails on chunk index 2.
    Then simulate redelivery and verify it resumes from index 2.
    """
    from workers.transcription import TranscriptionWorker
    from models.job import JobDB
    from workers.base import JobContext
    from services.ai_service import AIProvider
    from services.storage_service import StorageService
    from unittest.mock import AsyncMock, patch

    # 1. Setup mock storage to yield a fake audio file
    fake_audio = tmp_path / "fake.mp3"
    fake_audio.write_text("dummy")
    
    class FakeStorage(StorageService):
        import contextlib
        @contextlib.asynccontextmanager
        async def open_local(self, key):
            yield fake_audio
            
        async def upload_file(self, *args, **kwargs): pass
        async def upload_fileobj(self, *args, **kwargs): pass
        async def delete(self, *args, **kwargs): pass
        async def presign_get(self, *args, **kwargs): return ""
        async def presign_post(self, *args, **kwargs): return {}
        async def head_object(self, *args, **kwargs): return {}
        async def save(self, *args, **kwargs): pass
        async def stream(self, *args, **kwargs): pass

    # 2. Setup mock chunker to return 5 fake chunks and set duration > threshold
    async def mock_split(*args, **kwargs):
        return [fake_audio for _ in range(5)]
        
    async def mock_duration(*args, **kwargs):
        from services.lecture_service import CHUNK_THRESHOLD_SECONDS
        return CHUNK_THRESHOLD_SECONDS + 10.0

    # 3. Setup mock AI service that fails on the 3rd chunk (index 2)
    ai_mock = AsyncMock(spec=AIProvider)
    call_count = 0
    async def mock_transcribe(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 3:
            raise ValueError("API error on chunk 3")
        return f"transcribed {call_count}"
    ai_mock.transcribe_audio.side_effect = mock_transcribe

    worker = TranscriptionWorker(max_jobs=1)
    job = JobDB(id="j1", lecture_id="lec-1", stage="transcribe", version=1, status="processing")
    ctx = AsyncMock(spec=JobContext)

    with patch("workers.transcription.get_storage", return_value=FakeStorage()), \
         patch("workers.transcription.get_ai_service", return_value=ai_mock), \
         patch("workers.transcription.get_duration_seconds", side_effect=mock_duration), \
         patch("workers.transcription.split_into_chunks", side_effect=mock_split):
         
         # FIRST ATTEMPT
         with pytest.raises(ValueError, match="API error on chunk 3"):
             await worker.process_job(job, ctx)
             
         assert call_count == 3
         
         # SECOND ATTEMPT
         # Now ai_mock will not fail (call_count continues from 3, so not == 3)
         await worker.process_job(job, ctx)
         
         # We expect it to have called AI service only 3 MORE times (for indexes 2, 3, 4)
         # because indexes 0, 1 were already done.
         assert call_count == 6
         
    # Check the final transcript in DB
    from repositories.lecture_repository import LectureRepository
    repo = LectureRepository()
    lecture = await repo.get_by_id("lec-1")
    assert lecture.transcript is not None
    # We can check that the texts are in order
    assert "transcribed 1" in lecture.transcript
    assert "transcribed 2" in lecture.transcript
    assert "transcribed 4" in lecture.transcript # which is the 2nd attempt for index 2
    assert "transcribed 5" in lecture.transcript
    assert "transcribed 6" in lecture.transcript
