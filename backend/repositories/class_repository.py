"""Dispatches to the SQL ClassRepository implementation."""
from repositories._sql.academic_repository import ClassRepository  # noqa: F401

__all__ = ["ClassRepository"]
