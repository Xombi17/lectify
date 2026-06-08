"""Shared pytest hooks for LectureMind backend tests."""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add the backend directory to sys.path (works locally and in Docker)
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

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


# Import modules before patching so `patch("module.attr")` resolves correctly.
# Without these explicit imports, patch may fail with
# `AttributeError: module 'X' has no attribute 'Y'`.
import core.queue  # noqa: E402
import core.queue_config  # noqa: E402
import services.queue_client  # noqa: E402

_mock_redis = _build_mock_redis()
_patches = [
    # core.queue is patched at origin for lazy / inline imports
    patch.object(core.queue, "get_redis", return_value=_mock_redis),
    # consumer modules that did `from core.queue import get_redis`
    patch.object(services.queue_client, "get_redis", return_value=_mock_redis),
]


def setup_module():
    """Start all patches before any test runs."""
    for _p in _patches:
        _p.start()


def teardown_module():
    """Stop all patches after all tests complete."""
    for _p in _patches:
        _p.stop()


# Note: Patches are started by setup_module() which pytest calls automatically
# before running tests. Do NOT start them here at module level — that would
# create nested patch layers and prevent cleanup.


@pytest.fixture
def mock_redis_client():
    """Provide direct access to the shared mock Redis for per-test assertions."""
    return _mock_redis
