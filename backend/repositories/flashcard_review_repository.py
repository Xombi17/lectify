"""Dispatcher: FlashcardReviewRepository — pick Mongo or SQL based on DATABASE_BACKEND."""
from core.config import get_settings

if get_settings().DATABASE_BACKEND.lower() == "mongo":
    from repositories._mongo.flashcard_review_repository import FlashcardReviewRepository
else:
    from repositories._sql.flashcard_review_repository import FlashcardReviewRepository  # noqa: F401

__all__ = ["FlashcardReviewRepository"]
