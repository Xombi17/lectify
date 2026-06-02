"""Dispatcher: returns the right UserRepository based on DATABASE_BACKEND env."""
from core.config import get_settings

if get_settings().DATABASE_BACKEND.lower() == "mongo":
    from repositories._mongo.user_repository import UserRepository
else:
    from repositories._sql.user_repository import UserRepository  # noqa: F401

__all__ = ["UserRepository"]
