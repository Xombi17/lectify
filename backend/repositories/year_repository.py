"""Dispatches to the SQL YearRepository implementation."""
from repositories._sql.academic_repository import YearRepository  # noqa: F401

__all__ = ["YearRepository"]
