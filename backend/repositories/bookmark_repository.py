"""Dispatches to the SQL BookmarkRepository implementation."""
from repositories._sql.bookmark_repository import BookmarkRepository  # noqa: F401

__all__ = ["BookmarkRepository"]
