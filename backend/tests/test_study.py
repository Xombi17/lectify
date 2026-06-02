"""Tests for LectureMind Study features (iteration 5):

  1. PATCH /api/lectures/{id}/materials  (teacher manual edits)
  2. GET   /api/lectures/{id}/pdf        (PDF export)
  3. Bookmarks CRUD + isolation
  4. Spaced-repetition flashcards (SM-2 lite) — pure-function & HTTP tests
  5. Repository dispatcher: Mongo (live) and SQL (in-memory SQLite) impls

External APIs: NONE (no Gemini calls). Only Mongo (live) + reportlab + SM-2 math.
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests

sys.path.insert(0, "/app/backend")


def _arun(coro_factory):
    import core.db as core_db
    core_db._client = None
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

TEACHER = {"email": "teacher@lecturemind.example.com", "password": "Password123!",
           "name": "Teacher One", "role": "teacher"}
STUDENT = {"email": "student@lecturemind.example.com", "password": "Password123!",
           "name": "Student One", "role": "student"}


def _signup_or_login(creds: dict) -> dict:
    r = requests.post(f"{API}/auth/signup", json=creds, timeout=30)
    if r.status_code == 201:
        return r.json()
    if r.status_code == 409:
        r2 = requests.post(f"{API}/auth/login",
                           json={"email": creds["email"], "password": creds["password"]},
                           timeout=30)
        assert r2.status_code == 200, f"login fallback failed: {r2.text}"
        return r2.json()
    pytest.fail(f"signup unexpected status {r.status_code}: {r.text}")


def _seed_ready_lecture(teacher_id: str, with_transcript: bool = True,
                        published: bool = False, title: str = "TEST_ Study Lecture",
                        status: str = "ready") -> str:
    """Insert ready+materials lecture directly into Mongo. Returns lecture_id."""
    from repositories.lecture_repository import LectureRepository
    from models.lecture import LectureDB, StudyMaterials, QuizQuestion, Flashcard

    async def _seed():
        repo = LectureRepository()
        lid = repo.new_id()
        doc = LectureDB(
            id=lid,
            teacher_id=teacher_id,
            title=title,
            subject="TEST_Subject",
            semester="Fall-TEST",
            audio_object_key=f"lectures/{lid}/seed.wav",
            audio_filename="seed.wav",
            audio_mime="audio/wav",
            status=status,
            transcript=("Sample transcript about Dijkstra and BFS.") if with_transcript else None,
            published=published,
        )
        doc.materials = StudyMaterials(
            summary="Lecture on Dijkstra shortest path and BFS traversal in graphs.",
            smart_notes=["BFS explores breadth-first", "Dijkstra uses priority queue",
                         "Heaps speed it up", "O(E log V) complexity", "Negative weights break it"],
            key_concepts=["Dijkstra", "BFS", "graph algorithms"],
            quiz=[
                QuizQuestion(question="Q1", options=["a", "b"], answer_index=1, explanation="ex1"),
                QuizQuestion(question="Q2", options=["a", "b"], answer_index=0, explanation="ex2"),
            ],
            flashcards=[
                Flashcard(front="BFS?", back="Breadth-first search"),
                Flashcard(front="Dijkstra?", back="Shortest path single-source"),
                Flashcard(front="Big-O?", back="O(E log V)"),
                Flashcard(front="DAG?", back="Directed Acyclic Graph"),
            ],
        )
        d = doc.model_dump()
        d["created_at"] = d["created_at"].isoformat()
        d["updated_at"] = d["updated_at"].isoformat()
        await repo.col.insert_one(d)
        return lid

    return _arun(_seed)


def _cleanup_lecture(*lecture_ids: str):
    from core.db import get_db

    async def _do():
        db = get_db()
        ids = list(lecture_ids)
        await db["lectures"].delete_many({"id": {"$in": ids}})
        await db["bookmarks"].delete_many({"lecture_id": {"$in": ids}})
        await db["flashcard_reviews"].delete_many({"lecture_id": {"$in": ids}})

    _arun(_do)


@pytest.fixture(scope="module")
def teacher_auth():
    return _signup_or_login(TEACHER)


@pytest.fixture(scope="module")
def student_auth():
    return _signup_or_login(STUDENT)


@pytest.fixture(scope="module")
def th(teacher_auth):
    return {"Authorization": f"Bearer {teacher_auth['access_token']}"}


@pytest.fixture(scope="module")
def sh(student_auth):
    return {"Authorization": f"Bearer {student_auth['access_token']}"}


# ============================================================================
# Feature 1: PATCH /api/lectures/{id}/materials  — teacher manual edit
# ============================================================================
class TestMaterialsEdit:
    @pytest.fixture(scope="class")
    def lec(self, teacher_auth):
        tid = teacher_auth["user"]["id"]
        lid = _seed_ready_lecture(tid, published=False, title="TEST_ Edit Materials")

        # Pre-cache a translation so we can verify it's cleared
        from repositories.lecture_repository import LectureRepository

        async def _cache():
            await LectureRepository().col.update_one(
                {"id": lid},
                {"$set": {"translations": {"spanish": {"summary": "cached"}}}},
            )

        _arun(_cache)
        yield lid
        _cleanup_lecture(lid)

    @pytest.fixture(scope="class")
    def lec_processing(self, teacher_auth):
        tid = teacher_auth["user"]["id"]
        lid = _seed_ready_lecture(tid, status="processing", title="TEST_ Edit Processing")
        yield lid
        _cleanup_lecture(lid)

    def test_edit_requires_auth(self, lec):
        r = requests.patch(f"{API}/lectures/{lec}/materials",
                           json={"summary": "New"}, timeout=15)
        assert r.status_code == 401

    def test_edit_student_403(self, lec, sh):
        r = requests.patch(f"{API}/lectures/{lec}/materials",
                           headers=sh, json={"summary": "New"}, timeout=15)
        # require_teacher dep should give 403
        assert r.status_code == 403

    def test_edit_owner_success_and_clears_translations(self, lec, th):
        new_summary = "Edited summary — by teacher"
        new_notes = ["Note A", " Note B ", ""]   # last is blank; should be filtered
        new_concepts = ["Concept X", "Concept Y"]
        r = requests.patch(f"{API}/lectures/{lec}/materials",
                           headers=th, json={
                               "summary": new_summary,
                               "smart_notes": new_notes,
                               "key_concepts": new_concepts,
                           }, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["materials"]["summary"] == new_summary
        assert body["materials"]["smart_notes"] == ["Note A", "Note B"]
        assert body["materials"]["key_concepts"] == new_concepts
        # cached translation cleared
        assert body.get("translations") in ({}, None)

    def test_edit_404_when_not_owner(self, th):
        # Lecture id that doesn't exist (or owned by someone else)
        r = requests.patch(f"{API}/lectures/non-existent-id/materials",
                           headers=th, json={"summary": "X"}, timeout=15)
        assert r.status_code == 404

    def test_edit_400_when_not_ready(self, lec_processing, th):
        r = requests.patch(f"{API}/lectures/{lec_processing}/materials",
                           headers=th, json={"summary": "X"}, timeout=15)
        assert r.status_code == 400


# ============================================================================
# Feature 2: GET /api/lectures/{id}/pdf  — PDF export
# ============================================================================
class TestPdfExport:
    @pytest.fixture(scope="class")
    def lec_pub(self, teacher_auth):
        tid = teacher_auth["user"]["id"]
        lid = _seed_ready_lecture(tid, published=True, title="TEST_ PDF Published Lecture")
        yield lid
        _cleanup_lecture(lid)

    @pytest.fixture(scope="class")
    def lec_unpub(self, teacher_auth):
        tid = teacher_auth["user"]["id"]
        lid = _seed_ready_lecture(tid, published=False, title="TEST_ PDF Unpublished")
        yield lid
        _cleanup_lecture(lid)

    @pytest.fixture(scope="class")
    def lec_processing(self, teacher_auth):
        tid = teacher_auth["user"]["id"]
        lid = _seed_ready_lecture(tid, status="processing", title="TEST_ PDF Processing")
        yield lid
        _cleanup_lecture(lid)

    def test_pdf_404_missing(self, th):
        r = requests.get(f"{API}/lectures/zzz-doesnotexist/pdf", headers=th, timeout=15)
        assert r.status_code == 404

    def test_pdf_403_student_on_unpublished(self, lec_unpub, sh):
        r = requests.get(f"{API}/lectures/{lec_unpub}/pdf", headers=sh, timeout=15)
        assert r.status_code == 403

    def test_pdf_400_when_not_ready(self, lec_processing, th):
        r = requests.get(f"{API}/lectures/{lec_processing}/pdf", headers=th, timeout=15)
        assert r.status_code == 400

    def test_pdf_success_owner(self, lec_pub, th):
        r = requests.get(f"{API}/lectures/{lec_pub}/pdf", headers=th, timeout=30)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        cd = r.headers.get("content-disposition", "")
        assert "filename=" in cd
        body = r.content
        assert body[:4] == b"%PDF", "PDF magic bytes missing"
        assert len(body) > 500

        # Decode with pypdf for full content assertion
        import pypdf
        from io import BytesIO
        reader = pypdf.PdfReader(BytesIO(body))
        assert len(reader.pages) >= 1
        full_text = " ".join(p.extract_text() or "" for p in reader.pages)
        assert "TEST_ PDF Published Lecture" in full_text or "PDF Published" in full_text
        # Key sections present
        assert "Smart Notes" in full_text
        assert "Key Concepts" in full_text
        assert "Quiz" in full_text
        assert "Flashcards" in full_text

    def test_pdf_success_student_on_published(self, lec_pub, sh):
        r = requests.get(f"{API}/lectures/{lec_pub}/pdf", headers=sh, timeout=30)
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"


# ============================================================================
# Feature 3: Bookmarks CRUD + isolation
# ============================================================================
class TestBookmarks:
    @pytest.fixture(scope="class")
    def setup(self, teacher_auth, student_auth):
        tid = teacher_auth["user"]["id"]
        sid = student_auth["user"]["id"]
        lec_pub = _seed_ready_lecture(tid, published=True, title="TEST_ Bookmarks Pub")
        lec_unpub = _seed_ready_lecture(tid, published=False, title="TEST_ Bookmarks Unpub")

        # cleanup any prior test bookmarks for these users
        from core.db import get_db

        async def _wipe():
            db = get_db()
            await db["bookmarks"].delete_many({"user_id": {"$in": [tid, sid]}})

        _arun(_wipe)
        yield {"lec_pub": lec_pub, "lec_unpub": lec_unpub, "tid": tid, "sid": sid}
        _cleanup_lecture(lec_pub, lec_unpub)

    def test_bookmark_requires_auth(self, setup):
        r = requests.post(f"{API}/bookmarks",
                          json={"lecture_id": setup["lec_pub"], "kind": "concept",
                                "text": "Dijkstra", "ref_index": 0}, timeout=15)
        assert r.status_code == 401

    def test_bookmark_404_missing_lecture(self, setup, sh):
        r = requests.post(f"{API}/bookmarks", headers=sh,
                          json={"lecture_id": "zzz-nope", "kind": "concept",
                                "text": "x"}, timeout=15)
        assert r.status_code == 404

    def test_bookmark_403_student_on_unpublished(self, setup, sh):
        r = requests.post(f"{API}/bookmarks", headers=sh,
                          json={"lecture_id": setup["lec_unpub"], "kind": "concept",
                                "text": "Dijkstra", "ref_index": 0}, timeout=15)
        assert r.status_code == 403

    def test_bookmark_create_and_idempotent(self, setup, sh):
        payload = {"lecture_id": setup["lec_pub"], "kind": "concept",
                   "text": "Dijkstra", "ref_index": 0}
        r1 = requests.post(f"{API}/bookmarks", headers=sh, json=payload, timeout=15)
        assert r1.status_code == 201, r1.text
        b1 = r1.json()
        assert b1["user_id"] == setup["sid"]
        assert b1["kind"] == "concept"
        assert b1["text"] == "Dijkstra"
        assert b1["ref_index"] == 0

        # Same payload again -> idempotent (returns existing, same id)
        r2 = requests.post(f"{API}/bookmarks", headers=sh, json=payload, timeout=15)
        assert r2.status_code in (200, 201)
        assert r2.json()["id"] == b1["id"]

        # Verify only one row in DB
        from core.db import get_db

        async def _count():
            return await get_db()["bookmarks"].count_documents({
                "user_id": setup["sid"],
                "lecture_id": setup["lec_pub"],
                "kind": "concept",
                "ref_index": 0,
            })

        n = _arun(_count)
        assert n == 1, f"expected idempotent (1 row), got {n}"

    def test_list_my_bookmarks_isolation(self, setup, sh, th):
        # Teacher creates a bookmark on the published lecture
        rt = requests.post(f"{API}/bookmarks", headers=th,
                           json={"lecture_id": setup["lec_pub"], "kind": "note",
                                 "text": "Teacher note", "ref_index": 1}, timeout=15)
        assert rt.status_code == 201

        # Student lists own bookmarks -> NOT see teacher's
        rs = requests.get(f"{API}/bookmarks/me", headers=sh, timeout=15)
        assert rs.status_code == 200
        items = rs.json()
        assert all(b["user_id"] == setup["sid"] for b in items)
        assert any(b["text"] == "Dijkstra" for b in items)
        # Enrichment
        for b in items:
            assert "lecture_title" in b
            assert "lecture_subject" in b

        # Teacher lists own
        rtl = requests.get(f"{API}/bookmarks/me", headers=th, timeout=15)
        assert rtl.status_code == 200
        teacher_items = rtl.json()
        assert all(b["user_id"] == setup["tid"] for b in teacher_items)
        assert any(b["text"] == "Teacher note" for b in teacher_items)

    def test_list_lecture_bookmarks_isolation(self, setup, sh, th):
        # student should only see their own bookmark on lec_pub
        rs = requests.get(f"{API}/bookmarks/me", headers=sh, timeout=15)
        student_ids = {b["id"] for b in rs.json() if b["lecture_id"] == setup["lec_pub"]}

        r = requests.get(f"{API}/lectures/{setup['lec_pub']}/bookmarks",
                         headers=sh, timeout=15)
        assert r.status_code == 200
        per_lecture = r.json()
        assert {b["id"] for b in per_lecture} == student_ids
        # No teacher bookmark
        assert all(b["user_id"] == setup["sid"] for b in per_lecture)

    def test_delete_bookmark_owner_and_wrong_user(self, setup, sh, th):
        # Create then delete as same user
        r = requests.post(f"{API}/bookmarks", headers=sh,
                          json={"lecture_id": setup["lec_pub"], "kind": "flashcard",
                                "text": "BFS?", "ref_index": 0}, timeout=15)
        assert r.status_code == 201
        bid = r.json()["id"]

        # Wrong user -> 404
        r_wrong = requests.delete(f"{API}/bookmarks/{bid}", headers=th, timeout=15)
        assert r_wrong.status_code == 404

        # Right user -> 204
        r_ok = requests.delete(f"{API}/bookmarks/{bid}", headers=sh, timeout=15)
        assert r_ok.status_code == 204

        # Repeat delete -> 404
        r_again = requests.delete(f"{API}/bookmarks/{bid}", headers=sh, timeout=15)
        assert r_again.status_code == 404


# ============================================================================
# Feature 4: Spaced-repetition (SM-2)  — pure function & HTTP
# ============================================================================
class TestSm2PureFunction:
    """Unit tests for services/spaced_repetition.py — no DB."""

    def _seed(self, **over):
        from models.bookmark import FlashcardReviewDB
        base = dict(
            id="r1", user_id="u1", lecture_id="l1", card_index=0,
            ease_factor=2.5, interval_days=0, repetitions=0, total_reviews=0,
        )
        base.update(over)
        return FlashcardReviewDB(**base)

    def test_again_resets_reps_and_clamps_ease(self):
        from services.spaced_repetition import schedule_next
        prev = self._seed(repetitions=4, ease_factor=1.4, interval_days=20)
        nxt = schedule_next(prev, quality=0)
        assert nxt.repetitions == 0
        assert nxt.interval_days == 1
        # 1.4 - 0.20 = 1.20 -> clamped to 1.3
        assert nxt.ease_factor == 1.3

    def test_again_decrements_ease(self):
        from services.spaced_repetition import schedule_next
        prev = self._seed(ease_factor=2.5)
        nxt = schedule_next(prev, quality=0)
        assert nxt.ease_factor == round(2.5 - 0.20, 2)

    def test_good_progression_first_then_six_then_multiply(self):
        from services.spaced_repetition import schedule_next
        prev = self._seed()
        a = schedule_next(prev, quality=2)
        assert a.repetitions == 1
        assert a.interval_days == 1

        b = schedule_next(a, quality=2)
        assert b.repetitions == 2
        assert b.interval_days == 6

        c = schedule_next(b, quality=2)
        assert c.repetitions == 3
        # interval was 6, ease 2.5 -> 15
        assert c.interval_days == round(6 * 2.5)

    def test_easy_bumps_ease_clamped_high(self):
        from services.spaced_repetition import schedule_next
        prev = self._seed(ease_factor=2.75)
        nxt = schedule_next(prev, quality=3)
        # 2.75 + 0.10 = 2.85 -> clamp to 2.8
        assert nxt.ease_factor == 2.8

    def test_due_at_offset_matches_interval_days(self):
        from services.spaced_repetition import schedule_next
        prev = self._seed()
        nxt = schedule_next(prev, quality=2)
        # due_at ~ now + 1 day; allow 5-min skew
        expected = datetime.now(timezone.utc) + timedelta(days=nxt.interval_days)
        delta = abs((nxt.due_at - expected).total_seconds())
        assert delta < 300, f"due_at off by {delta}s"

    def test_invalid_quality_raises(self):
        from services.spaced_repetition import schedule_next
        with pytest.raises(ValueError):
            schedule_next(self._seed(), quality=5)


class TestReviewHttp:
    @pytest.fixture(scope="class")
    def setup(self, teacher_auth, student_auth):
        tid = teacher_auth["user"]["id"]
        sid = student_auth["user"]["id"]
        lec_pub = _seed_ready_lecture(tid, published=True, title="TEST_ Review Pub")
        lec_unpub = _seed_ready_lecture(tid, published=False, title="TEST_ Review Unpub")

        from core.db import get_db

        async def _wipe():
            db = get_db()
            await db["flashcard_reviews"].delete_many({"user_id": {"$in": [tid, sid]}})

        _arun(_wipe)
        yield {"lec_pub": lec_pub, "lec_unpub": lec_unpub, "tid": tid, "sid": sid}
        _cleanup_lecture(lec_pub, lec_unpub)

    def test_review_422_invalid_quality(self, setup, sh):
        r = requests.post(f"{API}/flashcards/review", headers=sh,
                          json={"lecture_id": setup["lec_pub"], "card_index": 0,
                                "quality": 99}, timeout=15)
        assert r.status_code == 422

    def test_review_400_card_index_out_of_bounds(self, setup, sh):
        r = requests.post(f"{API}/flashcards/review", headers=sh,
                          json={"lecture_id": setup["lec_pub"], "card_index": 999,
                                "quality": 2}, timeout=15)
        assert r.status_code == 400

    def test_review_404_missing_lecture(self, setup, sh):
        r = requests.post(f"{API}/flashcards/review", headers=sh,
                          json={"lecture_id": "zzz-nope", "card_index": 0,
                                "quality": 2}, timeout=15)
        assert r.status_code == 404

    def test_review_403_student_unpublished(self, setup, sh):
        r = requests.post(f"{API}/flashcards/review", headers=sh,
                          json={"lecture_id": setup["lec_unpub"], "card_index": 0,
                                "quality": 2}, timeout=15)
        assert r.status_code == 403

    def test_review_creates_then_upserts(self, setup, sh):
        # First review: Good -> interval=1, reps=1
        r1 = requests.post(f"{API}/flashcards/review", headers=sh,
                           json={"lecture_id": setup["lec_pub"], "card_index": 0,
                                 "quality": 2}, timeout=15)
        assert r1.status_code == 200, r1.text
        b1 = r1.json()
        assert b1["repetitions"] == 1
        assert b1["interval_days"] == 1
        assert b1["total_reviews"] == 1

        # Second review on same card (upsert): Good -> reps=2, interval=6
        r2 = requests.post(f"{API}/flashcards/review", headers=sh,
                           json={"lecture_id": setup["lec_pub"], "card_index": 0,
                                 "quality": 2}, timeout=15)
        assert r2.status_code == 200
        b2 = r2.json()
        assert b2["repetitions"] == 2
        assert b2["interval_days"] == 6
        assert b2["total_reviews"] == 2
        # Same primary key (no duplicate row)
        from core.db import get_db

        async def _count():
            return await get_db()["flashcard_reviews"].count_documents({
                "user_id": setup["sid"], "lecture_id": setup["lec_pub"], "card_index": 0,
            })

        assert _arun(_count) == 1

    def test_due_endpoint_hydration_and_filter(self, setup, sh, student_auth):
        # Seed a "due" review (due in the past) on another card
        from repositories.flashcard_review_repository import FlashcardReviewRepository
        from models.bookmark import FlashcardReviewDB

        sid = setup["sid"]
        past = datetime.now(timezone.utc) - timedelta(days=1)
        rev = FlashcardReviewDB(
            id=str(uuid.uuid4()), user_id=sid, lecture_id=setup["lec_pub"],
            card_index=1, ease_factor=2.5, interval_days=1, repetitions=1,
            last_reviewed_at=past, due_at=past, total_reviews=1,
        )

        async def _seed_rev():
            await FlashcardReviewRepository().upsert(rev)

        _arun(_seed_rev)

        # Defensive: seed a review with out-of-bounds card_index — must be filtered out
        bad = FlashcardReviewDB(
            id=str(uuid.uuid4()), user_id=sid, lecture_id=setup["lec_pub"],
            card_index=99, ease_factor=2.5, interval_days=1, repetitions=1,
            last_reviewed_at=past, due_at=past, total_reviews=1,
        )

        async def _seed_bad():
            await FlashcardReviewRepository().upsert(bad)

        _arun(_seed_bad)

        r = requests.get(f"{API}/flashcards/due", headers=sh, timeout=15)
        assert r.status_code == 200, r.text
        due_cards = r.json()
        # Card_index 1 should be present, 99 must NOT be
        idxs = [(c["lecture_id"], c["card_index"]) for c in due_cards]
        assert (setup["lec_pub"], 1) in idxs
        assert (setup["lec_pub"], 99) not in idxs
        # Hydration present
        card1 = next(c for c in due_cards if c["card_index"] == 1
                     and c["lecture_id"] == setup["lec_pub"])
        assert card1["lecture_title"] == "TEST_ Review Pub"
        assert card1["front"] == "Dijkstra?"
        assert card1["back"] == "Shortest path single-source"

    def test_due_filters_unpublished_for_student(self, setup, sh):
        # Seed a due review on an UNPUBLISHED lecture for the student
        from repositories.flashcard_review_repository import FlashcardReviewRepository
        from models.bookmark import FlashcardReviewDB

        past = datetime.now(timezone.utc) - timedelta(days=1)
        rev = FlashcardReviewDB(
            id=str(uuid.uuid4()), user_id=setup["sid"], lecture_id=setup["lec_unpub"],
            card_index=0, ease_factor=2.5, interval_days=1, repetitions=1,
            last_reviewed_at=past, due_at=past, total_reviews=1,
        )

        async def _seed():
            await FlashcardReviewRepository().upsert(rev)

        _arun(_seed)

        r = requests.get(f"{API}/flashcards/due", headers=sh, timeout=15)
        assert r.status_code == 200
        due = r.json()
        assert all(c["lecture_id"] != setup["lec_unpub"] for c in due)

    def test_lecture_flashcard_state(self, setup, sh):
        r = requests.get(f"{API}/lectures/{setup['lec_pub']}/flashcards/state",
                         headers=sh, timeout=15)
        assert r.status_code == 200
        items = r.json()
        # All for sid on lec_pub
        assert all(it["user_id"] == setup["sid"] for it in items)
        assert all(it["lecture_id"] == setup["lec_pub"] for it in items)


# ============================================================================
# Feature 5: PDF unit test (pure-function, no DB / HTTP)
# ============================================================================
class TestPdfUnit:
    def test_render_lecture_pdf_bytes_have_magic_and_title(self):
        from models.lecture import LectureDB, StudyMaterials, QuizQuestion, Flashcard
        from services.pdf_export import render_lecture_pdf

        lec = LectureDB(
            id="x", teacher_id="t", title="Algorithm Recap Lecture",
            subject="CS", semester="Fall25",
            audio_object_key="x", audio_filename="a.wav", audio_mime="audio/wav",
            status="ready",
            materials=StudyMaterials(
                summary="A talk on dijkstra & BFS.",
                smart_notes=[f"Note {i}" for i in range(5)],
                key_concepts=["KC1", "KC2", "KC3"],
                quiz=[
                    QuizQuestion(question=f"Q{i}", options=["a", "b"], answer_index=0,
                                 explanation="e") for i in range(2)
                ],
                flashcards=[Flashcard(front=f"f{i}", back=f"b{i}") for i in range(4)],
            ),
        )
        b = render_lecture_pdf(lec)
        assert b[:4] == b"%PDF"
        assert len(b) > 500

        import pypdf
        from io import BytesIO
        reader = pypdf.PdfReader(BytesIO(b))
        text = " ".join(p.extract_text() or "" for p in reader.pages)
        assert "Algorithm Recap Lecture" in text
        assert "Smart Notes" in text
        assert "Key Concepts" in text
        assert "Quiz" in text
        assert "Flashcards" in text


# ============================================================================
# Feature 6: Repository dispatcher — SQL impl with in-memory SQLite
# ============================================================================
class TestSqlBookmarkAndReviewRepos:
    """Exercise _sql impls against aiosqlite. Mirrors test_sql_repositories.py pattern."""

    @pytest.fixture(autouse=True)
    def _sql_env(self, monkeypatch):
        monkeypatch.setenv("DATABASE_BACKEND", "postgres")
        monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
        import importlib
        from core import config as cfg
        cfg.get_settings.cache_clear()
        importlib.reload(cfg)
        import core.sql_db as sdb
        importlib.reload(sdb)
        import repositories._sql.user_repository as ur
        import repositories._sql.lecture_repository as lr
        import repositories._sql.bookmark_repository as br
        import repositories._sql.flashcard_review_repository as fr
        importlib.reload(ur); importlib.reload(lr)
        importlib.reload(br); importlib.reload(fr)
        yield
        cfg.get_settings.cache_clear()

    def _setup(self):
        from core.sql_db import init_models
        from repositories._sql.user_repository import UserRepository
        from repositories._sql.lecture_repository import LectureRepository
        from models.user import UserDB
        from models.lecture import LectureDB, StudyMaterials, Flashcard

        async def go():
            await init_models()
            uid = "u-1"
            lid = "l-1"
            await UserRepository().create(UserDB(
                id=uid, name="U", email="u@x.com", role="student", password_hash="h"))
            mats = StudyMaterials(flashcards=[
                Flashcard(front="f0", back="b0"),
                Flashcard(front="f1", back="b1"),
            ])
            await LectureRepository().create(LectureDB(
                id=lid, teacher_id=uid, title="L", subject=None, semester=None,
                audio_object_key="k", audio_filename="a.wav", audio_mime="audio/wav",
                materials=mats,
            ))
            return uid, lid

        return go

    def test_sql_bookmark_full_cycle(self):
        from repositories._sql.bookmark_repository import BookmarkRepository
        from models.bookmark import BookmarkDB

        async def go():
            uid, lid = await self._setup()()
            repo = BookmarkRepository()
            bm = BookmarkDB(id=repo.new_id(), user_id=uid, lecture_id=lid,
                            kind="concept", text="Dijkstra", ref_index=0)
            await repo.add(bm)

            existing = await repo.find_existing(uid, lid, "concept", 0)
            assert existing is not None
            assert existing.id == bm.id

            none = await repo.find_existing(uid, lid, "concept", 99)
            assert none is None

            all_user = await repo.list_for_user(uid)
            assert len(all_user) == 1

            per_lec = await repo.list_for_user_lecture(uid, lid)
            assert len(per_lec) == 1

            # Wrong-user delete fails
            ok_wrong = await repo.delete(bm.id, "other-user")
            assert ok_wrong is False

            ok = await repo.delete(bm.id, uid)
            assert ok is True
            assert await repo.find_existing(uid, lid, "concept", 0) is None

            from core.sql_db import close_sql
            await close_sql()

        asyncio.run(go())

    def test_sql_flashcard_review_full_cycle(self):
        from repositories._sql.flashcard_review_repository import FlashcardReviewRepository
        from models.bookmark import FlashcardReviewDB

        async def go():
            uid, lid = await self._setup()()
            repo = FlashcardReviewRepository()
            past = datetime.now(timezone.utc) - timedelta(days=1)
            r1 = FlashcardReviewDB(id=repo.new_id(), user_id=uid, lecture_id=lid,
                                   card_index=0, ease_factor=2.5, interval_days=1,
                                   repetitions=1, last_reviewed_at=past, due_at=past,
                                   total_reviews=1)
            await repo.upsert(r1)

            got = await repo.get(uid, lid, 0)
            assert got is not None
            assert got.repetitions == 1

            # Upsert idempotency — change values, expect same single row
            r1b = r1.model_copy(update={"repetitions": 5, "interval_days": 7})
            await repo.upsert(r1b)
            got2 = await repo.get(uid, lid, 0)
            assert got2.repetitions == 5
            assert got2.interval_days == 7

            # list_due: r1 is past-due
            due = await repo.list_due_for_user(uid)
            assert len(due) == 1

            # list_all
            all_revs = await repo.list_all_for_user(uid)
            assert len(all_revs) == 1

            from core.sql_db import close_sql
            await close_sql()

        asyncio.run(go())


class TestDispatcher:
    def test_dispatcher_mongo_default(self, monkeypatch):
        """With default mongo backend, dispatcher should re-export _mongo impls."""
        monkeypatch.setenv("DATABASE_BACKEND", "mongo")
        import importlib
        from core import config as cfg
        cfg.get_settings.cache_clear()
        importlib.reload(cfg)
        import repositories.bookmark_repository as bref
        import repositories.flashcard_review_repository as fref
        importlib.reload(bref); importlib.reload(fref)
        from repositories._mongo.bookmark_repository import BookmarkRepository as MBM
        from repositories._mongo.flashcard_review_repository import FlashcardReviewRepository as MFR
        assert bref.BookmarkRepository is MBM
        assert fref.FlashcardReviewRepository is MFR

    def test_dispatcher_postgres_picks_sql(self, monkeypatch):
        monkeypatch.setenv("DATABASE_BACKEND", "postgres")
        monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
        import importlib
        from core import config as cfg
        cfg.get_settings.cache_clear()
        importlib.reload(cfg)
        import repositories.bookmark_repository as bref
        import repositories.flashcard_review_repository as fref
        importlib.reload(bref); importlib.reload(fref)
        from repositories._sql.bookmark_repository import BookmarkRepository as SBM
        from repositories._sql.flashcard_review_repository import FlashcardReviewRepository as SFR
        assert bref.BookmarkRepository is SBM
        assert fref.FlashcardReviewRepository is SFR
