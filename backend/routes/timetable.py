"""Timetable routes — scheduling, overlap protection, and access-controlled views."""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from core.deps import get_current_user
from models.timetable import (
    TimetableSlotCreate,
    TimetableSlotDB,
    TimetableSlotPublic,
    TimetableSlotUpdate,
)
from models.user import UserPublic
from repositories.student_enrollment_repository import StudentEnrollmentRepository
from repositories.teacher_assignment_repository import TeacherAssignmentRepository
from repositories.timetable_repository import TimetableRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/timetable", tags=["timetable"])


@router.post("/slots", response_model=TimetableSlotPublic, status_code=status.HTTP_201_CREATED)
async def create_timetable_slot(
    payload: TimetableSlotCreate,
    user: UserPublic = Depends(get_current_user),
):
    """Create a new timetable slot with strict overlap validation."""
    if user.role not in ("teacher", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher or admin role required to manage timetable",
        )

    # If teacher, verify active assignment to the class
    if user.role != "admin":
        ta_repo = TeacherAssignmentRepository()
        assignment = await ta_repo.find_existing(payload.class_id, user.id, active_only=True)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not assigned to teach this class",
            )
        if payload.teacher_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot schedule slots for another teacher",
            )

    if payload.start_time >= payload.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_time must be earlier than end_time",
        )

    timetable_repo = TimetableRepository()
    conflict = await timetable_repo.find_overlap(
        day_of_week=payload.day_of_week,
        start_time=payload.start_time,
        end_time=payload.end_time,
        class_id=payload.class_id,
        teacher_id=payload.teacher_id,
    )
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Schedule conflict: overlapping slot {conflict.id} on day {payload.day_of_week} "
                f"between {conflict.start_time} and {conflict.end_time}"
            ),
        )

    slot_id = timetable_repo.new_id()
    slot_db = TimetableSlotDB(
        id=slot_id,
        class_id=payload.class_id,
        teacher_id=payload.teacher_id,
        day_of_week=payload.day_of_week,
        start_time=payload.start_time,
        end_time=payload.end_time,
        room=payload.room,
    )
    created = await timetable_repo.create(slot_db)
    return created


@router.get("/my-schedule", response_model=List[TimetableSlotPublic])
async def get_my_schedule(
    user: UserPublic = Depends(get_current_user),
):
    """Retrieve personal timetable schedule based on student enrollment or teacher assignment."""
    timetable_repo = TimetableRepository()

    if user.role == "student":
        enrollment_repo = StudentEnrollmentRepository()
        enrollments = await enrollment_repo.list_for_student(user.id)
        class_ids = [e.class_id for e in enrollments]
        return await timetable_repo.list_by_classes(class_ids)

    if user.role == "teacher":
        return await timetable_repo.list_by_teacher(user.id)

    # Admin: return all slots
    return await timetable_repo.list_all()


@router.get("/class/{class_id}", response_model=List[TimetableSlotPublic])
async def get_class_schedule(
    class_id: str,
    user: UserPublic = Depends(get_current_user),
):
    """Retrieve schedule for a specific class with fail-closed security enforcement."""
    if user.role == "student":
        enrollment_repo = StudentEnrollmentRepository()
        enrollment = await enrollment_repo.find_existing(class_id, user.id)
        if not enrollment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Class not found or not enrolled",
            )

    elif user.role == "teacher":
        ta_repo = TeacherAssignmentRepository()
        assignment = await ta_repo.find_existing(class_id, user.id, active_only=True)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Class not found or not assigned",
            )

    timetable_repo = TimetableRepository()
    return await timetable_repo.list_by_class(class_id)


@router.put("/slots/{slot_id}", response_model=TimetableSlotPublic)
@router.patch("/slots/{slot_id}", response_model=TimetableSlotPublic)
async def update_timetable_slot(
    slot_id: str,
    payload: TimetableSlotUpdate,
    user: UserPublic = Depends(get_current_user),
):
    """Update a timetable slot with ownership and overlap checks."""
    if user.role not in ("teacher", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher or admin role required",
        )

    timetable_repo = TimetableRepository()
    slot = await timetable_repo.get_by_id(slot_id)
    if not slot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slot not found")

    if user.role != "admin":
        ta_repo = TeacherAssignmentRepository()
        assignment = await ta_repo.find_existing(slot.class_id, user.id, active_only=True)
        if not assignment or slot.teacher_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to edit this slot",
            )

    new_day = payload.day_of_week if payload.day_of_week is not None else slot.day_of_week
    new_start = payload.start_time if payload.start_time is not None else slot.start_time
    new_end = payload.end_time if payload.end_time is not None else slot.end_time

    if new_start >= new_end:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_time must be earlier than end_time",
        )

    conflict = await timetable_repo.find_overlap(
        day_of_week=new_day,
        start_time=new_start,
        end_time=new_end,
        class_id=slot.class_id,
        teacher_id=slot.teacher_id,
        exclude_slot_id=slot_id,
    )
    if conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Schedule conflict: overlapping slot {conflict.id} on day {new_day} "
                f"between {conflict.start_time} and {conflict.end_time}"
            ),
        )

    update_fields = {}
    if payload.day_of_week is not None:
        update_fields["day_of_week"] = payload.day_of_week
    if payload.start_time is not None:
        update_fields["start_time"] = payload.start_time
    if payload.end_time is not None:
        update_fields["end_time"] = payload.end_time
    if payload.room is not None:
        update_fields["room"] = payload.room

    updated = await timetable_repo.update(slot_id, update_fields)
    return updated


@router.delete("/slots/{slot_id}")
async def delete_timetable_slot(
    slot_id: str,
    user: UserPublic = Depends(get_current_user),
):
    """Delete a timetable slot."""
    if user.role not in ("teacher", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher or admin role required",
        )

    timetable_repo = TimetableRepository()
    slot = await timetable_repo.get_by_id(slot_id)
    if not slot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slot not found")

    if user.role != "admin":
        ta_repo = TeacherAssignmentRepository()
        assignment = await ta_repo.find_existing(slot.class_id, user.id, active_only=True)
        if not assignment or slot.teacher_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this slot",
            )

    deleted = await timetable_repo.delete(slot_id)
    return {"status": "deleted", "id": slot_id}
