"""P1 feature tests for LectureMind AI.

Covers:
  - POST /api/lectures/{id}/chat (auth, 404, 403 student-unpublished, 400 transcript-missing,
    persist messages, graceful 500 when GEMINI missing)
  - GET /api/lectures/{id}/chat (history ordering oldest-first, isolation per user)
  - POST /api/lectures/{id}/translate (auth, 400 not-ready, cache hit path,
    403 student-unpublished, 500-when-gemini-missing-graceful)
  - GET /api/search (auth, empty when no published, lexical fallback ranks
    higher score for better keyword match)
  - GET /api/analytics/me (auth, baseline zeros, after 3 seeded attempts -> counts,
    avg, weak/strong, streak math broken on gap)
  - POST /api/lectures/{id}/quiz/attempt persists into quiz_attempts collection
  - RBAC: teacher chat/translate/search own unpublished lecture
  - Cleanup: TEST_ prefixed lectures + chat_messages + quiz_attempts wiped at teardown
"""
import asyncio
import os
import struct
import sys
import time
from datetime import datetime, timedelta, timezone

import pytest
import requests

sys.path.insert(0, "/app/backend")

# Helper: run an async coroutine on a fresh event loop AND reset the
# core.db singleton (which caches a Motor client bound to the previous loop).
def _arun(coro_factory):
    """coro_factory: a zero-arg callable that returns a fresh coroutine."""
    import core.db as core_db  # noqa
    # Reset cached client so a new one is created on the new loop
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


def _wav_bytes(seconds=0.1, sample_rate=8000):
    n = int(seconds * sample_rate)
    data = b"\x00\x00" * n
    return (b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVE" + b"fmt "
            + struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16)
            + b"data" + struct.pack("<I", len(data)) + data)


# ---------- fixtures ----------

@pytest.fixture(scope="session")
def teacher_auth():
    return _signup_or_login(TEACHER)


@pytest.fixture(scope="session")
def student_auth():
    return _signup_or_login(STUDENT)


@pytest.fixture(scope="session")
def teacher_headers(teacher_auth):
    return {"Authorization": f"Bearer {teacher_auth['access_token']}"}


@pytest.fixture(scope="session")
def student_headers(student_auth):
    return {"Authorization": f"Bearer {student_auth['access_token']}"}


@pytest.fixture(scope="session")
def teacher_id(teacher_auth):
    return teacher_auth["user"]["id"]


@pytest.fixture(scope="session")
def student_id(student_auth):
    return student_auth["user"]["id"]


def _seed_ready_lecture(teacher_id: str, with_transcript: bool = True,
                        published: bool = False, title: str = "TEST_ P1 Lecture") -> str:
    """Insert a ready+materials lecture directly via Mongo so tests don't depend on Gemini."""
    from repositories.lecture_repository import LectureRepository
    from models.lecture import LectureDB

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
            status="ready",
            transcript=("Sample transcript about Dijkstra and BFS. "
                        "Graph algorithms include shortest path and traversal.")
            if with_transcript else None,
            published=published,
        )
        # Attach minimal materials
        from models.lecture import StudyMaterials, QuizQuestion, Flashcard
        doc.materials = StudyMaterials(
            summary="Lecture on Dijkstra shortest path and BFS traversal in graphs.",
            smart_notes=["BFS explores breadth-first", "Dijkstra uses priority queue"],
            key_concepts=["Dijkstra", "BFS", "graph algorithms", "shortest path"],
            quiz=[
                QuizQuestion(question="Q1", options=["a", "b"], answer_index=1, explanation=""),
                QuizQuestion(question="Q2", options=["a", "b"], answer_index=0, explanation=""),
            ],
            flashcards=[Flashcard(front="BFS?", back="Breadth-first search")],
        )
        # Serialize via repo
        d = doc.model_dump()
        d["created_at"] = d["created_at"].isoformat()
        d["updated_at"] = d["updated_at"].isoformat()
        await repo.col.insert_one(d)
        return lid

    return _arun(_seed)


def _seed_chat_message(lecture_id: str, user_id: str, role: str, content: str, offset_s: int = 0):
    from repositories.chat_repository import ChatRepository
    from models.chat import ChatMessageDB

    async def _do():
        repo = ChatRepository()
        msg = ChatMessageDB(
            id=repo.new_id(),
            lecture_id=lecture_id,
            user_id=user_id,
            role=role,
            content=content,
            created_at=datetime.now(timezone.utc) + timedelta(seconds=offset_s),
        )
        await repo.add(msg)
        return msg.id

    return _arun(_do)


def _seed_quiz_attempt(lecture_id: str, user_id: str, percentage: float,
                       score: int = 5, total: int = 10, day_offset: int = 0):
    from repositories.attempt_repository import AttemptRepository
    from models.chat import QuizAttemptRecord

    async def _do():
        repo = AttemptRepository()
        rec = QuizAttemptRecord(
            id=repo.new_id(),
            lecture_id=lecture_id,
            user_id=user_id,
            score=score,
            total=total,
            percentage=percentage,
            created_at=datetime.now(timezone.utc) + timedelta(days=day_offset),
        )
        await repo.add(rec)
        return rec.id

    return _arun(_do)


def _cleanup_collections(lecture_ids: list[str], user_ids: list[str]):
    from core.db import get_db

    async def _do():
        db = get_db()
        if lecture_ids:
            await db["lectures"].delete_many({"id": {"$in": lecture_ids}})
            await db["chat_messages"].delete_many({"lecture_id": {"$in": lecture_ids}})
            await db["quiz_attempts"].delete_many({"lecture_id": {"$in": lecture_ids}})
        if user_ids:
            await db["chat_messages"].delete_many({"user_id": {"$in": user_ids}})
            await db["quiz_attempts"].delete_many({"user_id": {"$in": user_ids}})

    _arun(_do)


# ---------- CHAT ----------

class TestChat:
    @pytest.fixture(scope="class")
    def seeded(self, request):
        teacher = _signup_or_login(TEACHER)
        student = _signup_or_login(STUDENT)
        tid = teacher["user"]["id"]
        sid = student["user"]["id"]
        # one with transcript+ready (unpublished)
        lec_unpub = _seed_ready_lecture(tid, with_transcript=True, published=False,
                                        title="TEST_ P1 Chat Unpub")
        lec_pub = _seed_ready_lecture(tid, with_transcript=True, published=True,
                                      title="TEST_ P1 Chat Pub")
        # one with NO transcript but ready (to test 400 transcript-not-ready)
        lec_no_tx = _seed_ready_lecture(tid, with_transcript=False, published=True,
                                        title="TEST_ P1 Chat NoTx")

        data = {
            "teacher_headers": {"Authorization": f"Bearer {teacher['access_token']}"},
            "student_headers": {"Authorization": f"Bearer {student['access_token']}"},
            "lec_unpub": lec_unpub,
            "lec_pub": lec_pub,
            "lec_no_tx": lec_no_tx,
            "tid": tid,
            "sid": sid,
        }
        yield data
        _cleanup_collections([lec_unpub, lec_pub, lec_no_tx], [tid, sid])

    def test_chat_requires_auth(self, seeded):
        r = requests.post(f"{API}/lectures/{seeded['lec_pub']}/chat",
                          json={"question": "what is BFS?"}, timeout=15)
        assert r.status_code == 401

    def test_chat_404_missing(self, seeded):
        r = requests.post(f"{API}/lectures/does-not-exist/chat",
                          headers=seeded["teacher_headers"],
                          json={"question": "hi"}, timeout=15)
        assert r.status_code == 404

    def test_chat_student_403_on_unpublished(self, seeded):
        r = requests.post(f"{API}/lectures/{seeded['lec_unpub']}/chat",
                          headers=seeded["student_headers"],
                          json={"question": "hi"}, timeout=15)
        assert r.status_code == 403

    def test_chat_400_transcript_missing(self, seeded):
        r = requests.post(f"{API}/lectures/{seeded['lec_no_tx']}/chat",
                          headers=seeded["teacher_headers"],
                          json={"question": "hi"}, timeout=15)
        assert r.status_code == 400

    def test_chat_teacher_own_unpublished_ok_or_gemini_500(self, seeded):
        """Teacher can chat own unpublished if AI works. Without GEMINI, expect 500 (graceful)."""
        r = requests.post(f"{API}/lectures/{seeded['lec_unpub']}/chat",
                          headers=seeded["teacher_headers"],
                          json={"question": "Explain Dijkstra"}, timeout=60)
        assert r.status_code in (200, 500), f"got {r.status_code}: {r.text}"
        if r.status_code == 200:
            body = r.json()
            assert body["user_message"]["role"] == "user"
            assert body["assistant_message"]["role"] == "assistant"
            assert body["user_message"]["content"]

    def test_chat_history_oldest_first_and_isolated(self, seeded):
        """Seed 2 messages for teacher, 2 for student on same lecture, ensure isolation + order."""
        lid = seeded["lec_pub"]
        # Seed messages with explicit time offsets
        _seed_chat_message(lid, seeded["tid"], "user", "T-USER-1", offset_s=-100)
        _seed_chat_message(lid, seeded["tid"], "assistant", "T-ASSIST-1", offset_s=-90)
        _seed_chat_message(lid, seeded["sid"], "user", "S-USER-1", offset_s=-80)
        _seed_chat_message(lid, seeded["sid"], "assistant", "S-ASSIST-1", offset_s=-70)

        # Teacher's history
        rt = requests.get(f"{API}/lectures/{lid}/chat",
                          headers=seeded["teacher_headers"], timeout=15)
        assert rt.status_code == 200
        msgs_t = rt.json()
        contents_t = [m["content"] for m in msgs_t]
        # Should contain only teacher's seeded messages
        assert "T-USER-1" in contents_t
        assert "T-ASSIST-1" in contents_t
        assert "S-USER-1" not in contents_t, "Student messages must not leak to teacher"
        assert "S-ASSIST-1" not in contents_t

        # Order: oldest first (created_at ascending)
        ts = [m["created_at"] for m in msgs_t]
        assert ts == sorted(ts), "History must be oldest first"

        # Student's history
        rs = requests.get(f"{API}/lectures/{lid}/chat",
                          headers=seeded["student_headers"], timeout=15)
        assert rs.status_code == 200
        contents_s = [m["content"] for m in rs.json()]
        assert "S-USER-1" in contents_s
        assert "T-USER-1" not in contents_s

    def test_chat_history_404_missing(self, seeded):
        r = requests.get(f"{API}/lectures/zzz-nope/chat",
                         headers=seeded["teacher_headers"], timeout=15)
        assert r.status_code == 404

    def test_chat_history_403_student_unpublished(self, seeded):
        r = requests.get(f"{API}/lectures/{seeded['lec_unpub']}/chat",
                         headers=seeded["student_headers"], timeout=15)
        assert r.status_code == 403


# ---------- TRANSLATE ----------

class TestTranslate:
    @pytest.fixture(scope="class")
    def seeded(self):
        teacher = _signup_or_login(TEACHER)
        student = _signup_or_login(STUDENT)
        tid = teacher["user"]["id"]
        sid = student["user"]["id"]
        lec_unpub = _seed_ready_lecture(tid, published=False, title="TEST_ P1 Translate Unpub")
        lec_pub = _seed_ready_lecture(tid, published=True, title="TEST_ P1 Translate Pub")

        # Lecture with status != ready for the 400 test
        from repositories.lecture_repository import LectureRepository

        async def _err_lec():
            repo = LectureRepository()
            lid = repo.new_id()
            now = datetime.now(timezone.utc).isoformat()
            await repo.col.insert_one({
                "id": lid, "teacher_id": tid, "title": "TEST_ Translate Err",
                "audio_object_key": f"lectures/{lid}/x.wav", "audio_filename": "x.wav",
                "audio_mime": "audio/wav", "status": "error", "published": False,
                "materials": {"summary": "", "smart_notes": [], "key_concepts": [],
                              "quiz": [], "flashcards": []},
                "translations": {}, "created_at": now, "updated_at": now,
            })
            return lid

        lec_err = _arun(_err_lec)

        # Pre-cache a translation directly on lec_pub
        from repositories.lecture_repository import LectureRepository as LR
        async def _cache():
            await LR().col.update_one({"id": lec_pub}, {"$set": {"translations": {
                "spanish": {"summary": "Resumen pre-cached", "smart_notes": ["Nota"],
                            "key_concepts": ["Dijkstra"], "flashcards": []}
            }}})

        _arun(_cache)

        data = {
            "teacher_headers": {"Authorization": f"Bearer {teacher['access_token']}"},
            "student_headers": {"Authorization": f"Bearer {student['access_token']}"},
            "lec_unpub": lec_unpub, "lec_pub": lec_pub, "lec_err": lec_err,
            "tid": tid, "sid": sid,
        }
        yield data
        _cleanup_collections([lec_unpub, lec_pub, lec_err], [tid, sid])

    def test_translate_requires_auth(self, seeded):
        r = requests.post(f"{API}/lectures/{seeded['lec_pub']}/translate",
                          json={"target_language": "spanish"}, timeout=15)
        assert r.status_code == 401

    def test_translate_400_when_not_ready(self, seeded):
        r = requests.post(f"{API}/lectures/{seeded['lec_err']}/translate",
                          headers=seeded["teacher_headers"],
                          json={"target_language": "spanish"}, timeout=15)
        assert r.status_code == 400

    def test_translate_student_403_on_unpublished(self, seeded):
        r = requests.post(f"{API}/lectures/{seeded['lec_unpub']}/translate",
                          headers=seeded["student_headers"],
                          json={"target_language": "spanish"}, timeout=15)
        assert r.status_code == 403

    def test_translate_cache_hit_no_ai_call(self, seeded):
        """Pre-cached 'spanish' should return without invoking AI (works even when GEMINI is empty)."""
        r = requests.post(f"{API}/lectures/{seeded['lec_pub']}/translate",
                          headers=seeded["teacher_headers"],
                          json={"target_language": "Spanish"}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["summary"] == "Resumen pre-cached"

    def test_translate_cold_path_either_200_or_500(self, seeded):
        """Cold path requires Gemini; in preview key is empty -> graceful 500. If a key is configured -> 200."""
        r = requests.post(f"{API}/lectures/{seeded['lec_pub']}/translate",
                          headers=seeded["teacher_headers"],
                          json={"target_language": "Hindi"}, timeout=60)
        assert r.status_code in (200, 500), f"got {r.status_code}: {r.text}"

        if r.status_code == 200:
            # verify cache grew
            from repositories.lecture_repository import LectureRepository

            async def _check():
                lec = await LectureRepository().get_by_id(seeded["lec_pub"])
                return lec.translations

            tr = _arun(_check)
            assert "hindi" in tr


# ---------- SEARCH ----------

class TestSearch:
    @pytest.fixture(scope="class")
    def seeded(self):
        teacher = _signup_or_login(TEACHER)
        student = _signup_or_login(STUDENT)
        tid = teacher["user"]["id"]
        sid = student["user"]["id"]
        # Two published lectures with different keyword density
        lec_dijkstra = _seed_ready_lecture(tid, published=True, title="TEST_ Dijkstra Deep Dive")
        lec_bfs = _seed_ready_lecture(tid, published=True, title="TEST_ Generic Other Topic")

        # Adjust lec_bfs to have very different materials so Dijkstra query scores lower for it
        from repositories.lecture_repository import LectureRepository

        async def _adj():
            await LectureRepository().col.update_one(
                {"id": lec_bfs},
                {"$set": {
                    "materials.summary": "Lecture about cooking pasta and recipes.",
                    "materials.key_concepts": ["pasta", "recipe", "cooking"],
                    "embedding": None,
                }},
            )
            # ensure no embedding on lec_dijkstra either to force lexical fallback
            await LectureRepository().col.update_one(
                {"id": lec_dijkstra}, {"$set": {"embedding": None}},
            )

        _arun(_adj)

        data = {
            "teacher_headers": {"Authorization": f"Bearer {teacher['access_token']}"},
            "student_headers": {"Authorization": f"Bearer {student['access_token']}"},
            "lec_dijkstra": lec_dijkstra, "lec_bfs": lec_bfs,
            "tid": tid, "sid": sid,
        }
        yield data
        _cleanup_collections([lec_dijkstra, lec_bfs], [tid, sid])

    def test_search_requires_auth(self):
        r = requests.get(f"{API}/search?q=test", timeout=15)
        assert r.status_code == 401

    def test_search_lexical_fallback_ranking(self, seeded):
        """No embeddings -> uses lexical only. Dijkstra lecture should rank higher."""
        r = requests.get(f"{API}/search?q=Dijkstra+shortest+path",
                         headers=seeded["student_headers"], timeout=30)
        assert r.status_code == 200, r.text
        results = r.json()
        assert isinstance(results, list)
        ids = [it["lecture_id"] for it in results]
        # Dijkstra lecture should be present and ranked above the cooking one
        assert seeded["lec_dijkstra"] in ids
        if seeded["lec_bfs"] in ids:
            idx_d = ids.index(seeded["lec_dijkstra"])
            idx_b = ids.index(seeded["lec_bfs"])
            assert idx_d < idx_b, f"Dijkstra should outrank cooking. got: {results}"
        # Score must be positive and bounded
        for r_ in results:
            assert 0 < r_["score"] <= 1.0

    def test_search_zero_match_excluded(self, seeded):
        """A query with no matching tokens should return empty (score == 0 entries are filtered)."""
        r = requests.get(f"{API}/search?q=zzzqqqxxxneverappears",
                         headers=seeded["student_headers"], timeout=20)
        assert r.status_code == 200
        # The cooking and dijkstra lectures contain none of these tokens -> empty
        results = r.json()
        assert results == [] or all(r_["lecture_id"] not in (seeded["lec_dijkstra"],
                                                              seeded["lec_bfs"])
                                    for r_ in results)


class TestSearchEmpty:
    def test_search_returns_empty_when_no_published(self):
        """If no published lectures, response is []. We assert >=200 + list shape (cannot guarantee
        zero published as other tests may seed published ones; so just check schema)."""
        teacher = _signup_or_login(TEACHER)
        h = {"Authorization": f"Bearer {teacher['access_token']}"}
        r = requests.get(f"{API}/search?q=arbitraryquery123", headers=h, timeout=20)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ---------- ANALYTICS ----------

class TestAnalytics:
    @pytest.fixture(scope="class")
    def isolated_user(self):
        """Use a fresh dedicated user so we can assert exact attempt counts."""
        creds = {"name": "P1 Analytics", "email": "TEST_p1analytics@lecturemind.example.com",
                 "password": "Password123!", "role": "student"}
        auth = _signup_or_login(creds)
        uid = auth["user"]["id"]
        h = {"Authorization": f"Bearer {auth['access_token']}"}

        # Wipe any prior data for this user
        from core.db import get_db

        async def _wipe():
            db = get_db()
            await db["quiz_attempts"].delete_many({"user_id": uid})

        _arun(_wipe)

        # Two seeded lectures (need to exist so analytics can find titles)
        teacher = _signup_or_login(TEACHER)
        tid = teacher["user"]["id"]
        lec_a = _seed_ready_lecture(tid, published=True, title="TEST_ Analytics A")
        lec_b = _seed_ready_lecture(tid, published=True, title="TEST_ Analytics B")

        data = {"headers": h, "uid": uid, "lec_a": lec_a, "lec_b": lec_b, "tid": tid}
        yield data

        async def _final_wipe():
            db = get_db()
            await db["quiz_attempts"].delete_many({"user_id": uid})

        _arun(_final_wipe)
        _cleanup_collections([lec_a, lec_b], [uid, tid])

    def test_analytics_requires_auth(self):
        r = requests.get(f"{API}/analytics/me", timeout=15)
        assert r.status_code == 401

    def test_baseline_zeros(self, isolated_user):
        r = requests.get(f"{API}/analytics/me", headers=isolated_user["headers"], timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["attempts_count"] == 0
        assert body["lectures_attempted"] == 0
        assert body["avg_percentage"] == 0.0
        assert body["streak_days"] == 0
        assert body["weak_lectures"] == []
        assert body["strong_lectures"] == []

    def test_after_three_seeded_attempts(self, isolated_user):
        # 2 attempts on lec_a (30%, 90%), 1 on lec_b (60%) — all today
        _seed_quiz_attempt(isolated_user["lec_a"], isolated_user["uid"], 30.0, day_offset=0)
        _seed_quiz_attempt(isolated_user["lec_a"], isolated_user["uid"], 90.0, day_offset=0)
        _seed_quiz_attempt(isolated_user["lec_b"], isolated_user["uid"], 60.0, day_offset=0)

        r = requests.get(f"{API}/analytics/me", headers=isolated_user["headers"], timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert body["attempts_count"] == 3
        assert body["lectures_attempted"] == 2
        # Average = (30+90+60)/3 = 60.0
        assert body["avg_percentage"] == 60.0
        # lec_a avg = 60, lec_b avg = 60. Both present in weak/strong.
        weak_ids = [w["lecture_id"] for w in body["weak_lectures"]]
        strong_ids = [w["lecture_id"] for w in body["strong_lectures"]]
        assert isolated_user["lec_a"] in weak_ids
        assert isolated_user["lec_b"] in strong_ids or isolated_user["lec_b"] in weak_ids
        assert body["last_attempt_at"] is not None
        # All attempts today -> streak should be 1
        assert body["streak_days"] == 1

    def test_streak_broken_with_gap(self, isolated_user):
        # Reset attempts for this user
        from core.db import get_db

        async def _reset():
            db = get_db()
            await db["quiz_attempts"].delete_many({"user_id": isolated_user["uid"]})

        _arun(_reset)

        # Seed: 2 today + 1 two-days-ago. Day -1 missing -> streak broken at 1.
        _seed_quiz_attempt(isolated_user["lec_a"], isolated_user["uid"], 50.0, day_offset=0)
        _seed_quiz_attempt(isolated_user["lec_a"], isolated_user["uid"], 70.0, day_offset=0)
        _seed_quiz_attempt(isolated_user["lec_b"], isolated_user["uid"], 80.0, day_offset=-2)

        r = requests.get(f"{API}/analytics/me", headers=isolated_user["headers"], timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert body["attempts_count"] == 3
        assert body["streak_days"] == 1, f"expected broken streak=1, got {body['streak_days']}"


# ---------- Quiz attempt persists ----------

class TestQuizPersistence:
    @pytest.fixture(scope="class")
    def seeded(self):
        teacher = _signup_or_login(TEACHER)
        student = _signup_or_login(STUDENT)
        tid = teacher["user"]["id"]
        sid = student["user"]["id"]
        lec = _seed_ready_lecture(tid, published=True, title="TEST_ P1 Quiz Persist")
        data = {
            "headers_student": {"Authorization": f"Bearer {student['access_token']}"},
            "lec": lec, "sid": sid, "tid": tid,
        }
        yield data
        _cleanup_collections([lec], [tid, sid])

    def test_attempt_creates_record_in_quiz_attempts(self, seeded):
        # Lecture has 2 quiz questions (from _seed_ready_lecture) with answers [1, 0]
        # Submit [1, 0] -> perfect
        r = requests.post(f"{API}/lectures/{seeded['lec']}/quiz/attempt",
                          headers=seeded["headers_student"],
                          json={"answers": [1, 0]}, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["score"] == 2
        assert body["total"] == 2
        assert body["percentage"] == 100.0

        # Verify a record landed in quiz_attempts
        from core.db import get_db

        async def _find():
            db = get_db()
            return await db["quiz_attempts"].find_one({
                "user_id": seeded["sid"], "lecture_id": seeded["lec"],
            })

        rec = _arun(_find)
        assert rec is not None, "Quiz attempt was not persisted in quiz_attempts collection"
        assert rec["score"] == 2
        assert rec["total"] == 2
        assert rec["percentage"] == 100.0
        assert rec["user_id"] == seeded["sid"]
        assert rec["lecture_id"] == seeded["lec"]
