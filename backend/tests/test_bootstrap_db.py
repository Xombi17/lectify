"""Tests for database schema bootstrap script and Postgres advisory locking."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from scripts.bootstrap_db import BOOTSTRAP_LOCK_KEY, bootstrap, main


@pytest.mark.asyncio
async def test_bootstrap_sqlite_idempotent(tmp_path):
    """bootstrap() creates all tables on SQLite and re-running is safe and idempotent."""
    db_file = tmp_path / "test_bootstrap.db"
    test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")

    try:
        count1 = await bootstrap(test_engine)
        assert count1 > 0

        # Running a second time should succeed with no errors
        count2 = await bootstrap(test_engine)
        assert count2 == count1
    finally:
        await test_engine.dispose()


@pytest.mark.asyncio
async def test_bootstrap_postgres_locking_sequence():
    """On PostgreSQL, pg_advisory_lock is acquired before create_all and released in finally."""
    call_log = []

    mock_engine = MagicMock()
    mock_engine.dialect.name = "postgresql"

    mock_lock_conn = AsyncMock()

    async def mock_execute(stmt, params=None):
        sql = str(stmt)
        if "pg_advisory_lock" in sql:
            call_log.append(("lock", params.get("k") if params else None))
        elif "pg_advisory_unlock" in sql:
            call_log.append(("unlock", params.get("k") if params else None))
        return MagicMock()

    mock_lock_conn.execute.side_effect = mock_execute
    mock_engine.connect = AsyncMock(return_value=mock_lock_conn)

    # Mock engine.begin() context manager for DDL execution
    mock_ddl_conn = AsyncMock()

    async def mock_run_sync(fn):
        call_log.append(("ddl_create_all", None))

    mock_ddl_conn.run_sync.side_effect = mock_run_sync

    class MockBeginCtx:
        async def __aenter__(self):
            return mock_ddl_conn
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    mock_engine.begin.return_value = MockBeginCtx()

    count = await bootstrap(mock_engine)
    assert count > 0

    assert call_log == [
        ("lock", BOOTSTRAP_LOCK_KEY),
        ("ddl_create_all", None),
        ("unlock", BOOTSTRAP_LOCK_KEY),
    ]


@pytest.mark.asyncio
async def test_bootstrap_postgres_unlocks_on_error():
    """Advisory lock is released in finally even if create_all raises an exception."""
    call_log = []

    mock_engine = MagicMock()
    mock_engine.dialect.name = "postgresql"

    mock_lock_conn = AsyncMock()

    async def mock_execute(stmt, params=None):
        sql = str(stmt)
        if "pg_advisory_lock" in sql:
            call_log.append(("lock", params.get("k") if params else None))
        elif "pg_advisory_unlock" in sql:
            call_log.append(("unlock", params.get("k") if params else None))
        return MagicMock()

    mock_lock_conn.execute.side_effect = mock_execute
    mock_engine.connect = AsyncMock(return_value=mock_lock_conn)

    class MockFailingBeginCtx:
        async def __aenter__(self):
            call_log.append(("ddl_fail", None))
            raise RuntimeError("DDL simulated crash")
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    mock_engine.begin.return_value = MockFailingBeginCtx()

    with pytest.raises(RuntimeError) as exc_info:
        await bootstrap(mock_engine)
    assert "DDL simulated crash" in str(exc_info.value)

    assert call_log == [
        ("lock", BOOTSTRAP_LOCK_KEY),
        ("ddl_fail", None),
        ("unlock", BOOTSTRAP_LOCK_KEY),
    ]


def test_main_success_and_failure(capsys):
    """main() returns 0 on success and 1 on error without leaking passwords."""
    with patch("scripts.bootstrap_db._run_and_close", return_value=12):
        with patch("scripts.bootstrap_db.asyncio.run", return_value=12):
            ret = main()
            assert ret == 0
            captured = capsys.readouterr()
            assert "Schema bootstrap successful: 12 tables ready." in captured.out

    with patch("scripts.bootstrap_db.asyncio.run", side_effect=Exception("Failed connect postgres://user:secretpass@host:5432/db")):
        ret_fail = main()
        assert ret_fail == 1
        captured_err = capsys.readouterr()
        assert "Schema bootstrap failed" in captured_err.err
        assert "secretpass" not in captured_err.err
