"""Dispatches to the SQL LectureRepository implementation."""
from repositories._sql.lecture_repository import LectureRepository  # noqa: F401

__all__ = ["LectureRepository"]
