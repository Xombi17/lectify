"""Tests for class-scoped fail-closed 404 lecture access enforcement."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from models.academic import StudentEnrollmentDB, TeacherAssignmentDB
from models.lecture import LectureDB, StudyMaterials, QuizQuestion
from models.user import UserPublic
from server import app


@pytest.fixture
def client():
    return TestClient(app)


def _make_lecture(lecture_id="lec_101", class_id="class_comps_a", teacher_id="usr_teacher_1", published=True, status="ready"):
    return LectureDB(
        id=lecture_id,
        teacher_id=teacher_id,
        title="Operating Systems: Memory Management",
        subject="Operating Systems",
        semester="Sem 4",
        class_id=class_id,
        timetable_slot_id=None,
        audio_object_key=f"lectures/{lecture_id}/audio.mp3",
        audio_filename="audio.mp3",
        audio_mime="audio/mpeg",
        transcript="Virtual memory maps logical addresses to physical page frames.",
        materials=StudyMaterials(
            summary="Virtual memory overview",
            smart_notes=["Paging", "Page table"],
            key_concepts=["TLB", "Demand Paging"],
            quiz=[
                QuizQuestion(
                    question="What is a page fault?",
                    options=["Page not in RAM", "Disk full", "Segmentation fault"],
                    answer_index=0,
                )
            ],
            flashcards=[],
        ),
        status=status,
        published=published,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@patch("core.deps.StudentEnrollmentRepository")
@patch("core.deps.TeacherAssignmentRepository")
@patch("core.deps.LectureRepository")
def test_student_fail_closed_404_on_lecture_detail(
    mock_lec_repo, mock_ta_repo, mock_se_repo, client
):
    """Un-enrolled student receives HTTP 404; enrolled receives 200."""
    student = UserPublic(
        id="usr_alice",
        email="alice@college.edu",
        name="Alice",
        role="student",
        created_at=datetime.now(timezone.utc),
    )
    lecture = _make_lecture()

    mock_lec_repo.return_value.get_by_id = AsyncMock(return_value=lecture)

    from core.deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: student

    try:
        # 1. Un-enrolled student -> 404
        mock_se_repo.return_value.find_existing = AsyncMock(return_value=None)
        res_unauth = client.get(f"/api/lectures/{lecture.id}")
        assert res_unauth.status_code == 404
        assert "Lecture not found" in res_unauth.json()["detail"]

        # 2. Enrolled student -> 200
        mock_se_repo.return_value.find_existing = AsyncMock(
            return_value=StudentEnrollmentDB(
                id="enr_1", class_id=lecture.class_id, student_id=student.id, enrolled_at=datetime.now(timezone.utc)
            )
        )
        res_auth = client.get(f"/api/lectures/{lecture.id}")
        assert res_auth.status_code == 200
        assert res_auth.json()["id"] == lecture.id
    finally:
        app.dependency_overrides.clear()


@patch("core.deps.StudentEnrollmentRepository")
@patch("core.deps.TeacherAssignmentRepository")
@patch("core.deps.LectureRepository")
def test_teacher_access_assignment_and_admin_bypass(
    mock_lec_repo, mock_ta_repo, mock_se_repo, client
):
    """Assigned teacher and admin can view lecture; unassigned teacher receives 403."""
    lecture = _make_lecture(teacher_id="usr_prof_x", class_id="class_cse_b")
    mock_lec_repo.return_value.get_by_id = AsyncMock(return_value=lecture)

    teacher_unassigned = UserPublic(
        id="usr_prof_y",
        email="prof_y@college.edu",
        name="Prof. Y",
        role="teacher",
        created_at=datetime.now(timezone.utc),
    )

    from core.deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: teacher_unassigned

    try:
        # 1. Teacher not owner and not assigned -> 403 Forbidden
        mock_ta_repo.return_value.find_existing = AsyncMock(return_value=None)
        res_forbidden = client.get(f"/api/lectures/{lecture.id}")
        assert res_forbidden.status_code == 403

        # 2. Teacher assigned to that class -> 200 OK
        mock_ta_repo.return_value.find_existing = AsyncMock(
            return_value=TeacherAssignmentDB(
                id="ta_1", class_id=lecture.class_id, teacher_id="usr_prof_y", active=True, assigned_at=datetime.now(timezone.utc)
            )
        )
        res_assigned = client.get(f"/api/lectures/{lecture.id}")
        assert res_assigned.status_code == 200

        # 3. Admin user -> 200 OK without assignment
        admin = UserPublic(
            id="usr_admin",
            email="admin@college.edu",
            name="Admin",
            role="admin",
            created_at=datetime.now(timezone.utc),
        )
        app.dependency_overrides[get_current_user] = lambda: admin
        res_admin = client.get(f"/api/lectures/{lecture.id}")
        assert res_admin.status_code == 200
    finally:
        app.dependency_overrides.clear()


@patch("routes.lectures.get_storage")
@patch("core.deps.StudentEnrollmentRepository")
@patch("core.deps.TeacherAssignmentRepository")
@patch("core.deps.LectureRepository")
def test_student_audio_streaming_access(
    mock_lec_repo, mock_ta_repo, mock_se_repo, mock_get_storage, client
):
    """Audio streaming fails closed with 404 for un-enrolled students."""
    student = UserPublic(
        id="usr_bob",
        email="bob@college.edu",
        name="Bob",
        role="student",
        created_at=datetime.now(timezone.utc),
    )
    lecture = _make_lecture()
    mock_lec_repo.return_value.get_by_id = AsyncMock(return_value=lecture)

    from core.deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: student

    try:
        # Un-enrolled -> 404
        mock_se_repo.return_value.find_existing = AsyncMock(return_value=None)
        res_unauth = client.get(f"/api/lectures/{lecture.id}/audio")
        assert res_unauth.status_code == 404

        # Enrolled -> 200 stream
        mock_se_repo.return_value.find_existing = AsyncMock(
            return_value=StudentEnrollmentDB(
                id="enr_2", class_id=lecture.class_id, student_id=student.id, enrolled_at=datetime.now(timezone.utc)
            )
        )
        mock_storage = AsyncMock()
        mock_storage.stream = AsyncMock(return_value=(iter([b"audio_bytes"]), 11, "audio/mpeg"))
        mock_get_storage.return_value = mock_storage

        res_auth = client.get(f"/api/lectures/{lecture.id}/audio")
        assert res_auth.status_code == 200
    finally:
        app.dependency_overrides.clear()


@patch("core.deps.StudentEnrollmentRepository")
@patch("core.deps.TeacherAssignmentRepository")
@patch("core.deps.LectureRepository")
def test_student_pdf_export_fail_closed(
    mock_lec_repo, mock_ta_repo, mock_se_repo, client
):
    """GET /api/lectures/{id}/pdf fails closed with 404 for un-enrolled student."""
    student = UserPublic(
        id="usr_bob",
        email="bob@college.edu",
        name="Bob",
        role="student",
        created_at=datetime.now(timezone.utc),
    )
    lecture = _make_lecture()
    mock_lec_repo.return_value.get_by_id = AsyncMock(return_value=lecture)

    from core.deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: student

    try:
        # Un-enrolled -> 404
        mock_se_repo.return_value.find_existing = AsyncMock(return_value=None)
        res_unauth = client.get(f"/api/lectures/{lecture.id}/pdf")
        assert res_unauth.status_code == 404

        # Enrolled -> 200 PDF
        mock_se_repo.return_value.find_existing = AsyncMock(
            return_value=StudentEnrollmentDB(
                id="enr_2", class_id=lecture.class_id, student_id=student.id, enrolled_at=datetime.now(timezone.utc)
            )
        )
        res_auth = client.get(f"/api/lectures/{lecture.id}/pdf")
        assert res_auth.status_code == 200
        assert res_auth.headers["content-type"] == "application/pdf"
    finally:
        app.dependency_overrides.clear()


@patch("routes.chat.get_ai_service")
@patch("routes.chat.ChatRepository")
@patch("core.deps.StudentEnrollmentRepository")
@patch("core.deps.TeacherAssignmentRepository")
@patch("core.deps.LectureRepository")
def test_student_chat_fail_closed(
    mock_lec_repo, mock_ta_repo, mock_se_repo, mock_chat_repo, mock_ai_service, client
):
    """POST /api/lectures/{id}/chat fails closed with 404 for un-enrolled student."""
    student = UserPublic(
        id="usr_bob",
        email="bob@college.edu",
        name="Bob",
        role="student",
        created_at=datetime.now(timezone.utc),
    )
    lecture = _make_lecture()
    mock_lec_repo.return_value.get_by_id = AsyncMock(return_value=lecture)

    from core.deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: student

    try:
        # Un-enrolled -> 404
        mock_se_repo.return_value.find_existing = AsyncMock(return_value=None)
        res_unauth = client.post(
            f"/api/lectures/{lecture.id}/chat",
            json={"question": "What is demand paging?"},
        )
        assert res_unauth.status_code == 404

        # Enrolled -> 200
        mock_se_repo.return_value.find_existing = AsyncMock(
            return_value=StudentEnrollmentDB(
                id="enr_2", class_id=lecture.class_id, student_id=student.id, enrolled_at=datetime.now(timezone.utc)
            )
        )
        mock_chat = mock_chat_repo.return_value
        mock_chat.list_for = AsyncMock(return_value=[])
        mock_chat.new_id.return_value = "msg_1"
        mock_chat.add = AsyncMock()

        mock_ai = mock_ai_service.return_value
        mock_ai.chat = AsyncMock(return_value="Demand paging brings pages into memory on demand.")

        res_auth = client.post(
            f"/api/lectures/{lecture.id}/chat",
            json={"question": "What is demand paging?"},
        )
        assert res_auth.status_code == 200
        assert "Demand paging" in res_auth.json()["assistant_message"]["content"]
    finally:
        app.dependency_overrides.clear()


@patch("repositories.attempt_repository.AttemptRepository")
@patch("core.deps.StudentEnrollmentRepository")
@patch("core.deps.TeacherAssignmentRepository")
@patch("core.deps.LectureRepository")
def test_student_quiz_attempt_fail_closed(
    mock_lec_repo, mock_ta_repo, mock_se_repo, mock_attempt_repo, client
):
    """POST /api/lectures/{id}/quiz/attempt fails closed with 404 for un-enrolled student."""
    student = UserPublic(
        id="usr_bob",
        email="bob@college.edu",
        name="Bob",
        role="student",
        created_at=datetime.now(timezone.utc),
    )
    lecture = _make_lecture()
    mock_lec_repo.return_value.get_by_id = AsyncMock(return_value=lecture)

    from core.deps import get_current_user
    app.dependency_overrides[get_current_user] = lambda: student

    try:
        # Un-enrolled -> 404
        mock_se_repo.return_value.find_existing = AsyncMock(return_value=None)
        res_unauth = client.post(
            f"/api/lectures/{lecture.id}/quiz/attempt",
            json={"answers": [0]},
        )
        assert res_unauth.status_code == 404

        # Enrolled -> 200
        mock_se_repo.return_value.find_existing = AsyncMock(
            return_value=StudentEnrollmentDB(
                id="enr_2", class_id=lecture.class_id, student_id=student.id, enrolled_at=datetime.now(timezone.utc)
            )
        )
        mock_att = mock_attempt_repo.return_value
        mock_att.new_id.return_value = "att_1"
        mock_att.add = AsyncMock()

        res_auth = client.post(
            f"/api/lectures/{lecture.id}/quiz/attempt",
            json={"answers": [0]},
        )
        assert res_auth.status_code == 200
        assert res_auth.json()["score"] == 1
        assert res_auth.json()["total"] == 1
    finally:
        app.dependency_overrides.clear()
