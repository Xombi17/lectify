"""Dispatcher: returns the right ChatRepository based on DATABASE_BACKEND env."""
from core.config import get_settings

if get_settings().DATABASE_BACKEND.lower() == "mongo":
    from repositories._mongo.chat_repository import ChatRepository
else:
    from repositories._sql.chat_repository import ChatRepository  # noqa: F401

__all__ = ["ChatRepository"]
