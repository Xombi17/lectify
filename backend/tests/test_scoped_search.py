"""Tests for class-scoped published lecture listing and zero-leakage search."""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from core.deps import get_current_user
from models.academic import StudentEnrollmentDB, TeacherAssignmentDB
from models.lecture import LectureDB, StudyMaterials
from models.user import UserPublic
from server import app


@pytest.fixture
def client():
    return TestClient(app)


def _make_lecture(
    lecture_id: str,
    class_id: str,
    title: str,
    summary: str,
    teacher_id: str = "tea_1",
    published: bool = True,
) -> LectureDB:
    return LectureDB(
        id=lecture_id,
        teacher_id=teacher_id,
        title=title,
        subject="CS",
        semester="Sem 4",
        audio_object_key=f"audio/{lecture_id}.mp3",
        audio_filename=f"{lecture_id}.mp3",
        audio_mime="audio/mpeg",
        duration_seconds=3600,
        chunk_count=1,
        progress_step=3,
        progress_total=3,
        progress_label="ready",
        status="ready",
        transcript=f"Transcript for {title}",
        materials=StudyMaterials(
            summary=summary,
            key_concepts=[title],
            key_topics=[title],
            quiz=[],
        ),
        embedding=[0.1, 0.2, 0.3],
        translations={},
        error_message=None,
        published=published,
        class_id=class_id,
        timetable_slot_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_lecture_repo_list_published_scoping(monkeypatch):
    """Test SQL LectureRepository list_published and list_published_embeddings with class_ids filter."""
    monkeypatch.setenv("DATABASE_BACKEND", "postgres")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    from core.sql_db import init_models
    from repositories._sql.lecture_repository import LectureRepository

    await init_models()
    repo = LectureRepository()

    cls_a = f"cls_a_{uuid.uuid4().hex[:6]}"
    cls_b = f"cls_b_{uuid.uuid4().hex[:6]}"
    cls_c = f"cls_c_{uuid.uuid4().hex[:6]}"

    lec_a = _make_lecture(f"lec_a_{uuid.uuid4().hex[:6]}", cls_a, "Operating Systems", "Virtual memory and paging")
    lec_b = _make_lecture(f"lec_b_{uuid.uuid4().hex[:6]}", cls_b, "Quantum Mechanics", "Superposition and entanglement")
    lec_c_draft = _make_lecture(f"lec_c_{uuid.uuid4().hex[:6]}", cls_c, "Compiler Design", "Lexing and parsing", published=False)

    await repo.create(lec_a)
    await repo.create(lec_b)
    await repo.create(lec_c_draft)

    # 1. Filter by class A -> only lec_a
    res_a = await repo.list_published(class_ids=[cls_a])
    assert len(res_a) == 1
    assert res_a[0].id == lec_a.id

    # 2. Filter by class B -> only lec_b
    res_b = await repo.list_published(class_ids=[cls_b])
    assert len(res_b) == 1
    assert res_b[0].id == lec_b.id

    # 3. Empty class_ids list -> empty list immediately
    res_empty = await repo.list_published(class_ids=[])
    assert res_empty == []

    # 4. None class_ids (admin) -> all published (lec_a and lec_b, excluding unpublished lec_c)
    res_all = await repo.list_published(class_ids=None)
    published_ids = {r.id for r in res_all}
    assert published_ids == {lec_a.id, lec_b.id}

    # 5. Embeddings filtering
    emb_a = await repo.list_published_embeddings(class_ids=[cls_a])
    assert len(emb_a) == 1
    assert emb_a[0]["id"] == lec_a.id
    assert emb_a[0]["class_id"] == cls_a

    emb_empty = await repo.list_published_embeddings(class_ids=[])
    assert emb_empty == []

    emb_all = await repo.list_published_embeddings(class_ids=None)
    assert {e["id"] for e in emb_all} == {lec_a.id, lec_b.id}


@patch("core.deps.TeacherAssignmentRepository")
@patch("core.deps.StudentEnrollmentRepository")
@patch("routes.lectures.LectureRepository")
def test_get_published_lectures_role_scoping(
    mock_lec_repo, mock_se_repo, mock_ta_repo, client
):
    """GET /api/lectures/published filters by enrolled/assigned class_ids per user role."""
    cls_a = "cls_operating_systems"
    cls_b = "cls_quantum_mechanics"

    from models.lecture import LectureSummary
    lec_summary_a = LectureSummary(
        id="lec_1",
        teacher_id="tea_1",
        title="Paging",
        subject="OS",
        semester="Sem 4",
        status="ready",
        class_id=cls_a,
        created_at=datetime.now(timezone.utc),
        published=True,
    )
    lec_summary_b = LectureSummary(
        id="lec_2",
        teacher_id="tea_2",
        title="Entanglement",
        subject="Physics",
        semester="Sem 6",
        status="ready",
        class_id=cls_b,
        created_at=datetime.now(timezone.utc),
        published=True,
    )

    async def mock_list_published(class_ids=None, limit=None, offset=0):
        if class_ids is None:
            return [lec_summary_a, lec_summary_b]
        res = []
        if cls_a in class_ids:
            res.append(lec_summary_a)
        if cls_b in class_ids:
            res.append(lec_summary_b)
        return res

    mock_lec_repo.return_value.list_published = AsyncMock(side_effect=mock_list_published)

    # 1. Student enrolled in Class A
    student = UserPublic(
        id="usr_alice",
        email="alice@college.edu",
        name="Alice",
        role="student",
        created_at=datetime.now(timezone.utc),
    )
    app.dependency_overrides[get_current_user] = lambda: student
    mock_se_repo.return_value.list_for_student = AsyncMock(
        return_value=[
            StudentEnrollmentDB(id="enr_1", class_id=cls_a, student_id=student.id, enrolled_at=datetime.now(timezone.utc))
        ]
    )

    try:
        res = client.get("/api/lectures/published")
        assert res.status_code == 200
        items = res.json()
        assert len(items) == 1
        assert items[0]["id"] == "lec_1"
        assert items[0]["title"] == "Paging"

        # 2. Student enrolled in 0 classes gets []
        mock_se_repo.return_value.list_for_student = AsyncMock(return_value=[])
        res_empty = client.get("/api/lectures/published")
        assert res_empty.status_code == 200
        assert res_empty.json() == []

        # 3. Teacher assigned to Class B
        teacher = UserPublic(
            id="usr_prof",
            email="prof@college.edu",
            name="Prof",
            role="teacher",
            created_at=datetime.now(timezone.utc),
        )
        app.dependency_overrides[get_current_user] = lambda: teacher
        mock_ta_repo.return_value.list_for_teacher = AsyncMock(
            return_value=[
                TeacherAssignmentDB(id="ta_1", class_id=cls_b, teacher_id=teacher.id, active=True, assigned_at=datetime.now(timezone.utc))
            ]
        )
        res_teacher = client.get("/api/lectures/published")
        assert res_teacher.status_code == 200
        items_teacher = res_teacher.json()
        assert len(items_teacher) == 1
        assert items_teacher[0]["id"] == "lec_2"
        assert items_teacher[0]["title"] == "Entanglement"

        # 4. Admin receives all published lectures across classes
        admin = UserPublic(
            id="usr_admin",
            email="admin@college.edu",
            name="Admin",
            role="admin",
            created_at=datetime.now(timezone.utc),
        )
        app.dependency_overrides[get_current_user] = lambda: admin
        res_admin = client.get("/api/lectures/published")
        assert res_admin.status_code == 200
        items_admin = res_admin.json()
        assert len(items_admin) == 2
    finally:
        app.dependency_overrides.clear()


@patch("routes.search.get_ai_service")
@patch("core.deps.TeacherAssignmentRepository")
@patch("core.deps.StudentEnrollmentRepository")
@patch("routes.search.LectureRepository")
def test_search_zero_leakage_across_classes(
    mock_lec_repo, mock_se_repo, mock_ta_repo, mock_ai_service, client
):
    """GET /api/search guarantees zero cross-class leakage for students and teachers."""
    cls_a = "cls_os"
    cls_b = "cls_quantum"

    docs_store = [
        {
            "id": "lec_os",
            "title": "Operating Systems: Demand Paging and Memory Management",
            "subject": "CS",
            "semester": "Sem 4",
            "class_id": cls_a,
            "embedding": [0.9, 0.1],
            "materials": {
                "summary": "Covers page replacement algorithms and demand paging.",
                "key_concepts": ["paging", "frames", "virtual memory"],
            },
        },
        {
            "id": "lec_quantum",
            "title": "Quantum Mechanics: Superposition and Entangled Qubits",
            "subject": "Physics",
            "semester": "Sem 6",
            "class_id": cls_b,
            "embedding": [0.1, 0.9],
            "materials": {
                "summary": "Covers qubits, entanglement, and quantum gates.",
                "key_concepts": ["superposition", "entanglement", "qubits"],
            },
        },
    ]

    async def mock_list_published_embeddings(class_ids=None):
        if class_ids is None:
            return docs_store
        if len(class_ids) == 0:
            return []
        return [d for d in docs_store if d["class_id"] in class_ids]

    mock_lec_repo.return_value.list_published_embeddings = AsyncMock(side_effect=mock_list_published_embeddings)
    mock_ai_service.return_value.embed = AsyncMock(return_value=[0.0, 0.0])

    student_a = UserPublic(
        id="usr_alice",
        email="alice@college.edu",
        name="Alice",
        role="student",
        created_at=datetime.now(timezone.utc),
    )
    app.dependency_overrides[get_current_user] = lambda: student_a
    mock_se_repo.return_value.list_for_student = AsyncMock(
        return_value=[
            StudentEnrollmentDB(id="enr_1", class_id=cls_a, student_id=student_a.id, enrolled_at=datetime.now(timezone.utc))
        ]
    )

    try:
        # Alice is in Class A (OS). She searches for "quantum" (only in Class B).
        # MUST return 0 results (zero leakage).
        res_quantum = client.get("/api/search?q=quantum")
        assert res_quantum.status_code == 200
        assert res_quantum.json() == []

        # Alice searches for "paging" (in Class A).
        res_paging = client.get("/api/search?q=paging")
        assert res_paging.status_code == 200
        hits = res_paging.json()
        assert len(hits) == 1
        assert hits[0]["lecture_id"] == "lec_os"

        # Student with zero enrollments gets []
        mock_se_repo.return_value.list_for_student = AsyncMock(return_value=[])
        res_zero = client.get("/api/search?q=paging")
        assert res_zero.status_code == 200
        assert res_zero.json() == []

        # Admin gets results across both classes
        admin = UserPublic(
            id="usr_admin",
            email="admin@college.edu",
            name="Admin",
            role="admin",
            created_at=datetime.now(timezone.utc),
        )
        app.dependency_overrides[get_current_user] = lambda: admin

        admin_quantum = client.get("/api/search?q=quantum")
        assert admin_quantum.status_code == 200
        assert len(admin_quantum.json()) == 1
        assert admin_quantum.json()[0]["lecture_id"] == "lec_quantum"

        admin_paging = client.get("/api/search?q=paging")
        assert admin_paging.status_code == 200
        assert len(admin_paging.json()) == 1
        assert admin_paging.json()[0]["lecture_id"] == "lec_os"
    finally:
        app.dependency_overrides.clear()
