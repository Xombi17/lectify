"""Singleton Mongo client, keyed per asyncio event loop.

Motor's AsyncIOMotorClient binds to the loop it was constructed on. Caching a
single instance at module scope works in normal FastAPI runs (one loop), but
breaks across multiple `asyncio.run()` calls (test suites, multi-tenant
workers, scripts) because the cached client retains a reference to a *closed*
loop.

We cache one client per running loop so the production code is naturally safe
in those contexts too. Repositories consume `get_db()` and never expose Mongo
types to routes/services.
"""
import asyncio

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from core.config import get_settings

_settings = get_settings()
_clients: dict[int, AsyncIOMotorClient] = {}


def _loop_key() -> int:
    try:
        loop = asyncio.get_running_loop()
        return id(loop)
    except RuntimeError:
        # No running loop (sync context). Use a sentinel that won't collide.
        return 0


def get_db() -> AsyncIOMotorDatabase:
    key = _loop_key()
    client = _clients.get(key)
    if client is None:
        client = AsyncIOMotorClient(_settings.MONGO_URL)
        _clients[key] = client
    return client[_settings.DB_NAME]


async def close_db() -> None:
    """Close the client bound to the current loop (best effort)."""
    key = _loop_key()
    client = _clients.pop(key, None)
    if client is not None:
        client.close()
