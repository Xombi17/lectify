"""Shared pytest hooks for LectureMind backend tests."""
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, "/app/backend")

# ── Shared mock Redis instance ─────────────────────────────────────────
# Patches at the consumer module level because `from X import fn` binds
# the name at import time — patching the origin doesn't propagate to
# already-imported references in consumer modules.


def _build_mock_redis():
    """Return a pre-configured AsyncMock Redis client."""
    mr = AsyncMock()
    mr.zadd = AsyncMock(return_value=1)
    mr.hset = AsyncMock(return_value=True)
    mr.zcard = AsyncMock(return_value=0)
    mr.ping = AsyncMock(return_value=True)
    mr.hgetall = AsyncMock(return_value={})
    mr.set = AsyncMock(return_value=True)
    mr.lpush = AsyncMock(return_value=1)
    return mr


# Apply patches at module level so they're in place before any test runs
_mock_redis = _build_mock_redis()
_patches = [
    # core.queue is patched at origin for lazy / inline imports
    patch("core.queue.get_redis", return_value=_mock_redis),
    # consumer modules that did `from core.queue import get_redis`
    patch("services.queue_client.get_redis", return_value=_mock_redis),
]
for _p in _patches:
    _p.start()


@pytest.fixture(autouse=True)
def mock_queue_config():
    """Predictable priority scoring for all tests."""
    with patch("core.queue_config.compute_priority_score", return_value=1000.0):
        yield


@pytest.fixture
def mock_redis_client():
    """Provide direct access to the shared mock Redis for per-test assertions."""
    return _mock_redis
