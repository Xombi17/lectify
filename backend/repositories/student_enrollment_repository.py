"""Dispatches to the SQL StudentEnrollmentRepository implementation."""
from repositories._sql.academic_repository import StudentEnrollmentRepository  # noqa: F401

__all__ = ["StudentEnrollmentRepository"]
