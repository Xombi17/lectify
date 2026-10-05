"""Tests for deterministic demo seed script."""
import os
import sys
from io import StringIO
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from core.sql_db import _engine, session_maker
from models.orm import (
    Base,
    BranchORM,
    ClassORM,
    DivisionORM,
    InstitutionORM,
    SemesterORM,
    StudentEnrollmentORM,
    SubjectORM,
    TeacherAssignmentORM,
    UserORM,
    YearORM,
)
from scripts.seed_demo import (
    ADMIN_EMAIL,
    INSTITUTION_CODE,
    STUDENT_EMAIL,
    TEACHER_EMAIL,
    main,
    seed,
)
from server import app


from httpx import ASGITransport, AsyncClient

@pytest.mark.asyncio
async def test_seed_demo_idempotent():
    """First run creates entities; second run creates 0 new entities."""
    maker = session_maker()
    passwords = {
        "admin": "AdminPassword123!",
        "teacher": "TeacherPassword123!",
        "student": "StudentPassword123!",
    }

    # 1. First run
    async with maker() as session:
        counts1 = await seed(session, passwords)
        assert counts1["created"] == 12  # 1 inst, 1 yr, 1 br, 1 sem, 1 div, 1 sub, 1 cls, 3 users, 1 enr, 1 assign

    # Capture row counts across all models
    models = [
        InstitutionORM,
        YearORM,
        BranchORM,
        SemesterORM,
        DivisionORM,
        SubjectORM,
        ClassORM,
        UserORM,
        StudentEnrollmentORM,
        TeacherAssignmentORM,
    ]
    counts_before = {}
    async with maker() as session:
        for m in models:
            res = await session.execute(select(func.count()).select_from(m))
            counts_before[m.__name__] = res.scalar()

    # 2. Second run
    async with maker() as session:
        counts2 = await seed(session, passwords)
        assert counts2["created"] == 0
        assert counts2["existing"] > 0

    # Verify no row count changed
    async with maker() as session:
        for m in models:
            res = await session.execute(select(func.count()).select_from(m))
            assert res.scalar() == counts_before[m.__name__], f"Row count changed for {m.__name__}"


@pytest.mark.asyncio
async def test_seeded_student_can_login():
    """Seeded student can authenticate via the real /api/auth/login endpoint."""
    maker = session_maker()
    student_pw = "StudentValidPass123!"
    passwords = {
        "admin": "AdminValidPass123!",
        "teacher": "TeacherValidPass123!",
        "student": student_pw,
    }
    async with maker() as session:
        await seed(session, passwords, reset_passwords=True)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/api/auth/login",
            json={"email": STUDENT_EMAIL, "password": student_pw},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["email"] == STUDENT_EMAIL
    assert data["user"]["role"] == "student"


def test_main_missing_env_non_tty(monkeypatch):
    """Non-tty missing env variables causes exit 2 and prints missing var names."""
    monkeypatch.delenv("DEMO_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("DEMO_TEACHER_PASSWORD", raising=False)
    monkeypatch.delenv("DEMO_STUDENT_PASSWORD", raising=False)

    stderr = StringIO()
    with patch("sys.stdin.isatty", return_value=False), patch("sys.stderr", stderr):
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code == 2

    err = stderr.getvalue()
    assert "Missing required password environment variable(s)" in err
    assert "DEMO_ADMIN_PASSWORD" in err
    assert "DEMO_TEACHER_PASSWORD" in err
    assert "DEMO_STUDENT_PASSWORD" in err


@pytest.mark.asyncio
async def test_reset_passwords_flag():
    """Existing user password is only updated if reset_passwords=True."""
    maker = session_maker()
    pw1 = "InitialPass123!"
    pw2 = "UpdatedPass123!"

    async with maker() as session:
        await seed(session, {"admin": pw1, "teacher": pw1, "student": pw1}, reset_passwords=True)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/auth/login", json={"email": STUDENT_EMAIL, "password": pw1})
        assert resp.status_code == 200

        # Run seed again without reset_passwords with new password
        async with maker() as session:
            await seed(session, {"admin": pw2, "teacher": pw2, "student": pw2}, reset_passwords=False)

        # Old password still works
        resp = await ac.post("/api/auth/login", json={"email": STUDENT_EMAIL, "password": pw1})
        assert resp.status_code == 200

        # Run seed with reset_passwords=True
        async with maker() as session:
            await seed(session, {"admin": pw2, "teacher": pw2, "student": pw2}, reset_passwords=True)

        # New password now works
        resp = await ac.post("/api/auth/login", json={"email": STUDENT_EMAIL, "password": pw2})
        assert resp.status_code == 200
