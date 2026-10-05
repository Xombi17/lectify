"""Lecture repository — SQLAlchemy (async) implementation."""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select

from core.sql_db import session_maker
from models.lecture import LectureDB, LectureSummary, StudyMaterials
from models.orm import LectureORM


def _to_lecture(row: LectureORM) -> LectureDB:
    materials_dict = row.materials or {}
    return LectureDB(
        id=row.id,
        teacher_id=row.teacher_id,
        title=row.title,
        subject=row.subject,
        semester=row.semester,
        audio_object_key=row.audio_object_key,
        audio_filename=row.audio_filename,
        audio_mime=row.audio_mime,
        duration_seconds=row.duration_seconds,
        chunk_count=row.chunk_count,
        progress_step=row.progress_step or 0,
        progress_total=row.progress_total or 0,
        progress_label=row.progress_label,
        status=row.status,
        transcript=row.transcript,
        transcription_confidence=row.transcription_confidence,
        transcription_language=row.transcription_language,
        transcription_cost_usd=row.transcription_cost_usd,
        low_confidence_segments=row.low_confidence_segments or [],
        materials=StudyMaterials(**materials_dict) if materials_dict else StudyMaterials(),
        embedding=row.embedding,
        translations=row.translations or {},
        cheatsheet=row.cheatsheet,
        podcast_script=row.podcast_script,
        quiz_v2=row.quiz_v2,
        concepts_v2=row.concepts_v2,
        error_message=row.error_message,
        published=bool(row.published),
        class_id=row.class_id,
        timetable_slot_id=row.timetable_slot_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _to_summary(row: LectureORM) -> LectureSummary:
    return LectureSummary(
        id=row.id,
        teacher_id=row.teacher_id,
        title=row.title,
        subject=row.subject,
        semester=row.semester,
        status=row.status,
        published=bool(row.published),
        class_id=row.class_id,
        timetable_slot_id=row.timetable_slot_id,
        created_at=row.created_at,
    )


class LectureRepository:
    async def ensure_indexes(self) -> None:
        return None  # ORM column indexes do the job

    async def create(self, lecture: LectureDB) -> LectureDB:
        async with session_maker()() as s, s.begin():
            s.add(LectureORM(
                id=lecture.id,
                teacher_id=lecture.teacher_id,
                title=lecture.title,
                subject=lecture.subject,
                semester=lecture.semester,
                audio_object_key=lecture.audio_object_key,
                audio_filename=lecture.audio_filename,
                audio_mime=lecture.audio_mime,
                duration_seconds=lecture.duration_seconds,
                chunk_count=lecture.chunk_count,
                progress_step=lecture.progress_step,
                progress_total=lecture.progress_total,
                progress_label=lecture.progress_label,
                status=lecture.status,
                transcript=lecture.transcript,
                materials=lecture.materials.model_dump(),
                embedding=lecture.embedding,
                translations=lecture.translations or {},
                error_message=lecture.error_message,
                published=lecture.published,
                class_id=lecture.class_id,
                timetable_slot_id=lecture.timetable_slot_id,
                created_at=lecture.created_at,
                updated_at=lecture.updated_at,
            ))
        return lecture

    async def get_by_id(self, lecture_id: str) -> Optional[LectureDB]:
        async with session_maker()() as s:
            row = await s.get(LectureORM, lecture_id)
            return _to_lecture(row) if row else None

    async def list_by_teacher(self, teacher_id: str) -> List[LectureSummary]:
        async with session_maker()() as s:
            stmt = (
                select(LectureORM)
                .where(LectureORM.teacher_id == teacher_id)
                .order_by(LectureORM.created_at.desc())
            )
            rows = (await s.execute(stmt)).scalars().all()
            return [_to_summary(r) for r in rows]

    async def list_published(self, class_ids: Optional[List[str]] = None) -> List[LectureSummary]:
        if class_ids is not None and len(class_ids) == 0:
            return []
        async with session_maker()() as s:
            stmt = (
                select(LectureORM)
                .where(LectureORM.published.is_(True))
            )
            if class_ids is not None:
                stmt = stmt.where(LectureORM.class_id.in_(class_ids))
            stmt = stmt.order_by(LectureORM.created_at.desc())
            rows = (await s.execute(stmt)).scalars().all()
            return [_to_summary(r) for r in rows]

    async def list_published_embeddings(self, class_ids: Optional[List[str]] = None) -> list[dict]:
        if class_ids is not None and len(class_ids) == 0:
            return []
        async with session_maker()() as s:
            stmt = select(LectureORM).where(LectureORM.published.is_(True))
            if class_ids is not None:
                stmt = stmt.where(LectureORM.class_id.in_(class_ids))
            rows = (await s.execute(stmt)).scalars().all()
            return [
                {
                    "id": r.id,
                    "title": r.title,
                    "subject": r.subject,
                    "semester": r.semester,
                    "class_id": r.class_id,
                    "embedding": r.embedding or [],
                    "materials": {
                        "summary": (r.materials or {}).get("summary"),
                        "key_concepts": (r.materials or {}).get("key_concepts", []),
                    },
                }
                for r in rows
            ]

    async def update_fields(self, lecture_id: str, fields: dict) -> None:
        if "materials" in fields and hasattr(fields["materials"], "model_dump"):
            fields["materials"] = fields["materials"].model_dump()
        fields["updated_at"] = datetime.now(timezone.utc)
        async with session_maker()() as s, s.begin():
            row = await s.get(LectureORM, lecture_id)
            if row is None:
                return
            for k, v in fields.items():
                if hasattr(row, k):
                    setattr(row, k, v)

    async def delete(self, lecture_id: str) -> None:
        async with session_maker()() as s, s.begin():
            row = await s.get(LectureORM, lecture_id)
            if row is not None:
                await s.delete(row)

    async def get_lectures_by_date_range(self, start: datetime, end: datetime) -> List[LectureDB]:
        """Get lectures created within a date range.

        Args:
            start: Start of range (inclusive).
            end: End of range (exclusive).

        Returns:
            List of LectureDB objects ordered by created_at descending.
        """
        async with session_maker()() as s:
            stmt = (
                select(LectureORM)
                .where(LectureORM.created_at >= start, LectureORM.created_at < end)
                .order_by(LectureORM.created_at.desc())
            )
            rows = (await s.execute(stmt)).scalars().all()
            return [_to_lecture(r) for r in rows]

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())
