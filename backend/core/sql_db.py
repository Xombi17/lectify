"""SQL engine + session factory for the PostgreSQL/SQLite backends.

Same per-loop caching pattern as `core/db.py` so we behave well in tests
and multi-loop workers.
"""
from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import get_settings
from models.orm import Base

_settings = get_settings()
_engines: dict[int, AsyncEngine] = {}
_makers: dict[int, async_sessionmaker[AsyncSession]] = {}


def _loop_key() -> int:
    try:
        return id(asyncio.get_running_loop())
    except RuntimeError:
        return 0


def _engine_kwargs(url: str) -> dict:
    is_postgres = url.startswith("postgres")
    kwargs = dict(echo=False, future=True)
    if is_postgres:
        kwargs.update(
            pool_size=_settings.DB_POOL_SIZE,
            max_overflow=_settings.DB_MAX_OVERFLOW,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
    return kwargs

def _engine() -> AsyncEngine:
    if not _settings.DATABASE_URL:
        raise RuntimeError(
            "DATABASE_BACKEND is set to a SQL backend but DATABASE_URL is empty."
        )
    key = _loop_key()
    eng = _engines.get(key)
    if eng is None:
        engine_kwargs = _engine_kwargs(_settings.DATABASE_URL)
        eng = create_async_engine(_settings.DATABASE_URL, **engine_kwargs)
        _engines[key] = eng
        _makers[key] = async_sessionmaker(eng, expire_on_commit=False, class_=AsyncSession)
    return eng


def session_maker() -> async_sessionmaker[AsyncSession]:
    _engine()  # ensure engine exists for this loop
    return _makers[_loop_key()]


async def init_models() -> None:
    """Idempotently create tables. Use Alembic for proper migrations in prod."""
    eng = _engine()
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_sql() -> None:
    key = _loop_key()
    eng = _engines.pop(key, None)
    _makers.pop(key, None)
    if eng is not None:
        await eng.dispose()
