"""End-to-end backend test suite for LectureMind AI.

Covers:
  - health
  - auth (signup/login/me, EmailStr, duplicate=409)
  - lectures (upload teacher OK / student 403, list mine, published, detail RBAC,
    publish error path, delete, quiz scoring, audio streaming)
  - background AI error path (GEMINI_API_KEY empty -> status=error)
"""
import io
import os
import struct
import time

import pytest
import requests

# Read REACT_APP_BACKEND_URL from frontend/.env (single source of truth).
def _load_backend_url() -> str:
    if os.environ.get("REACT_APP_BACKEND_URL"):
        return os.environ["REACT_APP_BACKEND_URL"]
    try:
        with open("/app/frontend/.env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    raise RuntimeError("REACT_APP_BACKEND_URL not found")


BASE_URL = _load_backend_url().rstrip("/")
API = f"{BASE_URL}/api"

TEACHER = {"email": "teacher@lecturemind.example.com", "password": "Password123!", "name": "Teacher One", "role": "teacher"}
STUDENT = {"email": "student@lecturemind.example.com", "password": "Password123!", "name": "Student One", "role": "student"}


# ---------- helpers ----------

def _signup_or_login(creds: dict) -> dict:
    """Try signup; fall back to login on 409."""
    r = requests.post(f"{API}/auth/signup", json=creds, timeout=30)
    if r.status_code == 201:
        return r.json()
    if r.status_code == 409:
        r2 = requests.post(
            f"{API}/auth/login",
            json={"email": creds["email"], "password": creds["password"]},
            timeout=30,
        )
        assert r2.status_code == 200, f"login fallback failed: {r2.status_code} {r2.text}"
        return r2.json()
    pytest.fail(f"signup unexpected status {r.status_code}: {r.text}")


def _wav_bytes(seconds: float = 0.2, sample_rate: int = 8000) -> bytes:
    """Tiny silent WAV (PCM 16-bit mono)."""
    n = int(seconds * sample_rate)
    data = b"\x00\x00" * n
    # RIFF header
    return (
        b"RIFF"
        + struct.pack("<I", 36 + len(data))
        + b"WAVE"
        + b"fmt "
        + struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16)
        + b"data"
        + struct.pack("<I", len(data))
        + data
    )


# ---------- fixtures ----------

@pytest.fixture(scope="session")
def teacher_auth() -> dict:
    return _signup_or_login(TEACHER)


@pytest.fixture(scope="session")
def student_auth() -> dict:
    return _signup_or_login(STUDENT)


@pytest.fixture(scope="session")
def teacher_token(teacher_auth) -> str:
    return teacher_auth["access_token"]


@pytest.fixture(scope="session")
def student_token(student_auth) -> str:
    return student_auth["access_token"]


@pytest.fixture
def teacher_headers(teacher_token):
    return {"Authorization": f"Bearer {teacher_token}"}


@pytest.fixture
def student_headers(student_token):
    return {"Authorization": f"Bearer {student_token}"}


# ---------- health ----------

class TestHealth:
    def test_health_ok(self):
        r = requests.get(f"{API}/health", timeout=15)
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    def test_root_ok(self):
        r = requests.get(f"{API}/", timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert body.get("status") == "ok"


# ---------- auth ----------

class TestAuth:
    def test_signup_or_existing_teacher(self, teacher_auth):
        assert "access_token" in teacher_auth
        assert isinstance(teacher_auth["access_token"], str) and teacher_auth["access_token"]
        assert teacher_auth["token_type"].lower() == "bearer"
        user = teacher_auth["user"]
        assert user["email"] == TEACHER["email"]
        assert user["role"] == "teacher"
        assert "id" in user and user["id"]

    def test_signup_or_existing_student(self, student_auth):
        assert student_auth["user"]["role"] == "student"
        assert student_auth["user"]["email"] == STUDENT["email"]

    def test_signup_duplicate_returns_409(self, teacher_auth):
        r = requests.post(f"{API}/auth/signup", json=TEACHER, timeout=20)
        assert r.status_code == 409
        assert "already" in r.json().get("detail", "").lower()

    def test_signup_invalid_email(self):
        r = requests.post(
            f"{API}/auth/signup",
            json={"name": "X", "email": "not-an-email", "password": "Password123!", "role": "student"},
            timeout=15,
        )
        assert r.status_code == 422

    def test_signup_short_password(self):
        r = requests.post(
            f"{API}/auth/signup",
            json={"name": "X", "email": "shortpw@example.com", "password": "abc", "role": "student"},
            timeout=15,
        )
        assert r.status_code == 422

    def test_login_success(self):
        r = requests.post(
            f"{API}/auth/login",
            json={"email": TEACHER["email"], "password": TEACHER["password"]},
            timeout=20,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["user"]["role"] == "teacher"
        assert body["access_token"]

    def test_login_wrong_password(self):
        r = requests.post(
            f"{API}/auth/login",
            json={"email": TEACHER["email"], "password": "WrongPass!1"},
            timeout=20,
        )
        assert r.status_code == 401

    def test_login_unknown_email(self):
        r = requests.post(
            f"{API}/auth/login",
            json={"email": "nobody@nowhere.example.com", "password": "Password123!"},
            timeout=20,
        )
        assert r.status_code == 401

    def test_me_with_token(self, teacher_headers):
        r = requests.get(f"{API}/auth/me", headers=teacher_headers, timeout=15)
        assert r.status_code == 200
        body = r.json()
        assert body["email"] == TEACHER["email"]
        assert body["role"] == "teacher"

    def test_me_without_token(self):
        r = requests.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 401

    def test_me_with_bad_token(self):
        r = requests.get(f"{API}/auth/me", headers={"Authorization": "Bearer not.a.jwt"}, timeout=15)
        assert r.status_code == 401


# ---------- lectures ----------

class TestLectures:
    @pytest.fixture(scope="class")
    def uploaded_lecture(self, request):
        """Class-scoped: upload once and reuse. Cleanup at teardown."""
        # local session-equivalent: get teacher token
        auth = _signup_or_login(TEACHER)
        token = auth["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        files = {"file": ("test_lecture.wav", _wav_bytes(0.2), "audio/wav")}
        data = {"title": "TEST_ Lecture Intro", "subject": "TEST_Science", "semester": "Fall-TEST"}
        r = requests.post(f"{API}/lectures", headers=headers, files=files, data=data, timeout=60)
        assert r.status_code == 202, f"upload failed: {r.status_code} {r.text}"
        lecture = r.json()
        assert lecture["status"] == "uploaded"
        assert lecture["teacher_id"] == auth["user"]["id"]
        assert lecture["title"] == "TEST_ Lecture Intro"
        assert lecture["audio_mime"] in ("audio/wav", "audio/x-wav", "audio/wave")

        yield {"lecture": lecture, "token": token, "headers": headers}

        # Teardown
        try:
            requests.delete(f"{API}/lectures/{lecture['id']}", headers=headers, timeout=15)
        except Exception:
            pass

    # ---- upload ----
    def test_upload_requires_teacher_role(self, student_headers):
        files = {"file": ("x.wav", _wav_bytes(0.1), "audio/wav")}
        data = {"title": "should not work"}
        r = requests.post(f"{API}/lectures", headers=student_headers, files=files, data=data, timeout=30)
        assert r.status_code == 403

    def test_upload_requires_auth(self):
        files = {"file": ("x.wav", _wav_bytes(0.1), "audio/wav")}
        data = {"title": "no auth"}
        r = requests.post(f"{API}/lectures", files=files, data=data, timeout=30)
        assert r.status_code == 401

    def test_upload_unsupported_mime(self, teacher_headers):
        files = {"file": ("x.txt", b"not audio", "text/plain")}
        data = {"title": "bad mime"}
        r = requests.post(f"{API}/lectures", headers=teacher_headers, files=files, data=data, timeout=30)
        assert r.status_code == 400

    def test_upload_teacher_success(self, uploaded_lecture):
        lec = uploaded_lecture["lecture"]
        assert lec["id"]
        assert lec["audio_object_key"].startswith(f"lectures/{lec['id']}/")

    # ---- list mine ----
    def test_list_mine_teacher(self, uploaded_lecture, teacher_headers):
        r = requests.get(f"{API}/lectures/mine", headers=teacher_headers, timeout=20)
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list)
        ids = [it["id"] for it in body]
        assert uploaded_lecture["lecture"]["id"] in ids

    def test_list_mine_student_forbidden(self, student_headers):
        r = requests.get(f"{API}/lectures/mine", headers=student_headers, timeout=15)
        assert r.status_code == 403

    # ---- get detail / RBAC ----
    def test_get_lecture_owner_teacher(self, uploaded_lecture, teacher_headers):
        lid = uploaded_lecture["lecture"]["id"]
        r = requests.get(f"{API}/lectures/{lid}", headers=teacher_headers, timeout=20)
        assert r.status_code == 200
        body = r.json()
        assert body["id"] == lid

    def test_get_unpublished_lecture_student_forbidden(self, uploaded_lecture, student_headers):
        lid = uploaded_lecture["lecture"]["id"]
        r = requests.get(f"{API}/lectures/{lid}", headers=student_headers, timeout=15)
        assert r.status_code == 403

    def test_get_lecture_not_found(self, teacher_headers):
        r = requests.get(f"{API}/lectures/does-not-exist-xyz", headers=teacher_headers, timeout=15)
        assert r.status_code == 404

    # ---- background AI error path ----
    def test_background_task_marks_error_without_gemini_key(self, uploaded_lecture, teacher_headers):
        """With GEMINI_API_KEY empty, background task should set status=error+error_message."""
        lid = uploaded_lecture["lecture"]["id"]
        deadline = time.time() + 30
        last_status = None
        last_err = None
        while time.time() < deadline:
            r = requests.get(f"{API}/lectures/{lid}", headers=teacher_headers, timeout=15)
            assert r.status_code == 200
            body = r.json()
            last_status = body["status"]
            last_err = body.get("error_message")
            if last_status == "error":
                break
            time.sleep(1.5)
        assert last_status == "error", f"expected status=error, got {last_status} (err={last_err})"
        assert last_err and isinstance(last_err, str) and len(last_err) > 0

    # ---- publish error path ----
    def test_publish_when_not_ready_returns_400(self, uploaded_lecture, teacher_headers):
        lid = uploaded_lecture["lecture"]["id"]
        r = requests.post(f"{API}/lectures/{lid}/publish", headers=teacher_headers, timeout=20)
        assert r.status_code == 400

    def test_publish_student_forbidden(self, uploaded_lecture, student_headers):
        lid = uploaded_lecture["lecture"]["id"]
        r = requests.post(f"{API}/lectures/{lid}/publish", headers=student_headers, timeout=15)
        assert r.status_code == 403

    def test_publish_not_owner_returns_404(self, uploaded_lecture):
        # Create a second teacher and try to publish someone else's lecture.
        second = {
            "name": "Teacher Two",
            "email": "TEST_teacher2@lecturemind.example.com",
            "password": "Password123!",
            "role": "teacher",
        }
        auth = _signup_or_login(second)
        headers = {"Authorization": f"Bearer {auth['access_token']}"}
        lid = uploaded_lecture["lecture"]["id"]
        r = requests.post(f"{API}/lectures/{lid}/publish", headers=headers, timeout=15)
        assert r.status_code == 404

    # ---- published listing ----
    def test_published_listing_visible_to_student(self, student_headers):
        r = requests.get(f"{API}/lectures/published", headers=student_headers, timeout=20)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_published_requires_auth(self):
        r = requests.get(f"{API}/lectures/published", timeout=15)
        assert r.status_code == 401

    # ---- audio streaming ----
    def test_audio_stream_teacher_owner(self, uploaded_lecture, teacher_headers):
        lid = uploaded_lecture["lecture"]["id"]
        r = requests.get(f"{API}/lectures/{lid}/audio", headers=teacher_headers, timeout=20)
        assert r.status_code == 200
        assert "audio" in r.headers.get("content-type", "")
        assert len(r.content) > 40  # at least RIFF header

    def test_audio_stream_student_forbidden_when_unpublished(self, uploaded_lecture, student_headers):
        lid = uploaded_lecture["lecture"]["id"]
        r = requests.get(f"{API}/lectures/{lid}/audio", headers=student_headers, timeout=15)
        assert r.status_code == 403

    # ---- quiz attempt logic ----
    def test_quiz_attempt_no_quiz_returns_400(self, uploaded_lecture, teacher_headers):
        """Lecture is in error state with no quiz; attempt should be 400."""
        lid = uploaded_lecture["lecture"]["id"]
        r = requests.post(
            f"{API}/lectures/{lid}/quiz/attempt",
            headers=teacher_headers,
            json={"answers": [0]},
            timeout=15,
        )
        assert r.status_code == 400


# ---------- isolated quiz scoring via seeded materials ----------

class TestQuizScoring:
    """Seed materials directly through Mongo so we can validate scoring math
    without needing the AI provider."""

    @pytest.fixture(scope="class")
    def seeded_lecture(self):
        """Upload a lecture as teacher, then directly mutate Mongo to attach a quiz + status=ready."""
        import asyncio
        import sys
        sys.path.insert(0, "/app/backend")
        from repositories.lecture_repository import LectureRepository  # noqa

        auth = _signup_or_login(TEACHER)
        token = auth["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        files = {"file": ("q.wav", _wav_bytes(0.1), "audio/wav")}
        data = {"title": "TEST_ Quiz Seed"}
        r = requests.post(f"{API}/lectures", headers=headers, files=files, data=data, timeout=30)
        assert r.status_code == 202
        lecture_id = r.json()["id"]

        async def seed():
            repo = LectureRepository()
            quiz = [
                {"question": "1+1?", "options": ["1", "2", "3", "4"], "answer_index": 1, "explanation": ""},
                {"question": "Color of sky?", "options": ["red", "blue", "green"], "answer_index": 1, "explanation": ""},
                {"question": "2*3?", "options": ["5", "6", "7"], "answer_index": 1, "explanation": ""},
            ]
            await repo.col.update_one(
                {"id": lecture_id},
                {"$set": {
                    "materials": {
                        "summary": "seeded",
                        "smart_notes": [],
                        "key_concepts": [],
                        "quiz": quiz,
                        "flashcards": [],
                    },
                    "status": "ready",
                    "error_message": None,
                }},
            )

        asyncio.run(seed())

        yield {"id": lecture_id, "headers": headers, "token": token}

        # Teardown
        try:
            requests.delete(f"{API}/lectures/{lecture_id}", headers=headers, timeout=15)
        except Exception:
            pass

    def test_quiz_attempt_perfect_score(self, seeded_lecture):
        r = requests.post(
            f"{API}/lectures/{seeded_lecture['id']}/quiz/attempt",
            headers=seeded_lecture["headers"],
            json={"answers": [1, 1, 1]},
            timeout=15,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["score"] == 3
        assert body["total"] == 3
        assert body["percentage"] == 100.0
        assert body["correct_answers"] == [1, 1, 1]
        assert body["user_answers"] == [1, 1, 1]

    def test_quiz_attempt_partial(self, seeded_lecture):
        r = requests.post(
            f"{API}/lectures/{seeded_lecture['id']}/quiz/attempt",
            headers=seeded_lecture["headers"],
            json={"answers": [1, 0, 1]},
            timeout=15,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["score"] == 2
        assert body["total"] == 3
        assert body["percentage"] == 66.7

    def test_quiz_attempt_mismatch_count_returns_400(self, seeded_lecture):
        r = requests.post(
            f"{API}/lectures/{seeded_lecture['id']}/quiz/attempt",
            headers=seeded_lecture["headers"],
            json={"answers": [1]},
            timeout=15,
        )
        assert r.status_code == 400

    def test_publish_ready_lecture_succeeds(self, seeded_lecture):
        """The 'ready' lecture should publish successfully and show in /published."""
        r = requests.post(
            f"{API}/lectures/{seeded_lecture['id']}/publish",
            headers=seeded_lecture["headers"],
            timeout=20,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["published"] is True
        assert body["status"] == "ready"

        # Now visible in /published
        r2 = requests.get(f"{API}/lectures/published", headers=seeded_lecture["headers"], timeout=15)
        assert r2.status_code == 200
        ids = [it["id"] for it in r2.json()]
        assert seeded_lecture["id"] in ids


# ---------- delete ----------

class TestDelete:
    def test_teacher_can_delete_own_lecture(self, teacher_headers):
        files = {"file": ("del.wav", _wav_bytes(0.1), "audio/wav")}
        data = {"title": "TEST_ to delete"}
        r = requests.post(f"{API}/lectures", headers=teacher_headers, files=files, data=data, timeout=30)
        assert r.status_code == 202
        lid = r.json()["id"]

        r = requests.delete(f"{API}/lectures/{lid}", headers=teacher_headers, timeout=15)
        assert r.status_code == 204

        # verify gone
        r2 = requests.get(f"{API}/lectures/{lid}", headers=teacher_headers, timeout=15)
        assert r2.status_code == 404

    def test_student_cannot_delete(self, student_headers):
        r = requests.delete(f"{API}/lectures/any-id", headers=student_headers, timeout=15)
        assert r.status_code == 403
