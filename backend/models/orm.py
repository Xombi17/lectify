"""SQLAlchemy ORM models — mirror of the Pydantic models for SQL backends.

Used by the PostgreSQL (and SQLite-for-tests) repository implementations.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
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
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


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
    __tablename__ = "branches"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    institution_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("institutions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    __table_args__ = (UniqueConstraint("institution_id", "code", name="uq_branch_institution_code"),)


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
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    credits: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    __table_args__ = (UniqueConstraint("semester_id", "code", name="uq_subject_semester_code"),)


class DivisionORM(Base):
    __tablename__ = "divisions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    semester_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("semesters.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    __table_args__ = (UniqueConstraint("semester_id", "name", name="uq_division_semester_name"),)


class ClassORM(Base):
    __tablename__ = "classes"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    division_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("divisions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    subject_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("subjects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)  # Display name for admin UI
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    __table_args__ = (UniqueConstraint("division_id", "subject_id", name="uq_class_division_subject"),)


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
