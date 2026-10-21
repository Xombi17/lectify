"""Tests for lecture upload and repository scoping."""
import io
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from models.academic import TeacherAssignmentDB
from models.lecture import LectureDB, StudyMaterials
from models.user import UserPublic
from server import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.asyncio
async def test_lecture_repository_persists_class_and_slot(monkeypatch):
    """Verify LectureRepository stores and hydrates class_id and timetable_slot_id."""
    monkeypatch.setenv("DATABASE_BACKEND", "postgres")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    from core.sql_db import init_models
    from repositories._sql.lecture_repository import LectureRepository

    await init_models()
    repo = LectureRepository()

    lecture_id = f"lec_{uuid.uuid4().hex[:8]}"
    class_id = f"cls_{uuid.uuid4().hex[:8]}"
    slot_id = f"slot_{uuid.uuid4().hex[:8]}"

    lecture = LectureDB(
        id=lecture_id,
        teacher_id="usr_teacher",
        title="Distributed Systems Lecture 1",
        subject="Distributed Systems",
        semester="Sem 6",
        class_id=class_id,
        timetable_slot_id=slot_id,
        audio_object_key="lectures/test.mp3",
        audio_filename="test.mp3",
        audio_mime="audio/mpeg",
        status="uploaded",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    created = await repo.create(lecture)
    assert created.class_id == class_id
    assert created.timetable_slot_id == slot_id

    fetched = await repo.get_by_id(lecture_id)
    assert fetched is not None
    assert fetched.class_id == class_id
    assert fetched.timetable_slot_id == slot_id

    summaries = await repo.list_by_teacher("usr_teacher")
    match = next((s for s in summaries if s.id == lecture_id), None)
    assert match is not None
    assert match.class_id == class_id
    assert match.timetable_slot_id == slot_id


def test_upload_lecture_missing_class_id_returns_422(client):
    """Omitting class_id on upload must fail with HTTP 422 Unprocessable Entity."""
    teacher = UserPublic(
        id="usr_t1",
        email="teacher@example.com",
        name="Prof. Turing",
        role="teacher",
        created_at=datetime.now(timezone.utc),
    )

    from core.deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: teacher

    try:
        audio_file = io.BytesIO(b"fake mp3 audio stream")
        response = client.post(
            "/api/lectures",
            data={"title": "Introduction to AI"},
            files={"file": ("intro.mp3", audio_file, "audio/mpeg")},
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


@patch("routes.lectures.enqueue_job", new_callable=AsyncMock)
@patch("routes.lectures.get_storage")
@patch("routes.lectures.LectureRepository")
@patch("routes.lectures.TimetableRepository")
@patch("routes.lectures.TeacherAssignmentRepository")
def test_upload_lecture_requires_assigned_class(
    mock_ta_repo, mock_tt_repo, mock_lec_repo, mock_get_storage, mock_enqueue, client
):
    """Teacher cannot upload lecture for an unassigned class (403), succeeds for assigned (202)."""
    teacher = UserPublic(
        id="usr_t1",
        email="teacher@example.com",
        name="Prof. Turing",
        role="teacher",
        created_at=datetime.now(timezone.utc),
    )

    from core.deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: teacher

    try:
        mock_storage = AsyncMock()
        mock_storage.save = AsyncMock(return_value="key")
        mock_get_storage.return_value = mock_storage

        mock_lec_inst = mock_lec_repo.return_value
        mock_lec_inst.new_id.return_value = "lec_100"
        mock_lec_inst.create = AsyncMock()

        mock_job = AsyncMock()
        mock_job.id = "job_100"
        mock_enqueue.return_value = mock_job

        # Case 1: Teacher is NOT assigned to class -> HTTP 403
        mock_ta_inst = mock_ta_repo.return_value
        mock_ta_inst.find_existing = AsyncMock(return_value=None)

        audio_file = io.BytesIO(b"fake audio data")
        res_unassigned = client.post(
            "/api/lectures",
            data={"title": "Unauthorized Lecture", "class_id": "cls_unassigned"},
            files={"file": ("unauth.mp3", audio_file, "audio/mpeg")},
        )
        assert res_unassigned.status_code == 403
        assert "Not assigned to teach this class" in res_unassigned.json()["detail"]

        # Case 2: Teacher IS assigned to class -> HTTP 202
        active_assignment = TeacherAssignmentDB(
            id="ta_1",
            class_id="cls_assigned",
            teacher_id="usr_t1",
            active=True,
            assigned_at=datetime.now(timezone.utc),
        )
        mock_ta_inst.find_existing = AsyncMock(return_value=active_assignment)

        # Case 2a: slot belongs to a different class (or is missing) -> HTTP 400
        from models.timetable import TimetableSlotDB
        slot = TimetableSlotDB(
            id="slot_1", class_id="cls_other", teacher_id="usr_t1", day_of_week=0,
            start_time="09:00", end_time="10:00", room="R1", created_at=datetime.now(timezone.utc),
        )
        mock_tt_repo.return_value.get_by_id = AsyncMock(return_value=slot)
        res_wrong_slot = client.post(
            "/api/lectures",
            data={"title": "Wrong Slot", "class_id": "cls_assigned", "timetable_slot_id": "slot_1"},
            files={"file": ("w.mp3", io.BytesIO(b"x"), "audio/mpeg")},
        )
        assert res_wrong_slot.status_code == 400
        mock_tt_repo.return_value.get_by_id = AsyncMock(return_value=None)
        res_missing_slot = client.post(
            "/api/lectures",
            data={"title": "Missing Slot", "class_id": "cls_assigned", "timetable_slot_id": "slot_1"},
            files={"file": ("m.mp3", io.BytesIO(b"x"), "audio/mpeg")},
        )
        assert res_missing_slot.status_code == 400

        # Case 2b: slot belongs to the class -> HTTP 202
        mock_tt_repo.return_value.get_by_id = AsyncMock(
            return_value=slot.model_copy(update={"class_id": "cls_assigned"})
        )
        audio_file2 = io.BytesIO(b"fake audio data 2")
        res_assigned = client.post(
            "/api/lectures",
            data={"title": "Authorized Lecture", "class_id": "cls_assigned", "timetable_slot_id": "slot_1"},
            files={"file": ("auth.mp3", audio_file2, "audio/mpeg")},
        )
        assert res_assigned.status_code == 202
        data = res_assigned.json()
        assert data["class_id"] == "cls_assigned"
        assert data["timetable_slot_id"] == "slot_1"
        assert data["teacher_id"] == "usr_t1"
    finally:
        app.dependency_overrides.clear()


@patch("routes.lectures.enqueue_job", new_callable=AsyncMock)
@patch("routes.lectures.get_storage")
@patch("routes.lectures.LectureRepository")
@patch("routes.lectures.TeacherAssignmentRepository")
def test_upload_lecture_admin_bypass(
    mock_ta_repo, mock_lec_repo, mock_get_storage, mock_enqueue, client
):
    """Admin can upload lecture to any class without explicit teacher assignment."""
    admin = UserPublic(
        id="usr_admin",
        email="admin@example.com",
        name="Administrator",
        role="admin",
        created_at=datetime.now(timezone.utc),
    )

    from core.deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        mock_storage = AsyncMock()
        mock_storage.save = AsyncMock(return_value="key")
        mock_get_storage.return_value = mock_storage

        mock_lec_inst = mock_lec_repo.return_value
        mock_lec_inst.new_id.return_value = "lec_admin"
        mock_lec_inst.create = AsyncMock()

        mock_job = AsyncMock()
        mock_job.id = "job_admin"
        mock_enqueue.return_value = mock_job

        mock_ta_inst = mock_ta_repo.return_value
        mock_ta_inst.find_existing = AsyncMock(return_value=None)

        audio_file = io.BytesIO(b"fake admin audio")
        res = client.post(
            "/api/lectures",
            data={"title": "Admin Upload", "class_id": "cls_any"},
            files={"file": ("admin.mp3", audio_file, "audio/mpeg")},
        )
        assert res.status_code == 202
        assert res.json()["class_id"] == "cls_any"
        # TeacherAssignmentRepository should not even be queried for admin
        mock_ta_inst.find_existing.assert_not_called()
    finally:
        app.dependency_overrides.clear()
