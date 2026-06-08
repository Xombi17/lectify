"""Audio chunking + hierarchical pipeline tests for LectureMind AI.

Covers:
  - services/audio_chunker.py: get_duration_seconds, split_into_chunks,
    cleanup_chunks, format_timestamp
  - models/lecture.py: LectureDB defaults for progress_* + chunk_count
  - services/lecture_service.py:
      * normalize_mime()
      * process_lecture_background() single-shot path (short audio)
      * process_lecture_background() chunked path (long audio)
      * error path cleans up chunks + sets status='error'
  - Regression smoke: POST /api/lectures response shape includes the new
    progress_* / chunk_count fields (defaulted by the model).

All AI calls are stubbed via a FakeAI provider; ffmpeg is the real binary.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import sys
import struct
from pathlib import Path

import pytest
import requests

sys.path.insert(0, "/app/backend")


# --- _arun helper: fresh event loop ---
def _arun(coro_factory):
    return asyncio.run(coro_factory())


def _load_backend_url() -> str:
    if os.environ.get("REACT_APP_BACKEND_URL"):
        return os.environ["REACT_APP_BACKEND_URL"]
    with open("/app/frontend/.env", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("REACT_APP_BACKEND_URL not found")


BASE_URL = _load_backend_url().rstrip("/")
API = f"{BASE_URL}/api"

# ---------- ffmpeg-generated test assets ----------

@pytest.fixture(scope="session")
def tmp_audio_dir(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("chunk_assets")


def _ffmpeg_sine(out_path: Path, duration: float, codec: str = "libmp3lame",
                 bitrate: str = "32k") -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
        "-acodec", codec, "-b:a", bitrate, "-ac", "1",
        str(out_path),
    ]
    r = subprocess.run(cmd, capture_output=True, timeout=120)
    assert r.returncode == 0, f"ffmpeg failed: {r.stderr.decode('utf-8', 'ignore')}"
    return out_path


@pytest.fixture(scope="session")
def mp3_70s(tmp_audio_dir) -> Path:
    return _ffmpeg_sine(tmp_audio_dir / "TEST_70s.mp3", 70.0)


# ============================================================================
# audio_chunker module tests
# ============================================================================

# --- format_timestamp ---
class TestFormatTimestamp:
    def test_below_hour(self):
        from services.audio_chunker import format_timestamp
        assert format_timestamp(125) == "02:05"

    def test_with_hour(self):
        from services.audio_chunker import format_timestamp
        assert format_timestamp(3661) == "01:01:01"

    def test_zero(self):
        from services.audio_chunker import format_timestamp
        assert format_timestamp(0) == "00:00"


# --- get_duration_seconds ---
class TestGetDuration:
    def test_returns_float_for_mp3(self, mp3_70s):
        from services.audio_chunker import get_duration_seconds

        async def _do():
            return await get_duration_seconds(mp3_70s)

        dur = _arun(_do)
        assert isinstance(dur, float)
        assert 68.0 <= dur <= 72.0, f"expected ~70s, got {dur}"


# --- split_into_chunks + cleanup ---
class TestSplitAndCleanup:
    def test_split_70s_into_30s_chunks_and_cleanup(self, mp3_70s):
        from services.audio_chunker import split_into_chunks, cleanup_chunks

        async def _split():
            return await split_into_chunks(mp3_70s, chunk_seconds=30)

        chunks = _arun(_split)
        try:
            assert len(chunks) >= 2, f"expected >=2 chunks, got {len(chunks)}"
            for c in chunks:
                assert c.exists(), f"chunk missing: {c}"
                assert c.stat().st_size > 0
        finally:
            cleanup_chunks(chunks)

        for c in chunks:
            assert not c.exists(), f"chunk not cleaned: {c}"


# ============================================================================
# LectureDB model defaults
# ============================================================================

class TestLectureDBDefaults:
    def test_progress_and_chunk_defaults(self):
        from models.lecture import LectureDB
        d = LectureDB(
            id="x", teacher_id="t", title="x",
            audio_object_key="k", audio_filename="f.mp3", audio_mime="audio/mpeg",
        )
        assert d.progress_step == 0
        assert d.progress_total == 0
        assert d.progress_label is None
        assert d.chunk_count is None


# ============================================================================
# normalize_mime
# ============================================================================

class TestNormalizeMime:
    def test_passthrough_audio_mpeg(self):
        from services.lecture_service import normalize_mime
        assert normalize_mime("audio/mpeg", "x.mp3") == "audio/mpeg"

    def test_ext_only_mp3(self):
        from services.lecture_service import normalize_mime
        assert normalize_mime("application/octet-stream", "lecture.mp3") == "audio/mpeg"

    def test_rejects_non_audio(self):
        from services.lecture_service import normalize_mime
        assert normalize_mime("application/pdf", "x.pdf") is None
        assert normalize_mime("text/plain", "x.txt") is None


# ============================================================================
# FakeAI provider + pipeline tests
# ============================================================================

class _FakeMaterials:
    """Returned by FakeAI.generate_study_materials / merge_chunk_digests.
    Tests use it via .summary / .smart_notes / .key_concepts attrs."""


def _build_fake_materials():
    from models.lecture import StudyMaterials, QuizQuestion, Flashcard
    return StudyMaterials(
        summary="FAKE summary",
        smart_notes=["fake note 1", "fake note 2"],
        key_concepts=["k1", "k2"],
        quiz=[QuizQuestion(question="q?", options=["a", "b"], answer_index=0)],
        flashcards=[Flashcard(front="f", back="b")],
    )


class FakeAI:
    def __init__(self, fail_transcribe_on_chunk: int | None = None):
        self.transcribe_calls: list[tuple[str, str]] = []
        self.digest_calls = 0
        self.merge_calls = 0
        self.generate_calls = 0
        self.embed_calls = 0
        self._fail_chunk = fail_transcribe_on_chunk

    async def transcribe_audio(self, path, mime):
        self.transcribe_calls.append((str(path), mime))
        if self._fail_chunk is not None and len(self.transcribe_calls) == self._fail_chunk:
            raise RuntimeError("FAKE transcribe failure")
        return "fake chunk text"

    async def generate_study_materials(self, transcript):
        self.generate_calls += 1
        return _build_fake_materials()

    async def digest_chunk(self, chunk_text):
        self.digest_calls += 1
        return {"chunk_summary": "s", "chunk_notes": ["n"], "key_concepts": ["k"]}

    async def merge_chunk_digests(self, digests):
        self.merge_calls += 1
        return _build_fake_materials()

    async def embed(self, text):
        self.embed_calls += 1
        return [0.1] * 8


def _seed_lecture_doc(audio_path: Path, mime: str, title: str = "TEST_chunk lecture") -> str:
    """Insert an 'uploaded' lecture row referencing a real on-disk file."""
    from repositories.lecture_repository import LectureRepository
    from models.lecture import LectureDB
    from services.storage_service import get_storage

    storage = get_storage()
    root = storage.local_path("")  # storage root path
    # Place audio under storage root so storage.local_path(key) resolves correctly
    key = f"lectures/TEST_chunk/{audio_path.name}"
    dst = storage.local_path(key)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(audio_path, dst)
    assert dst.exists()

    async def _seed():
        repo = LectureRepository()
        lid = repo.new_id()
        doc = LectureDB(
            id=lid, teacher_id="TEST_teacher", title=title,
            audio_object_key=key, audio_filename=audio_path.name,
            audio_mime=mime, status="uploaded",
        )
        d = doc.model_dump()
        d["created_at"] = d["created_at"].isoformat()
        d["updated_at"] = d["updated_at"].isoformat()
        await repo.col.insert_one(d)
        return lid

    return _arun(_seed), key


def _get_lecture(lid: str):
    from repositories.lecture_repository import LectureRepository

    async def _do():
        return await LectureRepository().get_by_id(lid)

    return _arun(_do)


def _delete_lecture(lid: str, key: str):
    from repositories.lecture_repository import LectureRepository
    from services.storage_service import get_storage

    async def _do():
        await LectureRepository().col.delete_one({"id": lid})

    _arun(_do)
    try:
        get_storage().local_path(key).unlink()
    except OSError:
        pass


# --- Single-shot path (short audio) ---
class TestSingleShotPipeline:
    def test_short_audio_takes_single_shot(self, mp3_70s, monkeypatch):
        import services.lecture_service as ls

        fake = FakeAI()
        monkeypatch.setattr(ls, "get_ai_service", lambda: fake)

        lid, key = _seed_lecture_doc(mp3_70s, "audio/mpeg",
                                     title="TEST_chunk single")
        try:
            _arun(lambda: ls.process_lecture_background(lid))
            lec = _get_lecture(lid)
            assert lec is not None
            assert lec.status == "ready", f"status={lec.status} err={lec.error_message}"
            assert lec.progress_label == "Done"
            assert lec.progress_step == lec.progress_total
            assert lec.transcript and lec.transcript == "fake chunk text"
            assert lec.materials.smart_notes == ["fake note 1", "fake note 2"]
            # embedding is list[float] (since FakeAI.embed returned a list) or None
            assert lec.embedding is None or (
                isinstance(lec.embedding, list)
                and all(isinstance(x, float) for x in lec.embedding)
            )
            # Single-shot path uses generate_study_materials, not chunked methods
            assert fake.generate_calls == 1
            assert fake.digest_calls == 0
            assert fake.merge_calls == 0
            assert len(fake.transcribe_calls) == 1
            # chunk_count should NOT have been set (single-shot)
            assert lec.chunk_count is None
        finally:
            _delete_lecture(lid, key)


# --- Chunked path (long audio) ---
@pytest.fixture(scope="session")
def mp3_1900s(tmp_audio_dir) -> Path:
    return _ffmpeg_sine(tmp_audio_dir / "TEST_1900s.mp3", 1900.0, bitrate="24k")


class TestChunkedPipeline:
    def test_long_audio_takes_chunked_path(self, mp3_1900s, monkeypatch):
        import services.lecture_service as ls

        fake = FakeAI()
        monkeypatch.setattr(ls, "get_ai_service", lambda: fake)

        lid, key = _seed_lecture_doc(mp3_1900s, "audio/mpeg",
                                     title="TEST_chunk long")
        try:
            _arun(lambda: ls.process_lecture_background(lid))
            lec = _get_lecture(lid)
            assert lec is not None, "lecture vanished"
            assert lec.status == "ready", \
                f"status={lec.status} err={lec.error_message}"
            assert lec.chunk_count is not None and lec.chunk_count > 1, \
                f"chunk_count={lec.chunk_count}"
            assert lec.duration_seconds and 1850 <= lec.duration_seconds <= 1950
            assert lec.progress_label == "Done"
            assert lec.progress_step == lec.progress_total
            # Chunked methods invoked
            assert fake.digest_calls == lec.chunk_count
            assert fake.merge_calls == 1
            assert len(fake.transcribe_calls) == lec.chunk_count
            # NOT the single-shot AI method
            assert fake.generate_calls == 0
            # Merged materials populated
            assert lec.materials.summary == "FAKE summary"
            assert lec.materials.smart_notes  # non-empty
            # Stitched transcript has chunk markers
            assert "[Chunk 1" in lec.transcript
            # Chunks directory was cleaned up
            chunks_dir = mp3_1900s.parent / ".chunks"
            # NB: chunks are written next to the source path inside storage
            from services.storage_service import get_storage
            src_in_storage = get_storage().local_path(key)
            chunks_dir2 = src_in_storage.parent / ".chunks"
            assert not chunks_dir2.exists() or not any(chunks_dir2.iterdir()), \
                f".chunks not cleaned: {list(chunks_dir2.iterdir())}"
        finally:
            _delete_lecture(lid, key)


# --- Error path: AI fails on chunk N ---
class TestChunkedErrorPath:
    def test_chunk_transcribe_failure_sets_error_and_cleans_up(self, mp3_1900s,
                                                                monkeypatch):
        import services.lecture_service as ls

        # Fail on the 2nd transcribe call (i.e. second chunk)
        fake = FakeAI(fail_transcribe_on_chunk=2)
        monkeypatch.setattr(ls, "get_ai_service", lambda: fake)

        lid, key = _seed_lecture_doc(mp3_1900s, "audio/mpeg",
                                     title="TEST_chunk err")
        try:
            _arun(lambda: ls.process_lecture_background(lid))
            lec = _get_lecture(lid)
            assert lec is not None
            assert lec.status == "error", f"status={lec.status}"
            assert lec.error_message and "FAKE" in lec.error_message
            # chunks dir gone (cleaned up in finally)
            from services.storage_service import get_storage
            src = get_storage().local_path(key)
            chunks_dir = src.parent / ".chunks"
            assert not chunks_dir.exists() or not any(chunks_dir.iterdir()), \
                f".chunks not cleaned after error: {list(chunks_dir.iterdir())}"
        finally:
            _delete_lecture(lid, key)


# ============================================================================
# Smoke: POST /api/lectures response shape (regression for new fields)
# ============================================================================

TEACHER = {"email": "teacher@lecturemind.example.com", "password": "Password123!",
           "name": "Teacher One", "role": "teacher"}


def _signup_or_login(creds):
    r = requests.post(f"{API}/auth/signup", json=creds, timeout=30)
    if r.status_code == 201:
        return r.json()
    if r.status_code == 409:
        r2 = requests.post(f"{API}/auth/login",
                           json={"email": creds["email"], "password": creds["password"]},
                           timeout=30)
        return r2.json()
    pytest.fail(f"signup unexpected {r.status_code}: {r.text}")


def _wav_bytes(seconds=0.1, sample_rate=8000):
    n = int(seconds * sample_rate)
    data = b"\x00\x00" * n
    return (b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVE" + b"fmt "
            + struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16)
            + b"data" + struct.pack("<I", len(data)) + data)


class TestSmokeResponseShape:
    def test_post_lecture_202_includes_new_fields(self):
        auth = _signup_or_login(TEACHER)
        h = {"Authorization": f"Bearer {auth['access_token']}"}
        files = {"file": ("TEST_smoke.wav", _wav_bytes(0.5), "audio/wav")}
        data = {"title": "TEST_chunk smoke shape", "subject": "TEST", "semester": "F"}
        r = requests.post(f"{API}/lectures", headers=h, files=files,
                          data=data, timeout=30)
        assert r.status_code == 202, r.text
        body = r.json()
        # Model defaults for new fields must appear in response
        assert "progress_step" in body
        assert "progress_total" in body
        assert "progress_label" in body
        assert "chunk_count" in body
        assert body["progress_step"] == 0
        assert body["progress_total"] == 0
        assert body["progress_label"] is None
        assert body["chunk_count"] is None

        # Cleanup the seeded lecture (background may fail since no GEMINI key)
        lid = body["id"]
        from repositories.lecture_repository import LectureRepository

        async def _del():
            await LectureRepository().col.delete_one({"id": lid})

        _arun(_del)
