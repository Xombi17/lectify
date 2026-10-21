"""Admin teacher-assignment flow: list assignable teachers and reject invalid teacher ids."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from core.deps import get_current_user
from models.academic import TeacherAssignmentDB
from models.user import UserDB, UserPublic
from server import app

NOW = datetime.now(timezone.utc)


def _user(role, uid):
    return UserPublic(id=uid, name=uid, email=f"{uid}@x.edu", role=role, created_at=NOW)


def _db_user(role, uid, name):
    return UserDB(id=uid, name=name, email=f"{uid}@x.edu", role=role, password_hash="x", created_at=NOW)


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


@patch("routes.enrollment.UserRepository")
def test_admin_lists_teachers_without_secrets(mock_users, client):
    mock_users.return_value.list_by_role = AsyncMock(return_value=[_db_user("teacher", "t1", "Prof A")])
    app.dependency_overrides[get_current_user] = lambda: _user("admin", "adm")
    res = client.get("/api/enrollment/teachers")
    assert res.status_code == 200
    assert res.json() == [{"id": "t1", "name": "Prof A", "email": "t1@x.edu"}]
    mock_users.return_value.list_by_role.assert_awaited_once_with("teacher")


@patch("routes.enrollment.UserRepository")
def test_non_admin_cannot_list_teachers(mock_users, client):
    app.dependency_overrides[get_current_user] = lambda: _user("student", "stu")
    assert client.get("/api/enrollment/teachers").status_code == 403


@patch("routes.enrollment.TeacherAssignmentRepository")
@patch("routes.enrollment.UserRepository")
def test_assign_rejects_unknown_or_non_teacher(mock_users, mock_ta, client):
    app.dependency_overrides[get_current_user] = lambda: _user("admin", "adm")
    for found in (None, _db_user("student", "s1", "Stu")):
        mock_users.return_value.get_by_id = AsyncMock(return_value=found)
        res = client.post("/api/enrollment/assignments", json={"class_id": "c1", "teacher_id": "x"})
        assert res.status_code == 400
    mock_ta.return_value.create.assert_not_called()


@patch("routes.enrollment.TeacherAssignmentRepository")
@patch("routes.enrollment.UserRepository")
def test_assign_valid_teacher(mock_users, mock_ta, client):
    app.dependency_overrides[get_current_user] = lambda: _user("admin", "adm")
    mock_users.return_value.get_by_id = AsyncMock(return_value=_db_user("teacher", "t1", "Prof A"))
    ta = mock_ta.return_value
    ta.find_existing = AsyncMock(return_value=None)
    ta.new_id.return_value = "ta1"
    ta.create = AsyncMock(side_effect=lambda a: a)
    res = client.post("/api/enrollment/assignments", json={"class_id": "c1", "teacher_id": "t1"})
    assert res.status_code == 201, res.text
    assert res.json()["teacher_id"] == "t1" and res.json()["class_id"] == "c1"
