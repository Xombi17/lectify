"""SQL repository tests against in-memory SQLite (aiosqlite).
"""
import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone

import pytest

sys.path.insert(0, "/app/backend")


@pytest.fixture(autouse=True)
def _sql_env(monkeypatch):
    """Force SQL backend with aiosqlite in-memory for this module."""
    monkeypatch.setenv("DATABASE_BACKEND", "postgres")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    import importlib
    from core import config as cfg
    cfg.get_settings.cache_clear()
    importlib.reload(cfg)
    import core.sql_db as sdb
    importlib.reload(sdb)
    # Reload _sql modules so they pick up the new session_maker reference
    import repositories._sql.user_repository as ur
    import repositories._sql.lecture_repository as lr
    import repositories._sql.chat_repository as cr
    import repositories._sql.attempt_repository as ar
    importlib.reload(ur); importlib.reload(lr)
    importlib.reload(cr); importlib.reload(ar)
    yield
    cfg.get_settings.cache_clear()


def _arun(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# User repository
# ---------------------------------------------------------------------------
class TestSqlUserRepository:
    def test_create_get_by_id_and_email(self):
        async def go():
            from core.sql_db import init_models, close_sql
            from repositories._sql.user_repository import UserRepository
            from models.user import UserDB

            await init_models()
            repo = UserRepository()
            uid = UserRepository.new_id()
            user = UserDB(
                id=uid,
                name="Alice",
                email="alice@example.com",
                role="teacher",
                password_hash="hash",
            )
            await repo.create(user)

            got = await repo.get_by_id(uid)
            assert got is not None
            assert got.email == "alice@example.com"
            assert got.role == "teacher"
            assert got.name == "Alice"

            by_email = await repo.get_by_email("alice@example.com")
            assert by_email is not None
            assert by_email.id == uid

            # case-insensitive email check (db handles comparison)
            none = await repo.get_by_email("Nobody@example.com")
            assert none is None
            await close_sql()
        _arun(go())


# ---------------------------------------------------------------------------
# Lecture repository
# ---------------------------------------------------------------------------
def _make_lecture(teacher_id: str, **over):
    from models.lecture import LectureDB, StudyMaterials
    base = dict(
        id=str(uuid.uuid4()),
        teacher_id=teacher_id,
        title="Test Lecture",
        subject="Math",
        semester="Fall25",
        audio_object_key=f"lectures/{teacher_id}/audio.mp3",
        audio_filename="audio.mp3",
        audio_mime="audio/mpeg",
        materials=StudyMaterials(),
    )
    base.update(over)
    return LectureDB(**base)


def _seed_teacher(uid="t1"):
    from repositories._sql.user_repository import UserRepository
    from models.user import UserDB
    return UserRepository().create(UserDB(
        id=uid, name="T", email=f"{uid}@x.com", role="teacher", password_hash="h",
    ))


class TestSqlLectureRepository:
    def test_create_get_list_and_delete(self):
        async def go():
            from core.sql_db import init_models, close_sql
            from repositories._sql.lecture_repository import LectureRepository
            await init_models()
            await _seed_teacher("t1")
            repo = LectureRepository()
            lec = _make_lecture("t1", title="Lec A")
            await repo.create(lec)

            got = await repo.get_by_id(lec.id)
            assert got is not None
            assert got.title == "Lec A"
            assert got.materials.summary is None
            assert got.published is False

            mine = await repo.list_by_teacher("t1")
            assert len(mine) == 1
            assert mine[0].id == lec.id
            assert mine[0].published is False

            await repo.delete(lec.id)
            assert await repo.get_by_id(lec.id) is None
            await close_sql()
        _arun(go())

    def test_update_fields_serializes_studymaterials(self):
        async def go():
            from core.sql_db import init_models, close_sql
            from repositories._sql.lecture_repository import LectureRepository
            from models.lecture import StudyMaterials
            await init_models()
            await _seed_teacher("t2")
            repo = LectureRepository()
            lec = _make_lecture("t2")
            await repo.create(lec)

            mats = StudyMaterials(
                summary="A short summary",
                smart_notes=["n1", "n2"],
                key_concepts=["k1"],
            )
            await repo.update_fields(lec.id, {
                "status": "ready",
                "transcript": "hello world",
                "materials": mats,  # MUST be converted to dict via model_dump
                "published": True,
                "embedding": [0.1, 0.2, 0.3],
            })

            got = await repo.get_by_id(lec.id)
            assert got.status == "ready"
            assert got.transcript == "hello world"
            assert got.materials.summary == "A short summary"
            assert got.materials.smart_notes == ["n1", "n2"]
            assert got.materials.key_concepts == ["k1"]
            assert got.published is True
            assert got.embedding == [0.1, 0.2, 0.3]
            await close_sql()
        _arun(go())

    def test_list_published_and_embeddings(self):
        async def go():
            from core.sql_db import init_models, close_sql
            from repositories._sql.lecture_repository import LectureRepository
            from models.lecture import StudyMaterials
            await init_models()
            await _seed_teacher("t3")
            repo = LectureRepository()
            l1 = _make_lecture("t3", title="Pub1")
            l2 = _make_lecture("t3", title="Pub2")
            l3 = _make_lecture("t3", title="Draft")
            await repo.create(l1); await repo.create(l2); await repo.create(l3)
            await repo.update_fields(l1.id, {
                "published": True, "embedding": [0.1, 0.2],
                "materials": StudyMaterials(summary="s1", key_concepts=["c"]),
            })
            await repo.update_fields(l2.id, {
                "published": True, "embedding": [0.3, 0.4],
                "materials": StudyMaterials(summary="s2", key_concepts=["d"]),
            })

            pubs = await repo.list_published()
            assert {p.title for p in pubs} == {"Pub1", "Pub2"}
            assert all(p.published for p in pubs)

            embs = await repo.list_published_embeddings()
            assert len(embs) == 2
            by_title = {e["title"]: e for e in embs}
            assert by_title["Pub1"]["embedding"] == [0.1, 0.2]
            assert by_title["Pub1"]["materials"]["summary"] == "s1"
            assert by_title["Pub1"]["materials"]["key_concepts"] == ["c"]
            await close_sql()
        _arun(go())

    def test_update_fields_no_op_when_missing(self):
        async def go():
            from core.sql_db import init_models, close_sql
            from repositories._sql.lecture_repository import LectureRepository
            await init_models()
            repo = LectureRepository()
            # must not raise
            await repo.update_fields("nope", {"status": "ready"})
            await close_sql()
        _arun(go())


# ---------------------------------------------------------------------------
# Chat repository
# ---------------------------------------------------------------------------
class TestSqlChatRepository:
    def test_add_and_list_for(self):
        async def go():
            from core.sql_db import init_models, close_sql
            from repositories._sql.chat_repository import ChatRepository
            from repositories._sql.lecture_repository import LectureRepository
            from models.chat import ChatMessageDB

            await init_models()
            await _seed_teacher("tc")
            lec = _make_lecture("tc")
            await LectureRepository().create(lec)

            repo = ChatRepository()
            uid = "tc"
            msgs = [
                ChatMessageDB(id=str(uuid.uuid4()), lecture_id=lec.id, user_id=uid,
                              role="user", content="Q1",
                              created_at=datetime.now(timezone.utc)),
                ChatMessageDB(id=str(uuid.uuid4()), lecture_id=lec.id, user_id=uid,
                              role="assistant", content="A1",
                              created_at=datetime.now(timezone.utc)),
            ]
            for m in msgs:
                await repo.add(m)

            got = await repo.list_for(lec.id, uid)
            assert len(got) == 2
            assert got[0].content == "Q1"
            assert got[1].content == "A1"

            # other user sees nothing
            await _seed_teacher("other")  # just to have user row (FK)
            empty = await repo.list_for(lec.id, "other")
            assert empty == []
            await close_sql()
        _arun(go())


# ---------------------------------------------------------------------------
# Attempt repository
# ---------------------------------------------------------------------------
class TestSqlAttemptRepository:
    def test_add_and_list_for_user(self):
        async def go():
            from core.sql_db import init_models, close_sql
            from repositories._sql.attempt_repository import AttemptRepository
            from repositories._sql.lecture_repository import LectureRepository
            from models.chat import QuizAttemptRecord

            await init_models()
            await _seed_teacher("ta")
            lec = _make_lecture("ta")
            await LectureRepository().create(lec)

            repo = AttemptRepository()
            r1 = QuizAttemptRecord(
                id=str(uuid.uuid4()), lecture_id=lec.id, user_id="ta",
                score=8, total=10, percentage=80.0,
                created_at=datetime.now(timezone.utc),
            )
            r2 = QuizAttemptRecord(
                id=str(uuid.uuid4()), lecture_id=lec.id, user_id="ta",
                score=5, total=10, percentage=50.0,
                created_at=datetime.now(timezone.utc),
            )
            await repo.add(r1); await repo.add(r2)

            out = await repo.list_for_user("ta")
            assert len(out) == 2
            assert {x.score for x in out} == {8, 5}
            assert all(isinstance(x.percentage, float) for x in out)

            other = await repo.list_for_user("nobody")
            assert other == []
            await close_sql()
        _arun(go())


# ---------------------------------------------------------------------------
# Dispatcher round-trip when DATABASE_BACKEND=postgres
# ---------------------------------------------------------------------------
class TestDispatcher:
    def test_dispatcher_returns_sql_impl(self):
        """When DATABASE_BACKEND=postgres at import time, dispatcher re-exports _sql."""
        import importlib
        from core import config as cfg
        cfg.get_settings.cache_clear()
        importlib.reload(cfg)
        import repositories.user_repository as uref
        importlib.reload(uref)
        from repositories._sql.user_repository import UserRepository as SqlUser
        assert uref.UserRepository is SqlUser
