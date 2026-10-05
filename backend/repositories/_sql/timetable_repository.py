"""Timetable repository — SQLAlchemy (async) implementation."""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import or_, select

from core.sql_db import session_maker
from models.orm import TimetableSlotORM
from models.timetable import TimetableSlotDB


def _to_timetable_slot(row: TimetableSlotORM) -> TimetableSlotDB:
    return TimetableSlotDB(
        id=row.id,
        class_id=row.class_id,
        teacher_id=row.teacher_id,
        day_of_week=row.day_of_week,
        start_time=row.start_time,
        end_time=row.end_time,
        room=row.room,
        created_at=row.created_at,
    )


class TimetableRepository:
    def new_id(self) -> str:
        return f"slot_{uuid.uuid4().hex[:12]}"

    async def create(self, slot: TimetableSlotDB) -> TimetableSlotDB:
        async with session_maker()() as s, s.begin():
            s.add(TimetableSlotORM(
                id=slot.id,
                class_id=slot.class_id,
                teacher_id=slot.teacher_id,
                day_of_week=slot.day_of_week,
                start_time=slot.start_time,
                end_time=slot.end_time,
                room=slot.room,
                created_at=slot.created_at,
            ))
        return slot

    async def get_by_id(self, slot_id: str) -> Optional[TimetableSlotDB]:
        async with session_maker()() as s:
            row = await s.get(TimetableSlotORM, slot_id)
            return _to_timetable_slot(row) if row else None

    async def list_by_class(self, class_id: str) -> List[TimetableSlotDB]:
        async with session_maker()() as s:
            q = (
                select(TimetableSlotORM)
                .where(TimetableSlotORM.class_id == class_id)
                .order_by(TimetableSlotORM.day_of_week, TimetableSlotORM.start_time)
            )
            res = await s.execute(q)
            return [_to_timetable_slot(r) for r in res.scalars()]

    async def list_by_classes(self, class_ids: List[str]) -> List[TimetableSlotDB]:
        if not class_ids:
            return []
        async with session_maker()() as s:
            q = (
                select(TimetableSlotORM)
                .where(TimetableSlotORM.class_id.in_(class_ids))
                .order_by(TimetableSlotORM.day_of_week, TimetableSlotORM.start_time)
            )
            res = await s.execute(q)
            return [_to_timetable_slot(r) for r in res.scalars()]

    async def list_by_teacher(self, teacher_id: str) -> List[TimetableSlotDB]:
        async with session_maker()() as s:
            q = (
                select(TimetableSlotORM)
                .where(TimetableSlotORM.teacher_id == teacher_id)
                .order_by(TimetableSlotORM.day_of_week, TimetableSlotORM.start_time)
            )
            res = await s.execute(q)
            return [_to_timetable_slot(r) for r in res.scalars()]

    async def list_all(self) -> List[TimetableSlotDB]:
        async with session_maker()() as s:
            q = select(TimetableSlotORM).order_by(
                TimetableSlotORM.day_of_week, TimetableSlotORM.start_time
            )
            res = await s.execute(q)
            return [_to_timetable_slot(r) for r in res.scalars()]

    async def find_overlap(
        self,
        day_of_week: int,
        start_time: str,
        end_time: str,
        class_id: Optional[str] = None,
        teacher_id: Optional[str] = None,
        exclude_slot_id: Optional[str] = None,
    ) -> Optional[TimetableSlotDB]:
        """Detect interval conflict on day_of_week where existing.start < new.end AND existing.end > new.start."""
        async with session_maker()() as s:
            clauses = [
                TimetableSlotORM.day_of_week == day_of_week,
                TimetableSlotORM.start_time < end_time,
                TimetableSlotORM.end_time > start_time,
            ]
            if exclude_slot_id:
                clauses.append(TimetableSlotORM.id != exclude_slot_id)

            target_conditions = []
            if class_id:
                target_conditions.append(TimetableSlotORM.class_id == class_id)
            if teacher_id:
                target_conditions.append(TimetableSlotORM.teacher_id == teacher_id)

            if target_conditions:
                clauses.append(or_(*target_conditions))

            q = select(TimetableSlotORM).where(*clauses).limit(1)
            res = await s.execute(q)
            row = res.scalar_one_or_none()
            return _to_timetable_slot(row) if row else None

    async def update(self, slot_id: str, fields: dict) -> Optional[TimetableSlotDB]:
        async with session_maker()() as s, s.begin():
            row = await s.get(TimetableSlotORM, slot_id)
            if not row:
                return None
            for k, v in fields.items():
                if hasattr(row, k) and v is not None:
                    setattr(row, k, v)
            return _to_timetable_slot(row)

    async def delete(self, slot_id: str) -> bool:
        async with session_maker()() as s, s.begin():
            row = await s.get(TimetableSlotORM, slot_id)
            if not row:
                return False
            await s.delete(row)
            return True
