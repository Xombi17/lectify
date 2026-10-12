"""Shared pytest hooks for LectureMind backend tests."""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("ENV", "test")
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-prod")

# Live-HTTP suites need a deployed backend; set REACT_APP_BACKEND_URL to run them
if (
    not os.environ.get("REACT_APP_BACKEND_URL")
    and not Path("/app/frontend/.env").exists()
):
    collect_ignore = [
        "test_chunking.py",
        "test_study.py",
        "test_lecturemind_p1.py",
        "test_lecturemind_api.py",
    ]
else:
    collect_ignore = []

import pytest
import pytest_asyncio

# Add the backend directory to sys.path (works locally and in Docker)
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from core.sql_db import _engine as get_engine
from core.sql_db import session_maker
from models.orm import Base, LectureORM, UserORM


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_maker()() as session:
        # insert stub user and lecture to satisfy foreign keys
        session.add(
            UserORM(
                id="u1", name="U", email="u@e.com", role="student", password_hash=""
            )
        )
        session.add(
            LectureORM(
                id="l1",
                teacher_id="u1",
                title="T",
                audio_object_key="",
                audio_filename="",
                audio_mime="",
            )
        )
        session.add(
            LectureORM(
                id="dup-test",
                teacher_id="u1",
                title="T",
                audio_object_key="",
                audio_filename="",
                audio_mime="",
            )
        )
        session.add(
            LectureORM(
                id="lec-123",
                teacher_id="u1",
                title="T",
                audio_object_key="",
                audio_filename="",
                audio_mime="",
            )
        )
        session.add(
            LectureORM(
                id="lec-1",
                teacher_id="u1",
                title="T",
                audio_object_key="",
                audio_filename="",
                audio_mime="",
            )
        )
        session.add(
            LectureORM(
                id="integration-test-1",
                teacher_id="u1",
                title="T",
                audio_object_key="",
                audio_filename="",
                audio_mime="",
            )
        )
        session.add(
            LectureORM(
                id="idempotency-test-1",
                teacher_id="u1",
                title="T",
                audio_object_key="",
                audio_filename="",
                audio_mime="",
            )
        )
        await session.commit()

    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(autouse=True)
async def reset_queue():
    from core.queue_backend import reset_queue_backend

    reset_queue_backend()
    yield
    reset_queue_backend()


_PROVIDER_KEYS = ("DEEPGRAM_API_KEY", "NAGA_AI_API_KEY", "NIM_API_KEY")


@pytest.fixture(autouse=True)
def _no_live_provider_keys(monkeypatch):
    """backend/.env is loaded under pytest; never let real provider keys reach tests."""
    from core.config import get_settings
    from services.ai_service import reset_cooldowns

    st = get_settings()
    for k in _PROVIDER_KEYS:
        monkeypatch.setattr(st, k, "", raising=False)
        monkeypatch.delenv(k, raising=False)
    reset_cooldowns()
    yield
    reset_cooldowns()
