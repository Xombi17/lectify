"""Comprehensive automated cross-class isolation test suite.

Verifies complete multi-tenant boundaries using the realistic 4-year engineering
college seed hierarchy (Apex Institute of Technology).
Ensures zero data leakage and strict fail-closed 404/403 access control across:
- Lecture detail retrieval
- Audio streaming
- Study materials (PDF export, bookmarks, flashcards)
- Quiz submission
- Chat & doubts (asking and history)
- Semantic & lexical search
- Timetable schedules
- Teacher lecture upload & publish restrictions
"""
import io
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from core.deps import get_current_user
from fixtures.college_seed import CollegeSeedData
from models.academic import (
    StudentEnrollmentDB,
    TeacherAssignmentDB,
)
from models.chat import ChatMessageDB
from models.lecture import LectureDB, StudyMaterials
from models.orm import (
    BranchORM,
    ClassORM,
    DivisionORM,
    InstitutionORM,
    SemesterORM,
    SubjectORM,
    YearORM,
)
from models.timetable import TimetableSlotDB
from models.user import UserPublic
from server import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def college() -> CollegeSeedData:
    """In-memory realistic college hierarchy matching seed_college_hierarchy structure."""
    now = datetime.now(timezone.utc)

    inst = InstitutionORM(
        id="inst_apex_100",
        name="Apex Institute of Technology",
        code="AIT",
        address="100 University Parkway, Tech City",
    )
    years = {
        1: YearORM(id="yr_1", institution_id=inst.id, number=1, name="First Year (FE)"),
        2: YearORM(id="yr_2", institution_id=inst.id, number=2, name="Second Year (SE)"),
        3: YearORM(id="yr_3", institution_id=inst.id, number=3, name="Third Year (TE)"),
        4: YearORM(id="yr_4", institution_id=inst.id, number=4, name="Final Year (BE)"),
    }
    branches = {
        "COMPS": BranchORM(id="br_comps", institution_id=inst.id, code="COMPS", name="Computer Engineering"),
        "CSE": BranchORM(id="br_cse", institution_id=inst.id, code="CSE", name="Computer Science & Engineering"),
    }
    semesters = {
        3: SemesterORM(id="sem_3", year_id=years[2].id, number=3, label="Semester 3"),
    }
    divisions = {
        "comps_a": DivisionORM(id="div_comps_a", semester_id=semesters[3].id, name="Comps A", capacity=60),
        "comps_b": DivisionORM(id="div_comps_b", semester_id=semesters[3].id, name="Comps B", capacity=60),
        "cse_a": DivisionORM(id="div_cse_a", semester_id=semesters[3].id, name="CSE A", capacity=60),
    }
    subjects = {
        "os": SubjectORM(id="sub_os", semester_id=semesters[3].id, code="CS301", name="Operating Systems", credits=4),
        "dsa": SubjectORM(id="sub_dsa", semester_id=semesters[3].id, code="CS302", name="Data Structures", credits=4),
    }
    classes = {
        "comps_a_os": ClassORM(id="cls_comps_a_os", division_id=divisions["comps_a"].id, subject_id=subjects["os"].id, name="Comps A · Operating Systems"),
        "comps_b_os": ClassORM(id="cls_comps_b_os", division_id=divisions["comps_b"].id, subject_id=subjects["os"].id, name="Comps B · Operating Systems"),
        "cse_a_os": ClassORM(id="cls_cse_a_os", division_id=divisions["cse_a"].id, subject_id=subjects["os"].id, name="CSE A · Operating Systems"),
    }
    # User profiles
    users = {
        "student_comps_a": UserPublic(id="usr_stu_comps_a", name="Alice CompsA", email="alice.compsa@apex.edu", role="student", created_at=now),
        "student_comps_b": UserPublic(id="usr_stu_comps_b", name="Bob CompsB", email="bob.compsb@apex.edu", role="student", created_at=now),
        "student_cse_a": UserPublic(id="usr_stu_cse_a", name="Charlie CseA", email="charlie.csea@apex.edu", role="student", created_at=now),
        "teacher_comps_a": UserPublic(id="usr_tea_comps_a", name="Prof Comps A", email="prof.compsa@apex.edu", role="teacher", created_at=now),
        "teacher_comps_b": UserPublic(id="usr_tea_comps_b", name="Prof Comps B", email="prof.compsb@apex.edu", role="teacher", created_at=now),
        "admin_user": UserPublic(id="usr_admin", name="Dean Academics", email="admin@apex.edu", role="admin", created_at=now),
    }

    # Lectures
    lectures = {
        "comps_a_lec": LectureDB(
            id="lec_comps_a_001",
            teacher_id=users["teacher_comps_a"].id,
            class_id=classes["comps_a_os"].id,
            timetable_slot_id="slot_comps_a_001",
            title="Comps A OS: Virtual Memory and Paging",
            subject="Operating Systems",
            semester="Semester 3",
            audio_object_key="audio/comps_a.mp3",
            audio_filename="comps_a.mp3",
            audio_mime="audio/mpeg",
            duration_seconds=3600.0,
            chunk_count=2,
            progress_step=3,
            progress_total=3,
            progress_label="ready",
            status="ready",
            published=True,
            transcript="Full audio transcript for Comps A. Exclusive details: paging page tables tlb comps_a_exclusive.",
            materials=StudyMaterials(
                summary="Demand paging, page tables, and TLB mechanisms explained for Comps Division A.",
                key_concepts=["paging", "page tables", "tlb", "comps_a_exclusive"],
                key_topics=["Operating Systems"],
                quiz=[
                    {
                        "question": "What is the key mechanism in Comps A?",
                        "options": ["paging", "random", "none", "other"],
                        "answer_index": 0,
                        "explanation": "paging is foundational.",
                    }
                ],
            ),
            embedding=[0.9, 0.1, 0.0],
            created_at=now,
            updated_at=now,
        ),
        "comps_b_lec": LectureDB(
            id="lec_comps_b_001",
            teacher_id=users["teacher_comps_b"].id,
            class_id=classes["comps_b_os"].id,
            timetable_slot_id="slot_comps_b_001",
            title="Comps B OS: Inverted Page Tables & Working Sets",
            subject="Operating Systems",
            semester="Semester 3",
            audio_object_key="audio/comps_b.mp3",
            audio_filename="comps_b.mp3",
            audio_mime="audio/mpeg",
            duration_seconds=3600.0,
            chunk_count=2,
            progress_step=3,
            progress_total=3,
            progress_label="ready",
            status="ready",
            published=True,
            transcript="Full audio transcript for Comps B. Exclusive details: inverted page table thrashing comps_b_isolated_secret.",
            materials=StudyMaterials(
                summary="Inverted page tables and thrashing avoidance strictly for Comps Division B.",
                key_concepts=["inverted page table", "thrashing", "comps_b_isolated_secret"],
                key_topics=["Operating Systems"],
                quiz=[
                    {
                        "question": "What is the key mechanism in Comps B?",
                        "options": ["inverted page table", "random", "none", "other"],
                        "answer_index": 0,
                        "explanation": "inverted page table is foundational.",
                    }
                ],
            ),
            embedding=[0.1, 0.9, 0.0],
            created_at=now,
            updated_at=now,
        ),
    }

    # Timetable slots
    slots = {
        "comps_a_slot": TimetableSlotDB(
            id="slot_comps_a_001",
            class_id=classes["comps_a_os"].id,
            teacher_id=users["teacher_comps_a"].id,
            day_of_week=0,
            start_time="09:00",
            end_time="10:30",
            room="Lab 201",
            created_at=now,
        ),
        "comps_b_slot": TimetableSlotDB(
            id="slot_comps_b_001",
            class_id=classes["comps_b_os"].id,
            teacher_id=users["teacher_comps_b"].id,
            day_of_week=1,
            start_time="11:00",
            end_time="12:30",
            room="Lab 202",
            created_at=now,
        ),
    }

    data = CollegeSeedData(
        institution=inst,
        years=years,
        branches=branches,
        semesters=semesters,
        divisions=divisions,
        subjects=subjects,
        classes=classes,
        users=users,
        lectures=lectures,
        slots=slots,
    )
    return data


def _set_user(college, user_key: str):
    user = college.users[user_key]
    app.dependency_overrides[get_current_user] = lambda: user


# ── 1. Direct Lecture Retrieval Isolation ─────────────────────────────


@patch("core.deps.StudentEnrollmentRepository")
@patch("core.deps.TeacherAssignmentRepository")
@patch("core.deps.LectureRepository")
def test_student_cannot_fetch_other_class_lecture_detail(
    mock_lec_repo, mock_ta_repo, mock_se_repo, college, client
):
    """Comps A student cannot fetch Comps B lecture detail (fail-closed HTTP 404)."""
    comps_a_lec = college.lectures["comps_a_lec"]
    comps_b_lec = college.lectures["comps_b_lec"]

    mock_lec_repo.return_value.get_by_id = AsyncMock(
        side_effect=lambda lid: comps_a_lec if lid == comps_a_lec.id else comps_b_lec if lid == comps_b_lec.id else None
    )

    # Student Comps A is enrolled ONLY in Comps A
    mock_se_repo.return_value.find_existing = AsyncMock(
        side_effect=lambda cid, uid: StudentEnrollmentDB(id="enr_1", class_id=cid, student_id=uid, enrolled_at=datetime.now(timezone.utc))
        if cid == comps_a_lec.class_id else None
    )

    _set_user(college, "student_comps_a")
    try:
        # Accessing Comps B lecture -> 404 Not Found (fail-closed)
        res_other = client.get(f"/api/lectures/{comps_b_lec.id}")
        assert res_other.status_code == 404
        assert res_other.json()["detail"] == "Lecture not found"

        # Accessing own Comps A lecture -> 200 OK
        res_own = client.get(f"/api/lectures/{comps_a_lec.id}")
        assert res_own.status_code == 200
        assert res_own.json()["id"] == comps_a_lec.id
    finally:
        app.dependency_overrides.clear()


# ── 2. Audio Streaming Isolation ──────────────────────────────────────


@patch("routes.lectures.get_storage")
@patch("core.deps.StudentEnrollmentRepository")
@patch("core.deps.TeacherAssignmentRepository")
@patch("core.deps.LectureRepository")
def test_student_cannot_stream_other_class_audio(
    mock_lec_repo, mock_ta_repo, mock_se_repo, mock_get_storage, college, client
):
    """Comps A student cannot stream audio for Comps B lecture (fail-closed HTTP 404)."""
    comps_a_lec = college.lectures["comps_a_lec"]
    comps_b_lec = college.lectures["comps_b_lec"]

    mock_lec_repo.return_value.get_by_id = AsyncMock(
        side_effect=lambda lid: comps_a_lec if lid == comps_a_lec.id else comps_b_lec if lid == comps_b_lec.id else None
    )
    mock_se_repo.return_value.find_existing = AsyncMock(
        side_effect=lambda cid, uid: StudentEnrollmentDB(id="enr_1", class_id=cid, student_id=uid, enrolled_at=datetime.now(timezone.utc))
        if cid == comps_a_lec.class_id else None
    )

    mock_storage = AsyncMock()
    mock_storage.stream = AsyncMock(return_value=(iter([b"audio_bytes"]), 11, "audio/mpeg"))
    mock_get_storage.return_value = mock_storage

    _set_user(college, "student_comps_a")
    try:
        # Stream Comps B -> 404
        res_b = client.get(f"/api/lectures/{comps_b_lec.id}/audio")
        assert res_b.status_code == 404

        # Stream Comps A -> 200
        res_a = client.get(f"/api/lectures/{comps_a_lec.id}/audio")
        assert res_a.status_code == 200
    finally:
        app.dependency_overrides.clear()


# ── 3. Study Materials Isolation (PDF, Bookmarks, Flashcards) ─────────


@patch("routes.study.FlashcardReviewRepository")
@patch("core.deps.StudentEnrollmentRepository")
@patch("core.deps.TeacherAssignmentRepository")
@patch("core.deps.LectureRepository")
def test_student_cannot_view_other_class_study_materials(
    mock_lec_repo, mock_ta_repo, mock_se_repo, mock_fc_repo, college, client
):
    """Comps A student cannot access PDF export, bookmarks, or flashcards of Comps B."""
    comps_a_lec = college.lectures["comps_a_lec"]
    comps_b_lec = college.lectures["comps_b_lec"]

    mock_lec_repo.return_value.get_by_id = AsyncMock(
        side_effect=lambda lid: comps_a_lec if lid == comps_a_lec.id else comps_b_lec if lid == comps_b_lec.id else None
    )
    mock_se_repo.return_value.find_existing = AsyncMock(
        side_effect=lambda cid, uid: StudentEnrollmentDB(id="enr_1", class_id=cid, student_id=uid, enrolled_at=datetime.now(timezone.utc))
        if cid == comps_a_lec.class_id else None
    )
    mock_fc_repo.return_value.list_all_for_user = AsyncMock(return_value=[])

    _set_user(college, "student_comps_a")
    try:
        # PDF -> 404 on Comps B, 200 on Comps A
        res_pdf_b = client.get(f"/api/lectures/{comps_b_lec.id}/pdf")
        assert res_pdf_b.status_code == 404

        res_pdf_a = client.get(f"/api/lectures/{comps_a_lec.id}/pdf")
        assert res_pdf_a.status_code == 200
        assert res_pdf_a.headers["content-type"] == "application/pdf"

        # Bookmarks list -> 404 on Comps B
        res_bm_b = client.get(f"/api/lectures/{comps_b_lec.id}/bookmarks")
        assert res_bm_b.status_code == 404

        # Create bookmark -> 404 on Comps B
        res_bm_create_b = client.post(
            "/api/bookmarks",
            json={"lecture_id": comps_b_lec.id, "kind": "concept", "text": "Rogue bookmark"},
        )
        assert res_bm_create_b.status_code == 404

        # Flashcards -> 404 on Comps B, 200 on Comps A
        res_fc_b = client.get(f"/api/lectures/{comps_b_lec.id}/flashcards/state")
        assert res_fc_b.status_code == 404

        res_fc_rev_b = client.post(
            "/api/flashcards/review",
            json={"lecture_id": comps_b_lec.id, "card_index": 0, "quality": 3},
        )
        assert res_fc_rev_b.status_code == 404

        res_fc_a = client.get(f"/api/lectures/{comps_a_lec.id}/flashcards/state")
        assert res_fc_a.status_code == 200
    finally:
        app.dependency_overrides.clear()


# ── 4. Quiz Attempt Isolation ─────────────────────────────────────────


@patch("repositories.attempt_repository.AttemptRepository")
@patch("core.deps.StudentEnrollmentRepository")
@patch("core.deps.TeacherAssignmentRepository")
@patch("core.deps.LectureRepository")
def test_student_cannot_attempt_other_class_quiz(
    mock_lec_repo, mock_ta_repo, mock_se_repo, mock_att_repo, college, client
):
    """Comps A student cannot submit quiz attempts for Comps B lecture (fail-closed HTTP 404)."""
    comps_a_lec = college.lectures["comps_a_lec"]
    comps_b_lec = college.lectures["comps_b_lec"]

    mock_lec_repo.return_value.get_by_id = AsyncMock(
        side_effect=lambda lid: comps_a_lec if lid == comps_a_lec.id else comps_b_lec if lid == comps_b_lec.id else None
    )
    mock_se_repo.return_value.find_existing = AsyncMock(
        side_effect=lambda cid, uid: StudentEnrollmentDB(id="enr_1", class_id=cid, student_id=uid, enrolled_at=datetime.now(timezone.utc))
        if cid == comps_a_lec.class_id else None
    )

    mock_att = mock_att_repo.return_value
    mock_att.new_id.return_value = "att_test_1"
    mock_att.add = AsyncMock()

    _set_user(college, "student_comps_a")
    try:
        # Comps B quiz -> 404
        res_b = client.post(
            f"/api/lectures/{comps_b_lec.id}/quiz/attempt",
            json={"answers": [0]},
        )
        assert res_b.status_code == 404

        # Comps A quiz -> 200
        res_a = client.post(
            f"/api/lectures/{comps_a_lec.id}/quiz/attempt",
            json={"answers": [0]},
        )
        assert res_a.status_code == 200
        assert res_a.json()["score"] == 1
    finally:
        app.dependency_overrides.clear()


# ── 5. Chat & Doubts Isolation ────────────────────────────────────────


@patch("routes.chat.get_ai_service")
@patch("routes.chat.ChatRepository")
@patch("core.deps.StudentEnrollmentRepository")
@patch("core.deps.TeacherAssignmentRepository")
@patch("core.deps.LectureRepository")
def test_student_cannot_query_or_post_other_class_chat(
    mock_lec_repo, mock_ta_repo, mock_se_repo, mock_chat_repo, mock_ai_service, college, client
):
    """Comps A student cannot ask questions or view chat history for Comps B lecture."""
    comps_a_lec = college.lectures["comps_a_lec"]
    comps_b_lec = college.lectures["comps_b_lec"]

    mock_lec_repo.return_value.get_by_id = AsyncMock(
        side_effect=lambda lid: comps_a_lec if lid == comps_a_lec.id else comps_b_lec if lid == comps_b_lec.id else None
    )
    mock_se_repo.return_value.find_existing = AsyncMock(
        side_effect=lambda cid, uid: StudentEnrollmentDB(id="enr_1", class_id=cid, student_id=uid, enrolled_at=datetime.now(timezone.utc))
        if cid == comps_a_lec.class_id else None
    )

    mock_ai = mock_ai_service.return_value
    mock_ai.chat = AsyncMock(return_value="Comps A paging explanation")

    mock_chat = mock_chat_repo.return_value
    mock_chat.list_for = AsyncMock(return_value=[])
    mock_chat.new_id.return_value = "msg_101"
    mock_chat.add = AsyncMock()

    _set_user(college, "student_comps_a")
    try:
        # Ask doubt on Comps B -> 404
        res_ask_b = client.post(
            f"/api/lectures/{comps_b_lec.id}/chat",
            json={"question": "What is inverted page table?"},
        )
        assert res_ask_b.status_code == 404

        # View chat on Comps B -> 404
        res_hist_b = client.get(f"/api/lectures/{comps_b_lec.id}/chat")
        assert res_hist_b.status_code == 404

        # Ask doubt on Comps A -> 200
        res_ask_a = client.post(
            f"/api/lectures/{comps_a_lec.id}/chat",
            json={"question": "Explain virtual memory."},
        )
        assert res_ask_a.status_code == 200
        assert "Comps A" in res_ask_a.json()["assistant_message"]["content"]
    finally:
        app.dependency_overrides.clear()


# ── 6. Search Partitioning Isolation ──────────────────────────────────


@patch("routes.search.get_ai_service")
@patch("core.deps.TeacherAssignmentRepository")
@patch("core.deps.StudentEnrollmentRepository")
@patch("routes.search.LectureRepository")
def test_student_search_filters_out_other_class_lectures(
    mock_lec_repo, mock_se_repo, mock_ta_repo, mock_ai_service, college, client
):
    """Search strictly isolates results to only classes the student is enrolled in."""
    comps_a_lec = college.lectures["comps_a_lec"]
    comps_b_lec = college.lectures["comps_b_lec"]

    docs_store = [
        {
            "id": comps_a_lec.id,
            "title": comps_a_lec.title,
            "subject": comps_a_lec.subject,
            "semester": comps_a_lec.semester,
            "class_id": comps_a_lec.class_id,
            "embedding": comps_a_lec.embedding,
            "materials": {
                "summary": comps_a_lec.materials.summary,
                "key_concepts": comps_a_lec.materials.key_concepts,
            },
        },
        {
            "id": comps_b_lec.id,
            "title": comps_b_lec.title,
            "subject": comps_b_lec.subject,
            "semester": comps_b_lec.semester,
            "class_id": comps_b_lec.class_id,
            "embedding": comps_b_lec.embedding,
            "materials": {
                "summary": comps_b_lec.materials.summary,
                "key_concepts": comps_b_lec.materials.key_concepts,
            },
        },
    ]

    async def mock_list_embeddings(class_ids=None):
        if class_ids is None:
            return docs_store
        if len(class_ids) == 0:
            return []
        return [d for d in docs_store if d["class_id"] in class_ids]

    mock_lec_repo.return_value.list_published_embeddings = AsyncMock(side_effect=mock_list_embeddings)
    mock_ai_service.return_value.embed = AsyncMock(return_value=[0.0, 0.0, 0.0])

    # Student enrollments
    mock_se_repo.return_value.list_for_student = AsyncMock(
        side_effect=lambda uid: [StudentEnrollmentDB(id="e1", class_id=comps_a_lec.class_id, student_id=uid, enrolled_at=datetime.now(timezone.utc))]
        if uid == college.users["student_comps_a"].id
        else [StudentEnrollmentDB(id="e2", class_id=comps_b_lec.class_id, student_id=uid, enrolled_at=datetime.now(timezone.utc))]
        if uid == college.users["student_comps_b"].id
        else []
    )

    try:
        # 1. Comps A searches for Comps B exclusive keyword ("comps_b_isolated_secret") -> 0 hits
        _set_user(college, "student_comps_a")
        res_a_leak = client.get("/api/search?q=comps_b_isolated_secret")
        assert res_a_leak.status_code == 200
        assert res_a_leak.json() == []

        # 2. Comps A searches for Comps A keyword ("comps_a_exclusive") -> 1 hit
        res_a_own = client.get("/api/search?q=comps_a_exclusive")
        assert res_a_own.status_code == 200
        hits_a = res_a_own.json()
        assert len(hits_a) == 1
        assert hits_a[0]["lecture_id"] == comps_a_lec.id

        # 3. Comps B searches for Comps A keyword -> 0 hits
        _set_user(college, "student_comps_b")
        res_b_leak = client.get("/api/search?q=comps_a_exclusive")
        assert res_b_leak.status_code == 200
        assert res_b_leak.json() == []

        # 4. Comps B searches for Comps B keyword -> 1 hit
        res_b_own = client.get("/api/search?q=comps_b_isolated_secret")
        assert res_b_own.status_code == 200
        hits_b = res_b_own.json()
        assert len(hits_b) == 1
        assert hits_b[0]["lecture_id"] == comps_b_lec.id

        # 5. Admin searches -> sees Comps B hit
        _set_user(college, "admin_user")
        res_admin = client.get("/api/search?q=comps-b-secret")
        assert res_admin.status_code == 200
        assert any(h["lecture_id"] == comps_b_lec.id for h in res_admin.json())
    finally:
        app.dependency_overrides.clear()


# ── 7. Timetable Schedule Isolation ───────────────────────────────────


@patch("routes.timetable.TimetableRepository")
@patch("routes.timetable.TeacherAssignmentRepository")
@patch("routes.timetable.StudentEnrollmentRepository")
def test_student_cannot_view_other_class_timetable(
    mock_se_repo, mock_ta_repo, mock_tt_repo, college, client
):
    """Student cannot view timetable slots for classes they are not enrolled in."""
    comps_a_class = college.classes["comps_a_os"]
    comps_b_class = college.classes["comps_b_os"]
    slot_a = college.slots["comps_a_slot"]
    slot_b = college.slots["comps_b_slot"]

    mock_tt = mock_tt_repo.return_value
    mock_tt.list_by_class = AsyncMock(
        side_effect=lambda cid: [slot_a] if cid == comps_a_class.id else [slot_b] if cid == comps_b_class.id else []
    )
    mock_tt.list_by_classes = AsyncMock(
        side_effect=lambda cids: [s for s in [slot_a, slot_b] if s.class_id in cids]
    )

    mock_se_repo.return_value.find_existing = AsyncMock(
        side_effect=lambda cid, uid: StudentEnrollmentDB(id="e1", class_id=cid, student_id=uid, enrolled_at=datetime.now(timezone.utc))
        if cid == comps_a_class.id else None
    )
    mock_se_repo.return_value.list_for_student = AsyncMock(
        return_value=[StudentEnrollmentDB(id="e1", class_id=comps_a_class.id, student_id="usr_stu_comps_a", enrolled_at=datetime.now(timezone.utc))]
    )

    _set_user(college, "student_comps_a")
    try:
        # Comps B class schedule -> 404 (fail-closed)
        res_b = client.get(f"/api/timetable/class/{comps_b_class.id}")
        assert res_b.status_code == 404

        # Comps A class schedule -> 200 with slot_a
        res_a = client.get(f"/api/timetable/class/{comps_a_class.id}")
        assert res_a.status_code == 200
        assert len(res_a.json()) == 1
        assert res_a.json()[0]["class_id"] == comps_a_class.id

        # My schedule -> only Comps A
        res_my = client.get("/api/timetable/my-schedule")
        assert res_my.status_code == 200
        slots = res_my.json()
        assert len(slots) == 1
        assert slots[0]["class_id"] == comps_a_class.id
    finally:
        app.dependency_overrides.clear()


# ── 8. Teacher Upload & Publishing Authorization ──────────────────────


@patch("routes.lectures.enqueue_job")
@patch("routes.lectures.get_storage")
@patch("routes.lectures.TeacherAssignmentRepository")
@patch("routes.lectures.LectureRepository")
def test_teacher_cannot_upload_lecture_to_unassigned_class(
    mock_lec_repo, mock_ta_repo, mock_get_storage, mock_enqueue, college, client
):
    """Teacher cannot upload a lecture to a class they are not assigned to (HTTP 403)."""
    comps_a_class = college.classes["comps_a_os"]
    comps_b_class = college.classes["comps_b_os"]
    teacher_a = college.users["teacher_comps_a"]

    mock_ta = mock_ta_repo.return_value
    mock_ta.find_existing = AsyncMock(
        side_effect=lambda class_id, teacher_id, active_only=True: TeacherAssignmentDB(
            id="ta_1", class_id=class_id, teacher_id=teacher_id, active=True, assigned_at=datetime.now(timezone.utc)
        )
        if class_id == comps_a_class.id and teacher_id == teacher_a.id else None
    )

    mock_lec_repo.return_value.new_id.return_value = "lec_new_1"
    mock_lec_repo.return_value.create = AsyncMock(
        side_effect=lambda lec: lec
    )

    mock_storage = AsyncMock()
    mock_storage.save = AsyncMock(return_value="audio/test.mp3")
    mock_get_storage.return_value = mock_storage
    mock_enqueue.return_value = MagicMock(id="job_123")

    _set_user(college, "teacher_comps_a")
    try:
        # Upload to Comps B -> 403 Forbidden
        fake_file_b = ("lecture_b.mp3", io.BytesIO(b"fake audio data b"), "audio/mpeg")
        res_unauth = client.post(
            "/api/lectures",
            data={"title": "Rogue Upload", "class_id": comps_b_class.id},
            files={"file": fake_file_b},
        )
        assert res_unauth.status_code == 403
        assert "Not assigned to teach this class" in res_unauth.json()["detail"]

        # Upload to assigned Comps A -> 202 Accepted
        fake_file_a = ("lecture_a.mp3", io.BytesIO(b"fake audio data a"), "audio/mpeg")
        res_auth = client.post(
            "/api/lectures",
            data={"title": "Legit Comps A Upload", "class_id": comps_a_class.id},
            files={"file": fake_file_a},
        )
        assert res_auth.status_code == 202
        assert res_auth.json()["title"] == "Legit Comps A Upload"
    finally:
        app.dependency_overrides.clear()


@patch("routes.lectures.LectureRepository")
def test_teacher_cannot_publish_lecture_for_unassigned_class(
    mock_lec_repo, college, client
):
    """Teacher cannot publish or unpublish a lecture from another teacher's unassigned class."""
    comps_b_lec = college.lectures["comps_b_lec"]
    mock_lec_repo.return_value.get_by_id = AsyncMock(return_value=comps_b_lec)

    _set_user(college, "teacher_comps_a")
    try:
        # Teacher Comps A attempting to publish Comps B lecture -> 404 (or 403)
        res = client.post(f"/api/lectures/{comps_b_lec.id}/publish")
        assert res.status_code in (403, 404)
    finally:
        app.dependency_overrides.clear()
