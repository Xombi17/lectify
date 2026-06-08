"""Dispatches to the SQL DivisionRepository implementation."""
from repositories._sql.academic_repository import DivisionRepository  # noqa: F401

__all__ = ["DivisionRepository"]
