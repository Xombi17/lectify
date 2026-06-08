"""Flashcard review models for spaced repetition (SM-2)."""
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class FlashcardReviewCreate(BaseModel):
    """Payload for recording a flashcard review."""
    lecture_id: str
    card_index: int
    quality: int  # 0 = Again, 1 = Hard, 2 = Good, 3 = Easy


class FlashcardReviewDB(BaseModel):
    id: str
    user_id: str
    lecture_id: str
    card_index: int
    ease_factor: float = 2.5
    interval_days: int = 0
    repetitions: int = 0
    last_reviewed_at: Optional[datetime] = None
    due_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_reviews: int = 0


class FlashcardReviewPublic(FlashcardReviewDB):
    """Read-only response shape for flashcard reviews."""
    pass
