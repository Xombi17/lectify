"""Account management: student-only signup, change/reset password, profile, admin user management."""
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from core.deps import extract_token_data, get_current_user
from core.security import create_access_token, hash_password, verify_password
from models.user import UserDB, UserPublic
from server import app

NOW = datetime.now(timezone.utc)


class FakeUsers:
    """In-memory stand-in for UserRepository (shared across the routes under test)."""

    def __init__(self):
        self.rows: dict[str, UserDB] = {}
        self._n = 0

    def add(self, uid, role, email, password="password1", name=None):
        self.rows[uid] = UserDB(id=uid, name=name or uid, email=email, role=role,
                                password_hash=hash_password(password), created_at=NOW)

    def __call__(self):
        return self

    def new_id(self):
        self._n += 1
        return f"new_{self._n}"

    async def create(self, user):
        self.rows[user.id] = user
        return user

    async def get_by_id(self, uid):
        return self.rows.get(uid)

    async def get_by_email(self, email):
        return next((u for u in self.rows.values() if u.email == email), None)

    async def update_name(self, uid, name):
        if uid not in self.rows:
            return None
        self.rows[uid] = self.rows[uid].model_copy(update={"name": name})
        return self.rows[uid]

    async def update_password_hash(self, uid, h):
        if uid not in self.rows:
            return False
        self.rows[uid] = self.rows[uid].model_copy(update={"password_hash": h})
        return True

    async def search(self, role=None, q=None, limit=50, offset=0):
        out = [u for u in self.rows.values()
               if (not role or u.role == role) and (not q or q.lower() in (u.name + u.email).lower())]
        return out[offset:offset + limit]


def pub(u: UserDB) -> UserPublic:
    return UserPublic(**u.model_dump(exclude={"password_hash"}))


async def _noop(*_a, **_k):
    return None


@pytest.fixture
def users():
    f = FakeUsers()
    f.add("adm", "admin", "adm@x.edu")
    f.add("stu", "student", "stu@x.edu", password="oldpassword")
    f.add("tea", "teacher", "tea@x.edu", name="Prof T")
    with patch("routes.auth.UserRepository", f), patch("routes.admin.UserRepository", f), \
         patch("core.deps.UserRepository", f), patch("routes.auth._blacklist", new=_noop), \
         patch("routes.admin.log_audit", new=_noop):
        yield f
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


def as_user(f: FakeUsers, uid: str):
    app.dependency_overrides[get_current_user] = lambda: pub(f.rows[uid])
    app.dependency_overrides[extract_token_data] = lambda: {"jti": "j", "exp": 9999999999}


# ── signup ────────────────────────────────────────────────────────────

def test_public_signup_is_student_only(users, client):
    for role in ("teacher", "admin"):
        r = client.post("/api/auth/signup", json={"name": "X", "email": f"{role}@x.edu",
                                                  "password": "longenough", "role": role})
        assert r.status_code == 403
    ok = client.post("/api/auth/signup", json={"name": "S", "email": "new@x.edu", "password": "longenough"})
    assert ok.status_code == 201 and ok.json()["user"]["role"] == "student"


def test_password_minimum_length(users, client):
    r = client.post("/api/auth/signup", json={"name": "S", "email": "s2@x.edu", "password": "short7!"})
    assert r.status_code == 422


# ── profile + change password ─────────────────────────────────────────

def test_update_profile_name(users, client):
    as_user(users, "stu")
    r = client.patch("/api/auth/me", json={"name": "  New Name  "})
    assert r.status_code == 200 and r.json()["name"] == "New Name"
    assert users.rows["stu"].name == "New Name"


def test_change_password(users, client):
    as_user(users, "stu")
    bad = client.post("/api/auth/change-password", json={"current_password": "nope", "new_password": "brandnew123"})
    assert bad.status_code == 400
    same = client.post("/api/auth/change-password", json={"current_password": "oldpassword", "new_password": "oldpassword"})
    assert same.status_code == 400
    ok = client.post("/api/auth/change-password", json={"current_password": "oldpassword", "new_password": "brandnew123"})
    assert ok.status_code == 200 and ok.json()["access_token"]
    assert verify_password("brandnew123", users.rows["stu"].password_hash)


# ── admin-issued reset link ───────────────────────────────────────────

def test_reset_link_flow_is_single_use(users, client):
    as_user(users, "adm")
    link = client.post("/api/admin/users/stu/reset-link")
    assert link.status_code == 200 and link.json()["expires_in_minutes"] == 30
    token = link.json()["reset_path"].split("token=")[1]

    app.dependency_overrides.clear()  # the reset call is unauthenticated
    done = client.post("/api/auth/reset-password", json={"token": token, "new_password": "afterreset99"})
    assert done.status_code == 204
    assert verify_password("afterreset99", users.rows["stu"].password_hash)

    again = client.post("/api/auth/reset-password", json={"token": token, "new_password": "another12345"})
    assert again.status_code == 400  # link died when the password changed


def test_reset_token_cannot_authenticate(users, client):
    as_user(users, "adm")
    token = client.post("/api/admin/users/stu/reset-link").json()["reset_path"].split("token=")[1]
    app.dependency_overrides.clear()
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_garbage_reset_token_rejected(users, client):
    r = client.post("/api/auth/reset-password", json={"token": "nonsense", "new_password": "longenough1"})
    assert r.status_code == 400
    login_token = create_access_token(subject="stu", role="student")
    r2 = client.post("/api/auth/reset-password", json={"token": login_token, "new_password": "longenough1"})
    assert r2.status_code == 400  # an access token is not a reset token


# ── admin user management ─────────────────────────────────────────────

def test_admin_creates_teacher_and_lists(users, client):
    as_user(users, "adm")
    made = client.post("/api/admin/users", json={"name": "Dr New", "email": "New@X.edu",
                                                 "password": "temp-pass-1", "role": "teacher"})
    assert made.status_code == 201 and made.json()["email"] == "new@x.edu" and made.json()["role"] == "teacher"
    assert "password_hash" not in made.json()
    dup = client.post("/api/admin/users", json={"name": "Dup", "email": "new@x.edu", "password": "temp-pass-1"})
    assert dup.status_code == 409
    teachers = client.get("/api/admin/users", params={"role": "teacher"}).json()
    assert {t["email"] for t in teachers} == {"tea@x.edu", "new@x.edu"}
    assert [t["email"] for t in client.get("/api/admin/users", params={"q": "prof"}).json()] == ["tea@x.edu"]


def test_non_admin_cannot_manage_users(users, client):
    as_user(users, "tea")
    assert client.get("/api/admin/users").status_code == 403
    assert client.post("/api/admin/users", json={"name": "X", "email": "x@x.edu", "password": "longenough1"}).status_code == 403
    assert client.post("/api/admin/users/stu/reset-link").status_code == 403


def test_reset_link_for_unknown_user_404(users, client):
    as_user(users, "adm")
    assert client.post("/api/admin/users/ghost/reset-link").status_code == 404
