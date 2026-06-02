"""Singleton Mongo client. The only place we touch the Mongo driver directly.

Repositories consume `get_db()` and never expose Mongo types to routes/services.
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from core.config import get_settings

_settings = get_settings()
_client: AsyncIOMotorClient | None = None


def get_db() -> AsyncIOMotorDatabase:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(_settings.MONGO_URL)
    return _client[_settings.DB_NAME]


async def close_db() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None
