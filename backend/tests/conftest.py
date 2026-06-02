"""Shared pytest hooks for LectureMind backend tests.

Resets the Motor client singleton before every test so that tests using
their own short-lived asyncio loops (asyncio.run) don't inherit a Motor
client bound to a previously-closed event loop. This is purely defensive
and matches the behaviour of the in-file `_arun` helper.
"""
import sys

import pytest

sys.path.insert(0, "/app/backend")


@pytest.fixture(autouse=True)
def _reset_motor_client_singleton():
    try:
        import core.db as core_db
        core_db._client = None
    except Exception:
        pass
    yield
    try:
        import core.db as core_db
        core_db._client = None
    except Exception:
        pass
