"""Enrollment routes — teacher assignments and student enrollment."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from core.deps import get_current_user, require_admin, require_teacher
from core.rate_limiter import InMemoryRateLimiter
from models.academic import (
    EnrollRequest,
    EnrolledStudent,
    StudentEnrollmentCreate,
    StudentEnrollmentDB,
    StudentEnrollmentPublic,
    TeacherAssignmentCreate,
    TeacherAssignmentPublic,
    TeacherAssignmentDB,
    TeacherClassSummary,
)
from models.user import UserPublic
from repositories.class_repository import ClassRepository
from repositories.division_repository import DivisionRepository
from repositories.institution_repository import InstitutionRepository
from repositories.semester_repository import SemesterRepository
from repositories.student_enrollment_repository import StudentEnrollmentRepository
from repositories.subject_repository import SubjectRepository
from repositories.teacher_assignment_repository import TeacherAssignmentRepository
from repositories.user_repository import UserRepository
from repositories.year_repository import YearRepository

router = APIRouter(prefix="/enrollment", tags=["enrollment"])

# Per-process in-memory rate limiter (replace with Redis in Phase 5)
_enroll_limiter = InMemoryRateLimiter()


async def rate_limit_enroll(request: Request) -> None:
    """Rate limit enrollment endpoint per IP."""
    ip = request.client.host if request.client else "unknown"
    allowed = await _enroll_limiter.check(f"enroll:{ip}", 10, 60)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests",
            headers={"Retry-After": "60"},
        )


class AssignmentUpdate(BaseModel):
    """Update model for teacher assignment - only active status can change."""
    active: bool


@router.post(
    "/assignments",
    response_model=TeacherAssignmentPublic,
    status_code=status.HTTP_201_CREATED,
)
async def assign_teacher(
    payload: TeacherAssignmentCreate,
    _: str = Depends(require_admin),
):
    """Assign a teacher to a class. Returns 409 if active assignment already exists."""
    repo = TeacherAssignmentRepository()

    # Check for existing assignment
    existing = await repo.find_existing(payload.class_id, payload.teacher_id, active_only=True)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Teacher already assigned to this class",
        )

    # Check for inactive existing assignment
    inactive = await repo.find_existing(payload.class_id, payload.teacher_id, active_only=False)
    if inactive and not inactive.active:
        # Reactivate the inactive assignment
        reactivated = await repo.set_active(inactive.id, True)
        if reactivated:
            return TeacherAssignmentPublic(**reactivated.model_dump())

    # Create new assignment
    assignment = TeacherAssignmentDB(
        id=repo.new_id(),
        class_id=payload.class_id,
        teacher_id=payload.teacher_id,
        active=payload.active,
    )
    created = await repo.create(assignment)
    return TeacherAssignmentPublic(**created.model_dump())


@router.get(
    "/assignments/class/{class_id}",
    response_model=List[TeacherAssignmentPublic],
)
async def list_assignments_for_class(
    class_id: str,
    _: str = Depends(require_admin),
):
    """List all active teacher assignments for a class."""
    repo = TeacherAssignmentRepository()
    assignments = await repo.list_for_class(class_id)
    return [TeacherAssignmentPublic(**a.model_dump()) for a in assignments]


@router.get(
    "/assignments/teacher/{teacher_id}",
    response_model=List[TeacherAssignmentPublic],
)
async def list_assignments_for_teacher(
    teacher_id: str,
    _: str = Depends(require_admin),
):
    """List all active teacher assignments for a teacher."""
    repo = TeacherAssignmentRepository()
    assignments = await repo.list_for_teacher(teacher_id)
    return [TeacherAssignmentPublic(**a.model_dump()) for a in assignments]


@router.delete(
    "/assignments/{assignment_id}",
    status_code=status.HTTP_200_OK,
)
async def unassign_teacher(
    assignment_id: str,
    _: str = Depends(require_admin),
):
    """Unassign a teacher from a class (soft delete)."""
    repo = TeacherAssignmentRepository()
    result = await repo.set_active(assignment_id, False)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )
    return {"ok": True}


@router.put(
    "/assignments/{assignment_id}",
    response_model=TeacherAssignmentPublic,
)
async def update_assignment(
    assignment_id: str,
    payload: AssignmentUpdate,
    _: str = Depends(require_admin),
):
    """Update teacher assignment active status."""
    repo = TeacherAssignmentRepository()
    result = await repo.set_active(assignment_id, payload.active)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )
    return TeacherAssignmentPublic(**result.model_dump())


@router.get(
    "/my-assignments",
    response_model=List[TeacherAssignmentPublic],
)
async def my_assignments(
    user: str = Depends(require_teacher),
):
    """List current teacher's active assignments."""
    repo = TeacherAssignmentRepository()
    assignments = await repo.list_for_teacher(user.id)
    return [TeacherAssignmentPublic(**a.model_dump()) for a in assignments]


# ============================================================================
# Student Enrollment Endpoints
# ============================================================================

@router.post(
    "/enroll",
    response_model=StudentEnrollmentPublic,
    status_code=status.HTTP_201_CREATED,
)
async def enroll_student(
    payload: EnrollRequest,
    user = Depends(get_current_user),
    _ = Depends(rate_limit_enroll),
):
    """Enroll the current student in a class. Returns 409 if already enrolled."""
    repo = StudentEnrollmentRepository()

    # Check for existing enrollment
    existing = await repo.find_existing(payload.class_id, user.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student already enrolled in this class",
        )

    # Create new enrollment
    enrollment = StudentEnrollmentDB(
        id=repo.new_id(),
        class_id=payload.class_id,
        student_id=user.id,
    )
    created = await repo.create(enrollment)

    # If token provided, increment QR enrollment count
    if payload.token:
        try:
            from core.security import decode_enrollment_token
            qr_payload = decode_enrollment_token(payload.token)
            qr_class_id = qr_payload["sub"]
            if qr_class_id == payload.class_id:
                from repositories.qr_code_repository import QRCodeRepository
                qr_repo = QRCodeRepository()
                qr = await qr_repo.get_active_for_class(payload.class_id)
                if qr:
                    await qr_repo.increment_enrollment(qr.id)
        except (ValueError, LookupError, HTTPException):
            pass  # Non-critical — enrollment already succeeded

    return StudentEnrollmentPublic(**created.model_dump())


@router.get(
    "/my-enrollments",
    response_model=List[StudentEnrollmentPublic],
)
async def my_enrollments(
    user = Depends(get_current_user),
):
    """List current student's enrollments."""
    repo = StudentEnrollmentRepository()
    enrollments = await repo.list_for_student(user.id)
    return [StudentEnrollmentPublic(**e.model_dump()) for e in enrollments]


@router.delete(
    "/enrollments/{enrollment_id}",
    status_code=status.HTTP_200_OK,
)
async def drop_enrollment(
    enrollment_id: str,
    user = Depends(get_current_user),
):
    """Drop an enrollment. Students can drop their own; admins can remove any."""
    repo = StudentEnrollmentRepository()

    enrollment = await repo.get_by_id(enrollment_id)
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found",
        )

    # Ownership check: students can only drop their own; admins can drop any
    if user.role != "admin" and enrollment.student_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found",
        )

    result = await repo.delete(enrollment_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Enrollment not found",
        )
    return {"ok": True}


# ============================================================================
# Teacher Endpoints for Student Enrollment
# ============================================================================

@router.get(
    "/classes/{class_id}/students",
    response_model=List[StudentEnrollmentPublic],
)
async def list_class_students(
    class_id: str,
    user = Depends(require_teacher),
):
    """List all students enrolled in a class the teacher teaches."""
    # Verify teacher owns this class
    ta_repo = TeacherAssignmentRepository()
    assignments = await ta_repo.list_for_teacher(user.id)
    class_ids = {a.class_id for a in assignments}

    if class_id not in class_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher not assigned to this class",
        )

    repo = StudentEnrollmentRepository()
    enrollments = await repo.list_for_class(class_id)
    return [StudentEnrollmentPublic(**e.model_dump()) for e in enrollments]


# ============================================================================
# Admin Endpoints for Student Enrollment
# ============================================================================

# Admin remove enrollment is handled by the unified drop_enrollment endpoint.
# The role check inside the endpoint allows admins to drop any enrollment.
# ============================================================================
# Teacher Dashboard — Class & Student View
# ============================================================================


@router.get(
    "/my-classes",
    response_model=List[TeacherClassSummary],
)
async def my_classes(
    user: UserPublic = Depends(require_teacher),
):
    """List the current teacher's assigned classes with full hierarchy."""
    ta_repo = TeacherAssignmentRepository()
    assignments = await ta_repo.list_for_teacher(user.id)

    summaries: List[TeacherClassSummary] = []
    for a in assignments:
        cls = await ClassRepository().get_by_id(a.class_id)
        if not cls:
            continue
        subject = await SubjectRepository().get_by_id(cls.subject_id)
        division = await DivisionRepository().get_by_id(cls.division_id)
        semester = await SemesterRepository().get_by_id(division.semester_id) if division else None
        year = await YearRepository().get_by_id(semester.year_id) if semester else None
        institution = await InstitutionRepository().get_by_id(year.institution_id) if year else None

        summaries.append(TeacherClassSummary(
            class_id=a.class_id,
            subject_name=subject.name if subject else "",
            division_name=division.name if division else "",
            semester_label=semester.label if semester else "",
            year_number=year.number if year else 0,
            institution_name=institution.name if institution else "",
            assignment_active=a.active,
            assignment_id=a.id,
        ))

    return summaries


@router.get(
    "/my-classes/{class_id}",
)
async def my_class_detail(
    class_id: str,
    user: UserPublic = Depends(require_teacher),
):
    """Get full detail for a teacher's assigned class."""
    # Verify teacher has active assignment for this class
    ta_repo = TeacherAssignmentRepository()
    assignments = await ta_repo.list_for_teacher(user.id)
    class_ids = {a.class_id for a in assignments}

    if class_id not in class_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher not assigned to this class",
        )

    cls = await ClassRepository().get_by_id(class_id)
    if not cls:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class not found",
        )

    subject = await SubjectRepository().get_by_id(cls.subject_id)
    division = await DivisionRepository().get_by_id(cls.division_id)
    semester = await SemesterRepository().get_by_id(division.semester_id) if division else None
    year = await YearRepository().get_by_id(semester.year_id) if semester else None
    institution = await InstitutionRepository().get_by_id(year.institution_id) if year else None

    # Count enrolled students
    se_repo = StudentEnrollmentRepository()
    students = await se_repo.list_for_class(class_id)

    return {
        "class_id": class_id,
        "subject_name": subject.name if subject else "",
        "division_name": division.name if division else "",
        "semester_label": semester.label if semester else "",
        "year_number": year.number if year else 0,
        "institution_name": institution.name if institution else "",
        "student_count": len(students),
        "students": [StudentEnrollmentPublic(**s.model_dump()) for s in students],
    }


@router.get(
    "/my-classes/{class_id}/students",
    response_model=List[EnrolledStudent],
)
async def my_class_students(
    class_id: str,
    user: UserPublic = Depends(require_teacher),
):
    """List enrolled students for a teacher's assigned class."""
    # Verify teacher assignment
    ta_repo = TeacherAssignmentRepository()
    assignments = await ta_repo.list_for_teacher(user.id)
    class_ids = {a.class_id for a in assignments}

    if class_id not in class_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher not assigned to this class",
        )

    se_repo = StudentEnrollmentRepository()
    enrollments = await se_repo.list_for_class(class_id)

    result: List[EnrolledStudent] = []
    user_repo = UserRepository()
    for e in enrollments:
        student = await user_repo.get_by_id(e.student_id)
        result.append(EnrolledStudent(
            student_id=e.student_id,
            student_name=student.name if student else "Unknown",
            student_email=student.email if student else "",
            enrolled_at=e.enrolled_at,
            enrollment_id=e.id,
        ))

    return result