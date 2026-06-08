"""Chat & analytics models."""
from datetime import datetime, timezone
from typing import List, Literal

from pydantic import BaseModel, Field


ChatRole = Literal["user", "assistant"]


class ChatMessageDB(BaseModel):
    id: str
    lecture_id: str
    user_id: str
    role: ChatRole
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatMessageCreate(BaseModel):
    """Payload for creating a new chat message."""
    lecture_id: str
    question: str = Field(..., min_length=1, max_length=2000)


class ChatMessagePublic(ChatMessageDB):
    """Read-only response shape for chat messages."""
    pass


class ChatAskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


class ChatAskResponse(BaseModel):
    user_message: ChatMessageDB
    assistant_message: ChatMessageDB


class QuizAnswer(BaseModel):
    """Individual answer within a quiz attempt."""
    question_index: int
    answer: int | str | bool | None = None
    correct: bool = False
    time_spent_seconds: int = 0


class QuizQuestionV2(BaseModel):
    """Enhanced quiz question with type, difficulty, and topic."""
    type: Literal["multiple_choice", "true_false", "fill_blank"]
    question: str
    options: list[str] = Field(default_factory=list)
    answer_index: int | None = None
    answer: bool | str | None = None
    accepted_answers: list[str] = Field(default_factory=list)
    explanation: str = ""
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    topic: str = ""


class QuizAttemptRecord(BaseModel):
    id: str
    lecture_id: str
    user_id: str
    score: int
    total: int
    percentage: float
    questions: list[QuizQuestionV2] = Field(default_factory=list)
    answers: list[QuizAnswer] = Field(default_factory=list)
    topic_scores: dict[str, float] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WeakLecture(BaseModel):
    lecture_id: str
    title: str
    avg_percentage: float
    attempts: int


class StudentAnalytics(BaseModel):
    attempts_count: int
    lectures_attempted: int
    avg_percentage: float
    last_attempt_at: datetime | None = None
    streak_days: int
    streak_data: dict | None = None
    current_goal_progress: dict | None = None
    weak_lectures: List[WeakLecture] = Field(default_factory=list)
    strong_lectures: List[WeakLecture] = Field(default_factory=list)


class TranslateRequest(BaseModel):
    target_language: str = Field(..., min_length=2, max_length=40)


class SearchResult(BaseModel):
    lecture_id: str
    title: str
    subject: str | None = None
    semester: str | None = None
    snippet: str | None = None
    score: float
