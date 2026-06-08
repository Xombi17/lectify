"""Pydantic models for queue jobs."""
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field

JobStatus = Literal[
    "queued",
    "processing",
    "retrying",
    "completed",
    "failed",
    "dead_letter",
]

JobStage = Literal[
    "transcribe",
    "generate_materials",
    "embed",
    "neo4j_sync",
]


class JobCreate(BaseModel):
    """Payload sent to the queue client when enqueueing a job."""
    lecture_id: str
    version: int = 1
    priority_score: float = 0.0
    stage: JobStage = "transcribe"


class JobDB(BaseModel):
    """Full job record stored in Redis / returned by the client."""
    id: str
    lecture_id: str
    type: str = "process_lecture"
    stage: JobStage = "transcribe"
    status: JobStatus = "queued"
    version: int = 1
    priority_score: float = 0.0
    attempt: int = 0
    max_attempts: int = 3
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class JobPublic(BaseModel):
    """Job representation exposed via API (no internals)."""
    id: str
    lecture_id: str
    stage: JobStage
    status: JobStatus
    attempt: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
