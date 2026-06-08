"""Dispatches to the SQL UserRepository implementation."""
from repositories._sql.user_repository import UserRepository  # noqa: F401

__all__ = ["UserRepository"]
