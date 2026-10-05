"""Tests for Timetable repository, overlap detection, and API endpoints."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from models.academic import StudentEnrollmentDB, TeacherAssignmentDB
from models.timetable import TimetableSlotDB
from models.user import UserPublic
from server import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.asyncio
async def test_timetable_repository_crud_and_overlap(monkeypatch):
    """Test repository CRUD operations and interval overlap logic."""
    monkeypatch.setenv("DATABASE_BACKEND", "postgres")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    from core.sql_db import init_models
    from repositories._sql.timetable_repository import TimetableRepository

    await init_models()
    repo = TimetableRepository()

    class_1 = f"cls_{uuid.uuid4().hex[:8]}"
    class_2 = f"cls_{uuid.uuid4().hex[:8]}"
    teacher_1 = f"tea_{uuid.uuid4().hex[:8]}"
    teacher_2 = f"tea_{uuid.uuid4().hex[:8]}"

    # 1. Create a slot: Monday (0), 09:00 - 10:30, Class 1, Teacher 1
    slot_1 = TimetableSlotDB(
        id=repo.new_id(),
        class_id=class_1,
        teacher_id=teacher_1,
        day_of_week=0,
        start_time="09:00",
        end_time="10:30",
        room="Room 101",
    )
    created_1 = await repo.create(slot_1)
    assert created_1.id == slot_1.id

    fetched = await repo.get_by_id(slot_1.id)
    assert fetched is not None
    assert fetched.room == "Room 101"

    # 2. Test overlap detection
    # a) Same class, overlapping time (10:00 - 11:00) on Monday -> CONFLICT
    conflict_class = await repo.find_overlap(
        day_of_week=0,
        start_time="10:00",
        end_time="11:00",
        class_id=class_1,
        teacher_id=teacher_2,
    )
    assert conflict_class is not None
    assert conflict_class.id == slot_1.id

    # b) Same teacher, different class, overlapping time (09:30 - 10:30) on Monday -> CONFLICT
    conflict_teacher = await repo.find_overlap(
        day_of_week=0,
        start_time="09:30",
        end_time="10:30",
        class_id=class_2,
        teacher_id=teacher_1,
    )
    assert conflict_teacher is not None
    assert conflict_teacher.id == slot_1.id

    # c) Adjacent slot: Monday 10:30 - 12:00 for same class & teacher -> NO CONFLICT
    adjacent = await repo.find_overlap(
        day_of_week=0,
        start_time="10:30",
        end_time="12:00",
        class_id=class_1,
        teacher_id=teacher_1,
    )
    assert adjacent is None

    # d) Different day: Tuesday (1) 09:00 - 10:30 -> NO CONFLICT
    diff_day = await repo.find_overlap(
        day_of_week=1,
        start_time="09:00",
        end_time="10:30",
        class_id=class_1,
        teacher_id=teacher_1,
    )
    assert diff_day is None

    # e) Self-exclusion: updating slot_1 itself with same time -> NO CONFLICT when exclude_slot_id=slot_1.id
    self_check = await repo.find_overlap(
        day_of_week=0,
        start_time="09:00",
        end_time="10:30",
        class_id=class_1,
        teacher_id=teacher_1,
        exclude_slot_id=slot_1.id,
    )
    assert self_check is None

    # 3. Create second slot on Wednesday
    slot_2 = TimetableSlotDB(
        id=repo.new_id(),
        class_id=class_2,
        teacher_id=teacher_1,
        day_of_week=2,
        start_time="14:00",
        end_time="15:30",
        room="Room 202",
    )
    await repo.create(slot_2)

    # 4. List queries
    by_class = await repo.list_by_class(class_1)
    assert len(by_class) == 1
    assert by_class[0].id == slot_1.id

    by_classes = await repo.list_by_classes([class_1, class_2])
    assert len(by_classes) == 2

    by_teacher = await repo.list_by_teacher(teacher_1)
    assert len(by_teacher) == 2

    # 5. Update slot
    updated = await repo.update(slot_1.id, {"room": "Room 101-A"})
    assert updated is not None
    assert updated.room == "Room 101-A"

    # 6. Delete slot
    deleted = await repo.delete(slot_1.id)
    assert deleted is True
    assert await repo.get_by_id(slot_1.id) is None


@patch("routes.timetable.TeacherAssignmentRepository")
@patch("routes.timetable.TimetableRepository")
def test_create_timetable_slot_overlap_rejection(
    mock_tt_repo, mock_ta_repo, client
):
    """POST /api/timetable/slots returns 409 on overlap and 201 on valid slot."""
    teacher = UserPublic(
        id="usr_t1",
        email="prof@college.edu",
        name="Prof. Gauss",
        role="teacher",
        created_at=datetime.now(timezone.utc),
    )

    from core.deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: teacher

    try:
        mock_ta_inst = mock_ta_repo.return_value
        # Teacher is assigned to class_101
        mock_ta_inst.find_existing = AsyncMock(
            return_value=TeacherAssignmentDB(
                id="ta_1", class_id="class_101", teacher_id="usr_t1", active=True, assigned_at=datetime.now(timezone.utc)
            )
        )

        mock_tt_inst = mock_tt_repo.return_value
        mock_tt_inst.new_id.return_value = "slot_new"

        # Case 1: Overlap detected -> HTTP 409
        mock_tt_inst.find_overlap = AsyncMock(
            return_value=TimetableSlotDB(
                id="slot_existing",
                class_id="class_101",
                teacher_id="usr_t1",
                day_of_week=1,
                start_time="10:00",
                end_time="11:30",
                created_at=datetime.now(timezone.utc),
            )
        )

        res_conflict = client.post(
            "/api/timetable/slots",
            json={
                "class_id": "class_101",
                "teacher_id": "usr_t1",
                "day_of_week": 1,
                "start_time": "11:00",
                "end_time": "12:00",
                "room": "Hall A",
            },
        )
        assert res_conflict.status_code == 409
        assert "Schedule conflict" in res_conflict.json()["detail"]

        # Case 2: Invalid times (start >= end) -> HTTP 400
        res_bad_time = client.post(
            "/api/timetable/slots",
            json={
                "class_id": "class_101",
                "teacher_id": "usr_t1",
                "day_of_week": 1,
                "start_time": "12:00",
                "end_time": "11:00",
            },
        )
        assert res_bad_time.status_code == 400

        # Case 3: No overlap -> HTTP 201 Created
        mock_tt_inst.find_overlap = AsyncMock(return_value=None)
        mock_tt_inst.create = AsyncMock(
            side_effect=lambda slot: slot
        )

        res_ok = client.post(
            "/api/timetable/slots",
            json={
                "class_id": "class_101",
                "teacher_id": "usr_t1",
                "day_of_week": 1,
                "start_time": "12:00",
                "end_time": "13:00",
                "room": "Hall B",
            },
        )
        assert res_ok.status_code == 201
        data = res_ok.json()
        assert data["id"] == "slot_new"
        assert data["class_id"] == "class_101"
        assert data["start_time"] == "12:00"
    finally:
        app.dependency_overrides.clear()


@patch("routes.timetable.StudentEnrollmentRepository")
@patch("routes.timetable.TimetableRepository")
def test_student_class_timetable_fail_closed_access(
    mock_tt_repo, mock_se_repo, client
):
    """Students cannot access timetable for an un-enrolled class (404), succeeds for enrolled."""
    student = UserPublic(
        id="usr_s1",
        email="student@college.edu",
        name="Alice Student",
        role="student",
        created_at=datetime.now(timezone.utc),
    )

    from core.deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: student

    try:
        mock_se_inst = mock_se_repo.return_value
        mock_tt_inst = mock_tt_repo.return_value

        # Un-enrolled class -> HTTP 404 (Fail-closed)
        mock_se_inst.find_existing = AsyncMock(return_value=None)
        res_unauth = client.get("/api/timetable/class/class_secret")
        assert res_unauth.status_code == 404
        assert "not enrolled" in res_unauth.json()["detail"].lower()

        # Enrolled class -> HTTP 200
        mock_se_inst.find_existing = AsyncMock(
            return_value=StudentEnrollmentDB(
                id="enr_1", class_id="class_enrolled", student_id="usr_s1", enrolled_at=datetime.now(timezone.utc)
            )
        )
        mock_tt_inst.list_by_class = AsyncMock(
            return_value=[
                TimetableSlotDB(
                    id="slot_1",
                    class_id="class_enrolled",
                    teacher_id="usr_t1",
                    day_of_week=0,
                    start_time="09:00",
                    end_time="10:00",
                    created_at=datetime.now(timezone.utc),
                )
            ]
        )
        res_auth = client.get("/api/timetable/class/class_enrolled")
        assert res_auth.status_code == 200
        assert len(res_auth.json()) == 1
        assert res_auth.json()[0]["id"] == "slot_1"
    finally:
        app.dependency_overrides.clear()


@patch("routes.timetable.StudentEnrollmentRepository")
@patch("routes.timetable.TimetableRepository")
def test_my_schedule_for_student_and_teacher(
    mock_tt_repo, mock_se_repo, client
):
    """GET /api/timetable/my-schedule resolves enrolled classes for student and assigned slots for teacher."""
    student = UserPublic(
        id="usr_s1",
        email="student@college.edu",
        name="Alice Student",
        role="student",
        created_at=datetime.now(timezone.utc),
    )

    from core.deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: student

    try:
        mock_se_inst = mock_se_repo.return_value
        mock_se_inst.list_for_student = AsyncMock(
            return_value=[
                StudentEnrollmentDB(id="e1", class_id="class_a", student_id="usr_s1", enrolled_at=datetime.now(timezone.utc)),
                StudentEnrollmentDB(id="e2", class_id="class_b", student_id="usr_s1", enrolled_at=datetime.now(timezone.utc)),
            ]
        )
        mock_tt_inst = mock_tt_repo.return_value
        mock_tt_inst.list_by_classes = AsyncMock(
            return_value=[
                TimetableSlotDB(id="s1", class_id="class_a", teacher_id="t1", day_of_week=0, start_time="09:00", end_time="10:00", created_at=datetime.now(timezone.utc))
            ]
        )

        res_student = client.get("/api/timetable/my-schedule")
        assert res_student.status_code == 200
        mock_tt_inst.list_by_classes.assert_called_once_with(["class_a", "class_b"])
        assert len(res_student.json()) == 1

        # Now test teacher
        teacher = UserPublic(
            id="usr_t1",
            email="prof@college.edu",
            name="Prof. Gauss",
            role="teacher",
            created_at=datetime.now(timezone.utc),
        )
        app.dependency_overrides[get_current_user] = lambda: teacher

        mock_tt_inst.list_by_teacher = AsyncMock(
            return_value=[
                TimetableSlotDB(id="s2", class_id="class_a", teacher_id="usr_t1", day_of_week=1, start_time="11:00", end_time="12:00", created_at=datetime.now(timezone.utc))
            ]
        )

        res_teacher = client.get("/api/timetable/my-schedule")
        assert res_teacher.status_code == 200
        mock_tt_inst.list_by_teacher.assert_called_once_with("usr_t1")
        assert len(res_teacher.json()) == 1
    finally:
        app.dependency_overrides.clear()
