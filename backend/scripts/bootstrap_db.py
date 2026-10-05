"""Database schema bootstrap script with PostgreSQL advisory locking."""
import asyncio
import logging
import sys
from sqlalchemy import text

from core.sql_db import _engine, close_sql
from models.orm import Base

logger = logging.getLogger(__name__)

# Fixed 64-bit int advisory lock key ("Lectify1" in ASCII hex: 0x4C65637469667931)
BOOTSTRAP_LOCK_KEY: int = 5504283845945100081


async def bootstrap(engine=None) -> int:
    """Run Base.metadata.create_all idempotently.

    On PostgreSQL, acquires a session-level advisory lock (BOOTSTRAP_LOCK_KEY)
    so concurrent executions serialize safely. On SQLite/other dialects, runs
    create_all directly without locking.

    Returns:
        int: Number of tables defined in Base.metadata
    """
    if engine is None:
        engine = _engine()

    if engine.dialect.name == "postgresql":
        logger.info("Acquiring PostgreSQL advisory lock %s...", BOOTSTRAP_LOCK_KEY)
        lock_conn = await engine.connect()
        # Advisory locks should be acquired in AUTOCOMMIT isolation
        await lock_conn.execution_options(isolation_level="AUTOCOMMIT")
        await lock_conn.execute(
            text("SELECT pg_advisory_lock(:k)"),
            {"k": BOOTSTRAP_LOCK_KEY},
        )
        try:
            logger.info("Advisory lock acquired. Executing create_all...")
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Schema tables created/verified.")
        finally:
            try:
                await lock_conn.execute(
                    text("SELECT pg_advisory_unlock(:k)"),
                    {"k": BOOTSTRAP_LOCK_KEY},
                )
                logger.info("Advisory lock released.")
            finally:
                await lock_conn.close()
    else:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    return len(Base.metadata.tables)


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    try:
        table_count = asyncio.run(_run_and_close())
        sys.stdout.write(f"Schema bootstrap successful: {table_count} tables ready.\n")
        return 0
    except Exception as e:
        # Sanitize exception message to ensure no credentials or sensitive URLs leak
        err_msg = str(e)
        if "@" in err_msg and "://" in err_msg:
            # Strip connection string userInfo if leaked in DB driver error
            import re
            err_msg = re.sub(r"://([^:]+):([^@]+)@", "://[REDACTED]:[REDACTED]@", err_msg)
        sys.stderr.write(f"Schema bootstrap failed: {err_msg}\n")
        return 1


async def _run_and_close() -> int:
    try:
        engine = _engine()
        return await bootstrap(engine)
    finally:
        await close_sql()


if __name__ == "__main__":
    sys.exit(main())
