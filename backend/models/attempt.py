"""Quiz attempt models for lecture quizzes."""
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class QuizAttemptCreate(BaseModel):
    """Payload for submitting a quiz attempt."""
    answers: list[int]


class QuizAttemptDB(BaseModel):
    id: str
    lecture_id: str
    user_id: str
    score: int
    total: int
    percentage: float
    correct_answers: list[int]
    user_answers: list[int]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class QuizAttemptPublic(QuizAttemptDB):
    """Read-only response shape for quiz attempts."""
    pass
