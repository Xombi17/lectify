"""Pydantic models for timetable scheduling."""
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class TimetableSlotCreate(BaseModel):
    class_id: str
    teacher_id: str
    day_of_week: int = Field(..., ge=0, le=6, description="0=Monday, 6=Sunday")
    start_time: str = Field(..., min_length=4, max_length=8, description="HH:MM format")
    end_time: str = Field(..., min_length=4, max_length=8, description="HH:MM format")
    room: Optional[str] = None


class TimetableSlotUpdate(BaseModel):
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    start_time: Optional[str] = Field(None, min_length=4, max_length=8)
    end_time: Optional[str] = Field(None, min_length=4, max_length=8)
    room: Optional[str] = None


class TimetableSlotDB(BaseModel):
    id: str
    class_id: str
    teacher_id: str
    day_of_week: int
    start_time: str
    end_time: str
    room: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TimetableSlotPublic(BaseModel):
    id: str
    class_id: str
    teacher_id: str
    day_of_week: int
    start_time: str
    end_time: str
    room: Optional[str] = None
    created_at: datetime
