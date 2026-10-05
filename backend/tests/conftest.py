"""Shared pytest hooks for LectureMind backend tests."""
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("ENV", "test")
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-prod")

import pytest
import pytest_asyncio

# Add the backend directory to sys.path (works locally and in Docker)
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from core.sql_db import _engine as get_engine
from core.sql_db import session_maker
from models.orm import Base, UserORM, LectureORM

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with session_maker()() as session:
        # insert stub user and lecture to satisfy foreign keys
        session.add(UserORM(id="u1", name="U", email="u@e.com", role="student", password_hash=""))
        session.add(LectureORM(id="l1", teacher_id="u1", title="T", audio_object_key="", audio_filename="", audio_mime=""))
        session.add(LectureORM(id="dup-test", teacher_id="u1", title="T", audio_object_key="", audio_filename="", audio_mime=""))
        session.add(LectureORM(id="lec-123", teacher_id="u1", title="T", audio_object_key="", audio_filename="", audio_mime=""))
        session.add(LectureORM(id="lec-1", teacher_id="u1", title="T", audio_object_key="", audio_filename="", audio_mime=""))
        session.add(LectureORM(id="integration-test-1", teacher_id="u1", title="T", audio_object_key="", audio_filename="", audio_mime=""))
        session.add(LectureORM(id="idempotency-test-1", teacher_id="u1", title="T", audio_object_key="", audio_filename="", audio_mime=""))
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
