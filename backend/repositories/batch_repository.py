"""Dispatches to the SQL BatchRepository implementation."""
from repositories._sql.academic_repository import BatchRepository  # noqa: F401

__all__ = ["BatchRepository"]
