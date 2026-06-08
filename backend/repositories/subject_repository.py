"""Dispatches to the SQL SubjectRepository implementation."""
from repositories._sql.academic_repository import SubjectRepository  # noqa: F401

__all__ = ["SubjectRepository"]
