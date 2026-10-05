"""Presigned upload trio + dead-letter proof tests (Phase 16-01 / 16-03).

Covers POST /lectures/upload-url, POST /lectures/{id}/upload-complete,
GET /lectures/{id}/audio-url, POST /lectures/{id}/retry and the
FORCE_FAIL_LECTURE_ID deterministic failure hook.
"""
import tempfile
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from models.academic import TeacherAssignmentDB
from models.job import JobCreate
from models.lecture import LectureDB
from models.user import UserPublic
from server import app


@pytest.fixture
def client():
    return TestClient(app)


def _teacher(uid="usr_t1"):
    return UserPublic(
        id=uid,
        email="teacher@example.com",
        name="Prof. Turing",
        role="teacher",
        created_at=datetime.now(timezone.utc),
    )


def _admin():
    return UserPublic(
        id="usr_admin",
        email="admin@example.com",
        name="Administrator",
        role="admin",
        created_at=datetime.now(timezone.utc),
    )


def _lecture(lecture_id="lec_100", teacher_id="usr_t1", status="uploading",
             class_id="cls_1", mime="audio/mpeg",
             key="classes/cls_1/lectures/lec_100/recording/a.mp3"):
    return LectureDB(
        id=lecture_id,
        teacher_id=teacher_id,
        title="T",
        class_id=class_id,
        audio_object_key=key,
        audio_filename="a.mp3",
        audio_mime=mime,
        status=status,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _override(user):
    from core.deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: user


def _clear():
    app.dependency_overrides.clear()


class TestUploadUrl:
    def _payload(self, **kw):
        base = {
            "title": "L1",
            "class_id": "cls_1",
            "filename": "a.mp3",
            "content_type": "audio/mpeg",
            "size": 1024,
        }
        base.update(kw)
        return base

    @patch("routes.lectures.enqueue_job", new_callable=AsyncMock)
    @patch("routes.lectures.get_storage")
    @patch("routes.lectures.LectureRepository")
    @patch("routes.lectures.TeacherAssignmentRepository")
    def test_happy_path(self, mock_ta, mock_lec, mock_storage_fn, mock_enq, client):
        _override(_teacher())
        try:
            mock_ta.return_value.find_existing = AsyncMock(return_value=TeacherAssignmentDB(
                id="ta_1", class_id="cls_1", teacher_id="usr_t1",
                active=True, assigned_at=datetime.now(timezone.utc),
            ))
            mock_lec_inst = mock_lec.return_value
            mock_lec_inst.new_id.return_value = "lec_100"
            mock_lec_inst.create = AsyncMock()
            storage = AsyncMock()
            storage.presign_post = AsyncMock(return_value={
                "url": "https://s3.example/upload",
                "fields": {"Content-Type": "audio/mpeg", "key": "x", "policy": "p"},
            })
            mock_storage_fn.return_value = storage

            r = client.post("/api/lectures/upload-url", json=self._payload())
            assert r.status_code == 200, r.text
            data = r.json()
            assert data["key"].startswith("classes/cls_1/lectures/")
            assert data["expires_in"] == 900
            assert "Content-Type" in data["fields"]
            assert data["lecture_id"] == "lec_100"
            # created row is uploading
            created = mock_lec_inst.create.call_args[0][0]
            assert created.status == "uploading"
            assert created.audio_object_key == data["key"]
        finally:
            _clear()

    @patch("routes.lectures.get_storage")
    @patch("routes.lectures.LectureRepository")
    @patch("routes.lectures.TeacherAssignmentRepository")
    def test_validations(self, mock_ta, mock_lec, mock_storage_fn, client):
        _override(_teacher())
        try:
            mock_ta.return_value.find_existing = AsyncMock(return_value=TeacherAssignmentDB(
                id="ta_1", class_id="cls_1", teacher_id="usr_t1",
                active=True, assigned_at=datetime.now(timezone.utc),
            ))
            mock_lec.return_value.new_id.return_value = "lec_x"
            mock_lec.return_value.create = AsyncMock()
            mock_storage_fn.return_value = AsyncMock()

            r = client.post("/api/lectures/upload-url", json=self._payload(size=209715201))
            assert r.status_code == 413

            r = client.post("/api/lectures/upload-url",
                            json=self._payload(content_type="video/mp4", filename="v.mp4"))
            assert r.status_code == 400
        finally:
            _clear()

    @patch("routes.lectures.LectureRepository")
    @patch("routes.lectures.TeacherAssignmentRepository")
    def test_forbidden_unassigned(self, mock_ta, mock_lec, client):
        _override(_teacher())
        try:
            mock_ta.return_value.find_existing = AsyncMock(return_value=None)
            r = client.post("/api/lectures/upload-url", json=self._payload())
            assert r.status_code == 403
        finally:
            _clear()

    @patch("routes.lectures.get_storage")
    @patch("routes.lectures.LectureRepository")
    @patch("routes.lectures.TeacherAssignmentRepository")
    def test_local_storage_501(self, mock_ta, mock_lec, mock_storage_fn, client):
        from services.storage_service import LocalStorage
        _override(_teacher())
        try:
            mock_ta.return_value.find_existing = AsyncMock(return_value=TeacherAssignmentDB(
                id="ta_1", class_id="cls_1", teacher_id="usr_t1",
                active=True, assigned_at=datetime.now(timezone.utc),
            ))
            mock_lec.return_value.new_id.return_value = "lec_loc"
            mock_lec.return_value.create = AsyncMock()
            mock_storage_fn.return_value = LocalStorage(tempfile.mkdtemp())

            r = client.post("/api/lectures/upload-url", json=self._payload())
            assert r.status_code == 501
        finally:
            _clear()

    def test_route_order(self, client):
        import inspect
        import routes.lectures as mod
        src = inspect.getsource(mod)
        assert src.index('"/upload-url"') < src.index('"/{lecture_id}"')


class TestUploadComplete:
    def _setup(self, mock_lec_cls, mock_storage_fn, mock_enq, lecture):
        inst = mock_lec_cls.return_value
        inst.get_by_id = AsyncMock(side_effect=[lecture, _lecture(
            lecture_id=lecture.id, teacher_id=lecture.teacher_id,
            status="queued", class_id=lecture.class_id,
            mime=lecture.audio_mime, key=lecture.audio_object_key)])
        inst.update_fields = AsyncMock()
        return inst

    @patch("routes.lectures.enqueue_job", new_callable=AsyncMock)
    @patch("routes.lectures.get_storage")
    @patch("routes.lectures.LectureRepository")
    def test_complete_happy_path_enqueues_once(self, mock_lec, mock_storage_fn, mock_enq, client):
        _override(_teacher())
        try:
            lec = _lecture()
            inst = self._setup(mock_lec, mock_storage_fn, mock_enq, lec)
            storage = AsyncMock()
            storage.head_object = AsyncMock(return_value={"size": 1024, "content_type": "audio/mpeg"})
            mock_storage_fn.return_value = storage
            mock_enq.return_value = AsyncMock(id="job_1")

            r = client.post(f"/api/lectures/{lec.id}/upload-complete")
            assert r.status_code == 202, r.text
            assert mock_enq.call_count == 1
        finally:
            _clear()

    @patch("routes.lectures.get_storage")
    @patch("routes.lectures.LectureRepository")
    def test_missing_object_409(self, mock_lec, mock_storage_fn, client):
        _override(_teacher())
        try:
            lec = _lecture()
            mock_lec.return_value.get_by_id = AsyncMock(return_value=lec)
            storage = AsyncMock()
            storage.head_object = AsyncMock(side_effect=FileNotFoundError("x"))
            mock_storage_fn.return_value = storage
            r = client.post(f"/api/lectures/{lec.id}/upload-complete")
            assert r.status_code == 409
            assert "not uploaded" in r.json()["detail"].lower()
        finally:
            _clear()

    @patch("routes.lectures.get_storage")
    @patch("routes.lectures.LectureRepository")
    def test_zero_byte_413_and_deleted(self, mock_lec, mock_storage_fn, client):
        _override(_teacher())
        try:
            lec = _lecture()
            mock_lec.return_value.get_by_id = AsyncMock(return_value=lec)
            storage = AsyncMock()
            storage.head_object = AsyncMock(return_value={"size": 0, "content_type": "audio/mpeg"})
            storage.delete = AsyncMock()
            mock_storage_fn.return_value = storage
            r = client.post(f"/api/lectures/{lec.id}/upload-complete")
            assert r.status_code == 413
            assert storage.delete.call_count == 1
        finally:
            _clear()

    @patch("routes.lectures.get_storage")
    @patch("routes.lectures.LectureRepository")
    def test_oversize_413(self, mock_lec, mock_storage_fn, client):
        _override(_teacher())
        try:
            lec = _lecture()
            mock_lec.return_value.get_by_id = AsyncMock(return_value=lec)
            storage = AsyncMock()
            storage.head_object = AsyncMock(
                return_value={"size": 201 * 1024 * 1024, "content_type": "audio/mpeg"})
            storage.delete = AsyncMock()
            mock_storage_fn.return_value = storage
            r = client.post(f"/api/lectures/{lec.id}/upload-complete")
            assert r.status_code == 413
        finally:
            _clear()

    @patch("routes.lectures.get_storage")
    @patch("routes.lectures.LectureRepository")
    def test_mime_mismatch_400(self, mock_lec, mock_storage_fn, client):
        _override(_teacher())
        try:
            lec = _lecture(mime="audio/mpeg")
            mock_lec.return_value.get_by_id = AsyncMock(return_value=lec)
            storage = AsyncMock()
            storage.head_object = AsyncMock(return_value={"size": 100, "content_type": "audio/wav"})
            mock_storage_fn.return_value = storage
            # audio/wav normalizes to audio/wav != audio/mpeg -> 400
            r = client.post(f"/api/lectures/{lec.id}/upload-complete")
            assert r.status_code == 400
        finally:
            _clear()

    @patch("routes.lectures.enqueue_job", new_callable=AsyncMock)
    @patch("routes.lectures.get_storage")
    @patch("routes.lectures.LectureRepository")
    def test_second_call_idempotent(self, mock_lec, mock_storage_fn, mock_enq, client):
        _override(_teacher())
        try:
            lec = _lecture(status="queued")
            mock_lec.return_value.get_by_id = AsyncMock(return_value=lec)
            mock_storage_fn.return_value = AsyncMock()
            r = client.post(f"/api/lectures/{lec.id}/upload-complete")
            assert r.status_code == 202
            assert mock_enq.call_count == 0
        finally:
            _clear()


class TestAudioUrl:
    @patch("routes.lectures.get_storage")
    @patch("routes.lectures.verify_lecture_access", new_callable=AsyncMock)
    def test_audio_url_ok(self, mock_verify, mock_storage_fn, client):
        _override(_teacher())
        try:
            mock_verify.return_value = _lecture()
            storage = AsyncMock()
            storage.presign_get = AsyncMock(return_value="https://s3.example/audio.mp3?x=1")
            mock_storage_fn.return_value = storage
            r = client.get("/api/lectures/lec_100/audio-url")
            assert r.status_code == 200, r.text
            data = r.json()
            assert data["url"].startswith("https://")
            assert data["expires_in"] == 900
        finally:
            _clear()

    @patch("routes.lectures.get_storage")
    @patch("routes.lectures.verify_lecture_access", new_callable=AsyncMock)
    def test_audio_url_local_501(self, mock_verify, mock_storage_fn, client):
        from services.storage_service import LocalStorage
        _override(_teacher())
        try:
            mock_verify.return_value = _lecture()
            mock_storage_fn.return_value = LocalStorage(tempfile.mkdtemp())
            r = client.get("/api/lectures/lec_100/audio-url")
            assert r.status_code == 501
        finally:
            _clear()

    @patch("routes.lectures.verify_lecture_access", new_callable=AsyncMock)
    def test_audio_url_forbidden(self, mock_verify, client):
        from fastapi import HTTPException
        _override(_teacher())
        try:
            mock_verify.side_effect = HTTPException(status_code=404, detail="Lecture not found")
            r = client.get("/api/lectures/lec_100/audio-url")
            assert r.status_code == 404
        finally:
            _clear()


class _FailingWorker:
    """Minimal BaseWorker subclass that always raises (dead-letter proof)."""

    def __init__(self):
        from workers.base import BaseWorker

        class _W(BaseWorker):
            stage = "transcribe"
            queue_name = "transcribe"
            visibility_timeout = 300

            async def process_job(self, job, ctx):
                raise RuntimeError("boom-poison")

        self._w = _W()

    def __getattr__(self, name):
        return getattr(self._w, name)


@pytest.mark.asyncio
class TestDeadLetter:
    async def test_receive_count_5_marks_dead_letter(self):
        from core.queue_backend import get_queue_backend
        from repositories.job_repository import JobRepository
        from repositories.lecture_repository import LectureRepository
        from services.queue_client import enqueue_job

        backend = get_queue_backend()
        repo = JobRepository()
        worker = _FailingWorker()

        job = await enqueue_job(JobCreate(lecture_id="l1", stage="transcribe", version=1))
        q = backend._queues.get("transcribe", [])
        assert len(q) == 1
        q[0]["receive_count"] = 4  # next receive is #5

        handled = await worker.run_once(wait_seconds=0)
        assert handled is True

        job_db = await repo.get(job.id)
        assert job_db.status == "dead_letter"

        lec = await LectureRepository().get_by_id("l1")
        assert lec.status == "dead_letter"

        # message left for broker DLQ (not deleted)
        assert len(backend._queues.get("transcribe", [])) == 1

    def test_force_fail_hook_gating(self, monkeypatch):
        from workers.transcription import is_forced_failure

        monkeypatch.delenv("FORCE_FAIL_LECTURE_ID", raising=False)
        assert is_forced_failure("lec_x") is False

        monkeypatch.setenv("FORCE_FAIL_LECTURE_ID", "lec_x")
        monkeypatch.setenv("ENV", "prod")
        assert is_forced_failure("lec_x") is False

        monkeypatch.setenv("ENV", "production")
        assert is_forced_failure("lec_x") is False

        for env in ("aws", "demo", "staging"):
            monkeypatch.setenv("ENV", env)
            assert is_forced_failure("lec_x") is True
            assert is_forced_failure("other") is False

    @pytest.mark.asyncio
    async def test_force_fail_raises_before_provider(self, monkeypatch):
        import os

        from models.job import JobDB
        from workers.transcription import TranscriptionWorker

        monkeypatch.setenv("FORCE_FAIL_LECTURE_ID", "lec_poison")
        monkeypatch.setenv("ENV", "demo")
        worker = TranscriptionWorker.__new__(TranscriptionWorker)
        job = JobDB(
            id="job_poison", lecture_id="lec_poison", stage="transcribe",
            version=1, status="queued", attempt=0,
            created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
        )
        with pytest.raises(RuntimeError, match="forced-failure-proof"):
            await worker.process_job(job, ctx=None)


class TestRetry:
    def _fake_session(self, max_version=1):
        from unittest.mock import AsyncMock, MagicMock

        result = MagicMock()
        result.scalar.return_value = max_version
        session = AsyncMock()
        session.execute = AsyncMock(return_value=result)
        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(return_value=session)
        cm.__aexit__ = AsyncMock(return_value=False)
        maker = MagicMock(return_value=cm)
        return maker

    @patch("routes.lectures.enqueue_job", new_callable=AsyncMock)
    @patch("core.sql_db.session_maker")
    @patch("routes.lectures.LectureRepository")
    def test_admin_resets_dead_letter(self, mock_lec, mock_sm, mock_enq, client):
        from unittest.mock import AsyncMock

        _override(_admin())
        try:
            dead = _lecture(lecture_id="lec_dl", status="dead_letter")
            queued = _lecture(lecture_id="lec_dl", status="queued")
            inst = mock_lec.return_value
            inst.get_by_id = AsyncMock(side_effect=[dead, queued])
            inst.update_fields = AsyncMock()
            mock_sm.return_value = self._fake_session(max_version=1)()
            # core.sql_db.session_maker is called as session_maker()()
            import core.sql_db
            orig = core.sql_db.session_maker
            core.sql_db.session_maker = lambda: self._fake_session(max_version=1)
            try:
                r = client.post("/api/lectures/lec_dl/retry")
            finally:
                core.sql_db.session_maker = orig
            assert r.status_code == 200, r.text
            assert r.json()["status"] == "queued"
            assert mock_enq.call_count == 1
            payload = mock_enq.call_args[0][0]
            assert payload.version == 2
            assert payload.stage == "transcribe"
        finally:
            _clear()

    @patch("routes.lectures.LectureRepository")
    def test_non_admin_forbidden(self, mock_lec, client):
        _override(_teacher())
        try:
            r = client.post("/api/lectures/lec_dl/retry")
            assert r.status_code == 403
        finally:
            _clear()

    @patch("routes.lectures.LectureRepository")
    def test_non_dead_letter_409(self, mock_lec, client):
        from unittest.mock import AsyncMock

        _override(_admin())
        try:
            mock_lec.return_value.get_by_id = AsyncMock(
                return_value=_lecture(lecture_id="lec_dl", status="ready"))
            r = client.post("/api/lectures/lec_dl/retry")
            assert r.status_code == 409
        finally:
            _clear()
