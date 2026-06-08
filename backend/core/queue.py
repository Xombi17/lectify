"""Redis connection pool and ARQ queue settings."""
from functools import lru_cache

from redis.asyncio import Redis, ConnectionPool

from core.config import get_settings


@lru_cache
def get_redis_pool() -> ConnectionPool:
    """Create a reusable Redis connection pool.

    Pool is cached via lru_cache so it's created once and reused
    across all workers and the API server.
    """
    settings = get_settings()
    return ConnectionPool.from_url(
        settings.REDIS_URL,
        max_connections=settings.REDIS_MAX_CONNECTIONS,
        decode_responses=False,  # arq needs bytes for job serialization
    )


@lru_cache
def get_redis() -> Redis:
    """Get a Redis client from the shared pool."""
    return Redis(connection_pool=get_redis_pool())


async def close_redis() -> None:
    """Close all connections in the pool. Call on shutdown."""
    pool = get_redis_pool()
    await pool.disconnect()