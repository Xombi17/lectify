"""Dispatches to the SQL BatchSemesterRepository implementation."""
from repositories._sql.academic_repository import BatchSemesterRepository  # noqa: F401

__all__ = ["BatchSemesterRepository"]
