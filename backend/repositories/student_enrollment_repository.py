"""Dispatcher: returns the right StudentEnrollmentRepository based on DATABASE_BACKEND env."""
from core.config import get_settings

if get_settings().DATABASE_BACKEND.lower() == "mongo":
    from repositories._mongo.academic_repository import StudentEnrollmentRepository
else:
    from repositories._sql.academic_repository import StudentEnrollmentRepository  # noqa: F401

__all__ = ["StudentEnrollmentRepository"]
