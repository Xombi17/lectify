"""SQLite queue backend tests — same-process semantics + cross-process visibility."""
import asyncio
import sys

import pytest

sys.path.insert(0, "/app/backend")


@pytest.fixture()
def _sqlite_env(monkeypatch, tmp_path):
    """Point the SQL layer at a temp file DB shared by all engine instances."""
    db_file = tmp_path / "queue_test.db"
    monkeypatch.setenv("DATABASE_BACKEND", "postgres")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_file}")
    monkeypatch.setenv("QUEUE_BACKEND", "sqlite")
    import importlib

    from core import config as cfg

    cfg.get_settings.cache_clear()
    importlib.reload(cfg)
    import core.sql_db as sdb

    importlib.reload(sdb)
    import core.queue_backend as qb

    importlib.reload(qb)
    yield qb
    cfg.get_settings.cache_clear()
    qb.reset_queue_backend()


def _arun(coro):
    return asyncio.run(coro)


class TestSqliteQueueBackend:
    def test_send_receive_delete(self, _sqlite_env):
        async def go():
            from core.sql_db import close_sql, init_models

            await init_models()
            backend = _sqlite_env.SqliteQueueBackend()
            await backend.send("transcribe", {"job_id": "j1"})
            assert await backend.depth("transcribe") == 1

            msgs = await backend.receive("transcribe", max_messages=1, wait_seconds=2)
            assert len(msgs) == 1
            assert msgs[0].body == {"job_id": "j1"}
            assert msgs[0].receive_count == 1

            # Invisible while in-flight
            assert await backend.receive("transcribe", max_messages=1, wait_seconds=1) == []

            await backend.delete("transcribe", msgs[0].receipt)
            assert await backend.depth("transcribe") == 0
            await close_sql()

        _arun(go())

    def test_cross_process_visibility(self, _sqlite_env):
        """A message sent through one backend instance is received through a
        fresh instance over the same file — the whole point: API and workers
        run in different processes locally."""
        async def go():
            from core.sql_db import close_sql, init_models

            await init_models()
            sender = _sqlite_env.SqliteQueueBackend()
            await sender.send("transcribe", {"job_id": "j9"})

            # Simulate the worker process: new instance, same file
            receiver = _sqlite_env.SqliteQueueBackend()
            msgs = await receiver.receive("transcribe", max_messages=1, wait_seconds=2)
            assert len(msgs) == 1
            assert msgs[0].body["job_id"] == "j9"
            await receiver.delete("transcribe", msgs[0].receipt)
            await close_sql()

        _arun(go())

    def test_change_visibility_releases(self, _sqlite_env):
        async def go():
            from core.sql_db import close_sql, init_models

            await init_models()
            backend = _sqlite_env.SqliteQueueBackend()
            await backend.send("transcribe", {"job_id": "j2"})
            msgs = await backend.receive("transcribe", max_messages=1, wait_seconds=2)
            assert len(msgs) == 1
            # Release immediately (shutdown drain path)
            await backend.change_visibility("transcribe", msgs[0].receipt, 0)
            again = await backend.receive("transcribe", max_messages=1, wait_seconds=2)
            assert len(again) == 1
            assert again[0].receive_count == 2
            await backend.delete("transcribe", again[0].receipt)
            await close_sql()

        _arun(go())

    def test_max_receives_moves_to_dlq(self, _sqlite_env):
        async def go():
            from core.sql_db import close_sql, init_models

            await init_models()
            backend = _sqlite_env.SqliteQueueBackend(max_receives=2)
            await backend.send("transcribe", {"job_id": "j3"})
            m1 = await backend.receive("transcribe", max_messages=1, wait_seconds=2)
            assert len(m1) == 1
            # Simulate redelivery after visibility timeout
            await backend.change_visibility("transcribe", m1[0].receipt, 0)
            m2 = await backend.receive("transcribe", max_messages=1, wait_seconds=2)
            assert len(m2) == 1
            await backend.change_visibility("transcribe", m2[0].receipt, 0)
            # Third receive exceeds max → moved to DLQ, nothing returned
            assert await backend.receive("transcribe", max_messages=1, wait_seconds=2) == []
            assert await backend.dlq_depth() == 1
            assert await backend.depth("transcribe") == 0
            await close_sql()

        _arun(go())
