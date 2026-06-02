"""Dispatcher: returns the right SemesterRepository based on DATABASE_BACKEND env."""
from core.config import get_settings

if get_settings().DATABASE_BACKEND.lower() == "mongo":
    from repositories._mongo.academic_repository import SemesterRepository
else:
    from repositories._sql.academic_repository import SemesterRepository  # noqa: F401

__all__ = ["SemesterRepository"]
