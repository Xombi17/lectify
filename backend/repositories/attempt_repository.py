"""Dispatcher: returns the right AttemptRepository based on DATABASE_BACKEND env."""
from core.config import get_settings

if get_settings().DATABASE_BACKEND.lower() == "mongo":
    from repositories._mongo.attempt_repository import AttemptRepository
else:
    from repositories._sql.attempt_repository import AttemptRepository  # noqa: F401

__all__ = ["AttemptRepository"]
