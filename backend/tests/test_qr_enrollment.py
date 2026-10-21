"""QR generation + enrollment hardening: storage key prefix, public URL base, role and ownership checks."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from core.deps import get_current_user
from core.security import create_enrollment_token
from models.user import UserPublic
from server import app

NOW = datetime.now(timezone.utc)


def _user(role, uid):
    return UserPublic(id=uid, name=uid, email=f"{uid}@x.edu", role=role, created_at=NOW)


def _request(headers: dict, scheme="http") -> Request:
    return Request({"type": "http", "scheme": scheme, "method": "POST", "path": "/",
                    "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
                    "query_string": b"", "server": ("api", 8000)})


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


# ── public URL base ───────────────────────────────────────────────────

def test_base_url_prefers_explicit_app_url():
    from routes import qr
    with patch.object(qr.settings, "APP_URL", "https://lectify.example.edu/"):
        assert qr._app_base_url(_request({"origin": "http://evil.test"})) == "https://lectify.example.edu"


def test_base_url_falls_back_to_browser_origin_then_host():
    from routes import qr
    with patch.object(qr.settings, "APP_URL", ""):
        assert qr._app_base_url(_request({"origin": "http://alb.example.com/"})) == "http://alb.example.com"
        assert qr._app_base_url(
            _request({"host": "alb.example.com", "x-forwarded-proto": "https"})
        ) == "https://alb.example.com"
        assert qr._app_base_url(_request({})) == "http://localhost:3000"


# ── generation: key lives under classes/ and URL is not localhost ─────

@pytest.mark.asyncio
async def test_qr_is_stored_under_classes_prefix_and_encodes_base_url():
    from routes import qr

    storage = MagicMock()
    storage.save = AsyncMock()
    repo = MagicMock()
    repo.new_id.return_value = "qr1"
    repo.create = AsyncMock(side_effect=lambda row: row)
    seen = {}
    real_make = qr.qrcode.make

    def spy(data, **kw):
        seen["url"] = data
        return real_make(data, **kw)

    with patch.object(qr, "get_storage", return_value=storage), \
         patch.object(qr, "QRCodeRepository", return_value=repo), \
         patch.object(qr.qrcode, "make", side_effect=spy):
        out = await qr._create_qr_internal("cls_9", "usr_1", "http://alb.example.com")

    key = storage.save.await_args.args[0]
    assert key == "classes/cls_9/qr/qr1.svg"  # inside the API role's classes/* write scope
    assert seen["url"].startswith("http://alb.example.com/enroll?token=")
    assert out.class_id == "cls_9"


# ── authorization ─────────────────────────────────────────────────────

@patch("routes.qr.ClassRepository")
@patch("routes.qr.TeacherAssignmentRepository")
def test_teacher_cannot_regenerate_qr_for_unassigned_class(mock_ta, mock_cls, client):
    mock_cls.return_value.get_by_id = AsyncMock(return_value=MagicMock())
    mock_ta.return_value.list_for_teacher = AsyncMock(return_value=[])
    app.dependency_overrides[get_current_user] = lambda: _user("teacher", "t1")
    assert client.post("/api/qr/classes/cls_1/regenerate").status_code == 403


@patch("routes.qr.ClassRepository")
def test_regenerate_unknown_class_404(mock_cls, client):
    mock_cls.return_value.get_by_id = AsyncMock(return_value=None)
    app.dependency_overrides[get_current_user] = lambda: _user("admin", "a1")
    assert client.post("/api/qr/classes/ghost/regenerate").status_code == 404


def test_only_students_can_enroll(client):
    token = create_enrollment_token("cls_1", "secret")
    for role in ("teacher", "admin"):
        app.dependency_overrides[get_current_user] = lambda r=role: _user(r, r)
        assert client.post(f"/api/qr/enroll/{token}").status_code == 403


@patch("routes.qr.ClassRepository")
@patch("routes.qr.QRCodeRepository")
def test_preview_returns_class_name(mock_qr, mock_cls, client):
    token = create_enrollment_token("cls_1", "secret")
    qr_row = MagicMock(token_secret="secret", is_active=True, id="qr1")
    mock_qr.return_value.get_active_for_class = AsyncMock(return_value=qr_row)
    mock_qr.return_value.increment_scan = AsyncMock()
    cls = MagicMock()
    cls.name = "OS · COMPS A"
    mock_cls.return_value.get_by_id = AsyncMock(return_value=cls)
    r = client.get(f"/api/qr/enroll/{token}")
    assert r.status_code == 200
    assert r.json()["class_name"] == "OS · COMPS A"
    assert r.json()["redirect_url"] == f"/enroll?token={token}"
