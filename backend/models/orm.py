"""SQLAlchemy ORM models — mirror of the Pydantic models for SQL backends.

Used by the PostgreSQL (and SQLite-for-tests) repository implementations.
"""
from __future__ import annotations

from datetime import datetime, timezone, date
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import expression as sql_expr


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class UserORM(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class LectureORM(Base):
    __tablename__ = "lectures"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    teacher_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(120), nullable=True)
    semester: Mapped[str | None] = mapped_column(String(120), nullable=True)
    audio_object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    audio_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    audio_mime: Mapped[str] = mapped_column(String(64), nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    chunk_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    progress_step: Mapped[int] = mapped_column(Integer, default=0)
    progress_total: Mapped[int] = mapped_column(Integer, default=0)
    progress_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="uploaded", index=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcription_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    transcription_language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    transcription_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    low_confidence_segments: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    materials: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    translations: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # Phase 9: lazy-generated AI content (cached on lecture row)
    cheatsheet: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    podcast_script: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    quiz_v2: Mapped[list | None] = mapped_column(JSON, nullable=True)
    concepts_v2: Mapped[list | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    # Phase 13.1: class-scoped access and timetable scheduling
    class_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("classes.id", ondelete="SET NULL"), index=True, nullable=True
    )
    timetable_slot_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("timetable_slots.id", ondelete="SET NULL"), index=True, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class TimetableSlotORM(Base):
    __tablename__ = "timetable_slots"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    class_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("classes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    teacher_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[str] = mapped_column(String(8), nullable=False)
    end_time: Mapped[str] = mapped_column(String(8), nullable=False)
    room: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ChatMessageORM(Base):
    __tablename__ = "chat_messages"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    lecture_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("lectures.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


class QuizAttemptORM(Base):
    __tablename__ = "quiz_attempts"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    lecture_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("lectures.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    total: Mapped[int] = mapped_column(Integer, nullable=False)
    percentage: Mapped[float] = mapped_column(Float, nullable=False)
    question_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


class BookmarkORM(Base):
    __tablename__ = "bookmarks"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    lecture_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("lectures.id", ondelete="CASCADE"), index=True, nullable=False
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    ref_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


class FlashcardReviewORM(Base):
    __tablename__ = "flashcard_reviews"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    lecture_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("lectures.id", ondelete="CASCADE"), index=True, nullable=False
    )
    card_index: Mapped[int] = mapped_column(Integer, nullable=False)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5)
    interval_days: Mapped[int] = mapped_column(Integer, default=0)
    repetitions: Mapped[int] = mapped_column(Integer, default=0)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    total_reviews: Mapped[int] = mapped_column(Integer, default=0)


# Academic hierarchy entities
from sqlalchemy import UniqueConstraint


class InstitutionORM(Base):
    __tablename__ = "institutions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class YearORM(Base):
    __tablename__ = "years"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    institution_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("institutions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    __table_args__ = (UniqueConstraint("institution_id", "number", name="uq_year_institution_number"),)


class BranchORM(Base):
    # Domain convention: Branch (DB entity) = Department (institution/UI terminology).
    # Rename to departments/department_id only in a dedicated cleanup migration.
    __tablename__ = "branches"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    institution_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("institutions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    __table_args__ = (UniqueConstraint("institution_id", "code", name="uq_branch_institution_code"),)


class BatchORM(Base):
    """Graduating cohort, e.g. Batch of 2028 (admitted 2024).

    Divisions attach to (branch, batch) so the division structure can
    differ per cohort (CSE-2028 has one division, CSE-2029+ has A/B/C).
    """
    __tablename__ = "batches"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    institution_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("institutions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    admission_year: Mapped[int] = mapped_column(Integer, nullable=False)
    graduating_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    __table_args__ = (UniqueConstraint("institution_id", "graduating_year", name="uq_batch_institution_graduating"),)


class BatchSemesterORM(Base):
    """Cohort progression: where a batch is in curriculum time.

    A division's "current semester" is DERIVED from this (batch -> row whose
    window contains today), never stored on the division itself — one source
    of truth. A class pins a teaching instance to one of these rows.
    """
    __tablename__ = "batch_semesters"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    batch_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("batches.id", ondelete="CASCADE"), index=True, nullable=False
    )
    semester_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("semesters.id", ondelete="CASCADE"), index=True, nullable=False
    )
    academic_year: Mapped[str] = mapped_column(String(9), nullable=False)  # e.g. "2026-27"
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    __table_args__ = (UniqueConstraint("batch_id", "semester_id", name="uq_batchsemester_batch_semester"),)


class SemesterORM(Base):
    __tablename__ = "semesters"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    year_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("years.id", ondelete="CASCADE"), index=True, nullable=False
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    __table_args__ = (UniqueConstraint("year_id", "number", name="uq_semester_year_number"),)


class SubjectORM(Base):
    __tablename__ = "subjects"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    semester_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("semesters.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Owning department, e.g. CSE's Semester III subjects vs CE's.
    branch_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("branches.id", ondelete="CASCADE"), index=True, nullable=True
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    credits: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # mandatory | elective | lab | project | internship | broadening
    category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    __table_args__ = (UniqueConstraint("semester_id", "branch_id", "code", name="uq_subject_semester_branch_code"),)


class DivisionORM(Base):
    __tablename__ = "divisions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    # Legacy placement: which semester of the curriculum this division sits in.
    # Nullable now — cohort-based divisions use branch_id + batch_id instead.
    semester_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("semesters.id", ondelete="CASCADE"), index=True, nullable=True
    )
    # Cohort placement: department + graduating batch, e.g. CSE × Batch 2029.
    branch_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("branches.id", ondelete="CASCADE"), index=True, nullable=True
    )
    batch_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("batches.id", ondelete="CASCADE"), index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    __table_args__ = (UniqueConstraint("semester_id", "name", name="uq_division_semester_name"),)


class ClassORM(Base):
    """A teaching instance: one subject taught to one division during one
    academic period. The (division, subject, batch_semester) triple is unique
    so retakes and repeat teaching across years don't collide."""
    __tablename__ = "classes"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    division_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("divisions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    subject_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("subjects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    batch_semester_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("batch_semesters.id", ondelete="SET NULL"), index=True, nullable=True
    )
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)  # Display name for admin UI
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    __table_args__ = (UniqueConstraint(
        "division_id", "subject_id", "batch_semester_id",
        name="uq_class_division_subject_period",
    ),)


class TeacherAssignmentORM(Base):
    __tablename__ = "teacher_assignments"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    class_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("classes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    teacher_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    __table_args__ = (UniqueConstraint("class_id", "teacher_id", name="uq_teacher_assignment_class_teacher"),)


class AuditLogORM(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    admin_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=False
    )
    action: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


class QueueMessageORM(Base):
    """Durable queue storage for the SQLite queue backend (local dev).

    Lets the API process and worker processes share one queue through the
    same database file. Workers claim jobs in the jobs table, so duplicate
    delivery from concurrent pollers is safe.
    """
    __tablename__ = "queue_messages"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    queue: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    visible_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    receipt: Mapped[str | None] = mapped_column(String(64), nullable=True)
    receive_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class QRCodeORM(Base):
    __tablename__ = "qr_codes"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    class_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("classes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token_secret: Mapped[str] = mapped_column(String(255), nullable=False)
    svg_key: Mapped[str] = mapped_column(String(500), nullable=False)
    png_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    scan_count: Mapped[int] = mapped_column(Integer, default=0)
    enrollment_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    generated_by: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    __table_args__ = (
        Index("uq_qr_active_class", "class_id", unique=True, postgresql_where=sql_expr.text("is_active = true")),
    )


class TokenBlacklistORM(Base):
    __tablename__ = "token_blacklist"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
    )


class StudentEnrollmentORM(Base):
    __tablename__ = "student_enrollments"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    class_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("classes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    student_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    __table_args__ = (UniqueConstraint("class_id", "student_id", name="uq_student_enrollment_class_student"),)

class JobORM(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    lecture_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("lectures.id", ondelete="CASCADE"), index=True, nullable=False
    )
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    attempt: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    priority_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    __table_args__ = (UniqueConstraint("lecture_id", "stage", "version", name="uq_jobs_lecture_stage_version"),)


class JobChunkORM(Base):
    __tablename__ = "job_chunks"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    lecture_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("lectures.id", ondelete="CASCADE"), index=True, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    __table_args__ = (UniqueConstraint("lecture_id", "version", "chunk_index", name="uq_job_chunks_lecture_version_index"),)
