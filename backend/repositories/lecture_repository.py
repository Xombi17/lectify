"""Dispatcher: returns the right LectureRepository based on DATABASE_BACKEND env."""
from core.config import get_settings

if get_settings().DATABASE_BACKEND.lower() == "mongo":
    from repositories._mongo.lecture_repository import LectureRepository
else:
    from repositories._sql.lecture_repository import LectureRepository  # noqa: F401

__all__ = ["LectureRepository"]
