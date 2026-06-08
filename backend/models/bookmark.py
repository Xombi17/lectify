"""Bookmark + FlashcardReview models."""
from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


BookmarkKind = Literal["concept", "note", "flashcard"]


class BookmarkDB(BaseModel):
    id: str
    user_id: str
    lecture_id: str
    kind: BookmarkKind
    text: str
    ref_index: Optional[int] = None  # index in materials.{key_concepts | smart_notes | flashcards}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BookmarkCreate(BaseModel):
    lecture_id: str
    kind: BookmarkKind
    text: str = Field(..., min_length=1, max_length=1000)
    ref_index: Optional[int] = None


class BookmarkPublic(BookmarkDB):
    """Read-only response shape for bookmark endpoints."""
    pass


class BookmarkWithLecture(BookmarkDB):
    lecture_title: str
    lecture_subject: Optional[str] = None


# --- Spaced-repetition (SM-2 lite) ---

# Quality rating from the user: 0 = Again, 1 = Hard, 2 = Good, 3 = Easy
ReviewQuality = Literal[0, 1, 2, 3]


class FlashcardReviewDB(BaseModel):
    id: str
    user_id: str
    lecture_id: str
    card_index: int           # index into lecture.materials.flashcards
    ease_factor: float = 2.5  # SM-2 EF
    interval_days: int = 0
    repetitions: int = 0
    last_reviewed_at: Optional[datetime] = None
    due_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_reviews: int = 0


class ReviewSubmit(BaseModel):
    lecture_id: str
    card_index: int
    quality: ReviewQuality


class DueCard(BaseModel):
    """Hydrated due-card: ready for the student to study without extra fetches."""
    lecture_id: str
    lecture_title: str
    card_index: int
    front: str
    back: str
    due_at: datetime
    repetitions: int
    ease_factor: float


class MaterialsUpdate(BaseModel):
    """Teacher edits to AI-generated study materials."""
    summary: Optional[str] = None
    smart_notes: Optional[List[str]] = None
    key_concepts: Optional[List[str]] = None
