"""Dispatcher: BookmarkRepository — pick Mongo or SQL based on DATABASE_BACKEND."""
from core.config import get_settings

if get_settings().DATABASE_BACKEND.lower() == "mongo":
    from repositories._mongo.bookmark_repository import BookmarkRepository
else:
    from repositories._sql.bookmark_repository import BookmarkRepository  # noqa: F401

__all__ = ["BookmarkRepository"]
