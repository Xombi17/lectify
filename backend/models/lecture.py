"""Pydantic models for lectures and AI-generated study materials."""
from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

LectureStatus = Literal[
    "uploaded", "queued", "processing", "retrying",
    "ready", "error", "dead_letter",
]


class QuizQuestion(BaseModel):
    question: str
    options: List[str]
    answer_index: int
    explanation: Optional[str] = None


class Flashcard(BaseModel):
    front: str
    back: str


class StudyMaterials(BaseModel):
    summary: Optional[str] = None
    smart_notes: List[str] = Field(default_factory=list)
    key_concepts: List[str] = Field(default_factory=list)
    quiz: List[QuizQuestion] = Field(default_factory=list)
    flashcards: List[Flashcard] = Field(default_factory=list)


class LectureCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    subject: Optional[str] = None
    semester: Optional[str] = None


class LectureDB(BaseModel):
    id: str
    teacher_id: str
    title: str
    subject: Optional[str] = None
    semester: Optional[str] = None
    audio_object_key: str
    audio_filename: str
    audio_mime: str
    duration_seconds: Optional[float] = None
    chunk_count: Optional[int] = None
    progress_step: int = 0
    progress_total: int = 0
    progress_label: Optional[str] = None
    status: LectureStatus = "uploaded"
    transcript: Optional[str] = None
    transcription_confidence: Optional[float] = None  # 0.0-1.0
    transcription_language: Optional[str] = None  # "en", "hi", etc.
    transcription_cost_usd: Optional[float] = None  # cost in USD
    low_confidence_segments: list[dict] = Field(default_factory=list)  # flagged segments
    materials: StudyMaterials = Field(default_factory=StudyMaterials)
    embedding: Optional[List[float]] = None
    translations: dict = Field(default_factory=dict)
    error_message: Optional[str] = None
    published: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LectureSummary(BaseModel):
    """Listing payload — omits transcript & materials."""
    id: str
    teacher_id: str
    title: str
    subject: Optional[str]
    semester: Optional[str]
    status: LectureStatus
    published: bool
    created_at: datetime


class QuizAttempt(BaseModel):
    answers: List[int]


class QuizResult(BaseModel):
    score: int
    total: int
    percentage: float
    correct_answers: List[int]
    user_answers: List[int]
