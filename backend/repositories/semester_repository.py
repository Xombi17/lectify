"""Dispatches to the SQL SemesterRepository implementation."""
from repositories._sql.academic_repository import SemesterRepository  # noqa: F401

__all__ = ["SemesterRepository"]
