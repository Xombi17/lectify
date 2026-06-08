"""Admin routes — hierarchy CRUD, guarded by require_admin."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from core.deps import require_admin
from models.academic import (
    AuditLogDB,
    AuditLogPublic,
    BranchCreate,
    BranchPublic,
    ClassCreate,
    ClassPublic,
    DivisionCreate,
    DivisionPublic,
    InstitutionCreate,
    InstitutionPublic,
    SemesterCreate,
    SemesterPublic,
    SubjectCreate,
    SubjectPublic,
    TeacherAssignmentCreate,
    TeacherAssignmentPublic,
    YearCreate,
    YearPublic,
)
from repositories.audit_log_repository import AuditLogRepository
from repositories.branch_repository import BranchRepository
from repositories.class_repository import ClassRepository
from repositories.division_repository import DivisionRepository
from repositories.institution_repository import InstitutionRepository
from repositories.semester_repository import SemesterRepository
from repositories.subject_repository import SubjectRepository
from repositories.teacher_assignment_repository import TeacherAssignmentRepository
from repositories.year_repository import YearRepository

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


# ============================================================================
# Institution
# ============================================================================


@router.get("/institutions", response_model=List[InstitutionPublic])
async def list_institutions():
    repo = InstitutionRepository()
    return await repo.list_all()


@router.post(
    "/institutions",
    response_model=InstitutionPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_institution(payload: InstitutionCreate):
    repo = InstitutionRepository()
    existing = await repo.get_by_code(payload.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Institution with this code already exists",
        )
    from models.academic import InstitutionDB

    institution = InstitutionDB(
        id=repo.new_id(),
        name=payload.name,
        code=payload.code,
        address=payload.address,
    )
    return await repo.create(institution)


@router.get("/institutions/{institution_id}", response_model=InstitutionPublic)
async def get_institution(institution_id: str):
    repo = InstitutionRepository()
    result = await repo.get_by_id(institution_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return result


@router.put("/institutions/{institution_id}", response_model=InstitutionPublic)
async def update_institution(institution_id: str, payload: InstitutionCreate):
    repo = InstitutionRepository()
    result = await repo.update(institution_id, payload.model_dump())
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return result


@router.delete("/institutions/{institution_id}")
async def delete_institution(institution_id: str):
    repo = InstitutionRepository()
    success = await repo.delete(institution_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return {"ok": True}


# ============================================================================
# Year
# ============================================================================


@router.get("/years", response_model=List[YearPublic])
async def list_years():
    repo = YearRepository()
    return await repo.list_all()


@router.post("/years", response_model=YearPublic, status_code=status.HTTP_201_CREATED)
async def create_year(payload: YearCreate):
    repo = YearRepository()
    from models.academic import YearDB

    year = YearDB(
        id=repo.new_id(),
        institution_id=payload.institution_id,
        number=payload.number,
        name=payload.name,
    )
    return await repo.create(year)


@router.get("/years/{year_id}", response_model=YearPublic)
async def get_year(year_id: str):
    repo = YearRepository()
    result = await repo.get_by_id(year_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return result


@router.put("/years/{year_id}", response_model=YearPublic)
async def update_year(year_id: str, payload: YearCreate):
    repo = YearRepository()
    result = await repo.update(year_id, payload.model_dump())
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return result


@router.delete("/years/{year_id}")
async def delete_year(year_id: str):
    repo = YearRepository()
    success = await repo.delete(year_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return {"ok": True}


# ============================================================================
# Branch
# ============================================================================


@router.get("/branches", response_model=List[BranchPublic])
async def list_branches():
    repo = BranchRepository()
    return await repo.list_all()


@router.post(
    "/branches",
    response_model=BranchPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_branch(payload: BranchCreate):
    repo = BranchRepository()
    from models.academic import BranchDB

    branch = BranchDB(
        id=repo.new_id(),
        institution_id=payload.institution_id,
        code=payload.code,
        name=payload.name,
    )
    return await repo.create(branch)


@router.get("/branches/{branch_id}", response_model=BranchPublic)
async def get_branch(branch_id: str):
    repo = BranchRepository()
    result = await repo.get_by_id(branch_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return result


@router.put("/branches/{branch_id}", response_model=BranchPublic)
async def update_branch(branch_id: str, payload: BranchCreate):
    repo = BranchRepository()
    result = await repo.update(branch_id, payload.model_dump())
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return result


@router.delete("/branches/{branch_id}")
async def delete_branch(branch_id: str):
    repo = BranchRepository()
    success = await repo.delete(branch_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return {"ok": True}


@router.get(
    "/institutions/{institution_id}/branches",
    response_model=List[BranchPublic],
)
async def list_institution_branches(institution_id: str):
    repo = BranchRepository()
    return await repo.list_by_institution(institution_id)


# ============================================================================
# Semester
# ============================================================================


@router.get("/semesters", response_model=List[SemesterPublic])
async def list_semesters():
    repo = SemesterRepository()
    return await repo.list_all()


@router.post(
    "/semesters",
    response_model=SemesterPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_semester(payload: SemesterCreate):
    repo = SemesterRepository()
    from models.academic import SemesterDB

    semester = SemesterDB(
        id=repo.new_id(),
        year_id=payload.year_id,
        number=payload.number,
        label=payload.label,
    )
    return await repo.create(semester)


@router.get("/semesters/{semester_id}", response_model=SemesterPublic)
async def get_semester(semester_id: str):
    repo = SemesterRepository()
    result = await repo.get_by_id(semester_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return result


@router.put("/semesters/{semester_id}", response_model=SemesterPublic)
async def update_semester(semester_id: str, payload: SemesterCreate):
    repo = SemesterRepository()
    result = await repo.update(semester_id, payload.model_dump())
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return result


@router.delete("/semesters/{semester_id}")
async def delete_semester(semester_id: str):
    repo = SemesterRepository()
    success = await repo.delete(semester_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return {"ok": True}


@router.get(
    "/years/{year_id}/semesters",
    response_model=List[SemesterPublic],
)
async def list_year_semesters(year_id: str):
    repo = SemesterRepository()
    return await repo.list_by_year(year_id)


# ============================================================================
# Subject
# ============================================================================


@router.get("/subjects", response_model=List[SubjectPublic])
async def list_subjects():
    repo = SubjectRepository()
    return await repo.list_all()


@router.post(
    "/subjects",
    response_model=SubjectPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_subject(payload: SubjectCreate):
    repo = SubjectRepository()
    from models.academic import SubjectDB

    subject = SubjectDB(
        id=repo.new_id(),
        semester_id=payload.semester_id,
        code=payload.code,
        name=payload.name,
        credits=payload.credits,
    )
    return await repo.create(subject)


@router.get("/subjects/{subject_id}", response_model=SubjectPublic)
async def get_subject(subject_id: str):
    repo = SubjectRepository()
    result = await repo.get_by_id(subject_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return result


@router.put("/subjects/{subject_id}", response_model=SubjectPublic)
async def update_subject(subject_id: str, payload: SubjectCreate):
    repo = SubjectRepository()
    result = await repo.update(subject_id, payload.model_dump())
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return result


@router.delete("/subjects/{subject_id}")
async def delete_subject(subject_id: str):
    repo = SubjectRepository()
    success = await repo.delete(subject_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return {"ok": True}


@router.get(
    "/semesters/{semester_id}/subjects",
    response_model=List[SubjectPublic],
)
async def list_semester_subjects(semester_id: str):
    repo = SubjectRepository()
    return await repo.list_by_semester(semester_id)


# ============================================================================
# Division
# ============================================================================


@router.get("/divisions", response_model=List[DivisionPublic])
async def list_divisions():
    repo = DivisionRepository()
    return await repo.list_all()


@router.post(
    "/divisions",
    response_model=DivisionPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_division(payload: DivisionCreate):
    repo = DivisionRepository()
    from models.academic import DivisionDB

    division = DivisionDB(
        id=repo.new_id(),
        semester_id=payload.semester_id,
        name=payload.name,
        capacity=payload.capacity,
    )
    return await repo.create(division)


@router.get("/divisions/{division_id}", response_model=DivisionPublic)
async def get_division(division_id: str):
    repo = DivisionRepository()
    result = await repo.get_by_id(division_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return result


@router.put("/divisions/{division_id}", response_model=DivisionPublic)
async def update_division(division_id: str, payload: DivisionCreate):
    repo = DivisionRepository()
    result = await repo.update(division_id, payload.model_dump())
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return result


@router.delete("/divisions/{division_id}")
async def delete_division(division_id: str):
    repo = DivisionRepository()
    success = await repo.delete(division_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return {"ok": True}


@router.get(
    "/semesters/{semester_id}/divisions",
    response_model=List[DivisionPublic],
)
async def list_semester_divisions(semester_id: str):
    repo = DivisionRepository()
    return await repo.list_by_semester(semester_id)


# ============================================================================
# Class
# ============================================================================


@router.get("/classes", response_model=List[ClassPublic])
async def list_classes():
    repo = ClassRepository()
    return await repo.list_all()


@router.post(
    "/classes",
    response_model=ClassPublic,
    status_code=status.HTTP_201_CREATED,
)
async def create_class(payload: ClassCreate):
    repo = ClassRepository()
    from models.academic import ClassDB

    cls = ClassDB(
        id=repo.new_id(),
        division_id=payload.division_id,
        subject_id=payload.subject_id,
    )
    return await repo.create(cls)


@router.get("/classes/{class_id}", response_model=ClassPublic)
async def get_class(class_id: str):
    repo = ClassRepository()
    result = await repo.get_by_id(class_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return result


@router.put("/classes/{class_id}", response_model=ClassPublic)
async def update_class(class_id: str, payload: ClassCreate):
    repo = ClassRepository()
    result = await repo.update(class_id, payload.model_dump())
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return result


@router.delete("/classes/{class_id}")
async def delete_class(class_id: str):
    repo = ClassRepository()
    success = await repo.delete(class_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return {"ok": True}


@router.get(
    "/divisions/{division_id}/classes",
    response_model=List[ClassPublic],
)
async def list_division_classes(division_id: str):
    repo = ClassRepository()
    return await repo.list_by_division(division_id)


# ============================================================================
# TeacherAssignment
# ============================================================================


@router.post(
    "/assignments",
    response_model=TeacherAssignmentPublic,
    status_code=status.HTTP_201_CREATED,
)
async def assign_teacher(payload: TeacherAssignmentCreate):
    repo = TeacherAssignmentRepository()
    existing = await repo.find_existing(payload.class_id, payload.teacher_id)
    if existing:
        if existing.active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Teacher already assigned to this class",
            )
        result = await repo.set_active(existing.id, True)
        if result:
            return result

    from models.academic import TeacherAssignmentDB

    assignment = TeacherAssignmentDB(
        id=repo.new_id(),
        class_id=payload.class_id,
        teacher_id=payload.teacher_id,
        active=True,
    )
    return await repo.create(assignment)


@router.get(
    "/assignments/class/{class_id}",
    response_model=List[TeacherAssignmentPublic],
)
async def list_class_assignments(class_id: str):
    repo = TeacherAssignmentRepository()
    return await repo.list_for_class(class_id)


@router.get(
    "/assignments/teacher/{teacher_id}",
    response_model=List[TeacherAssignmentPublic],
)
async def list_teacher_assignments(teacher_id: str):
    repo = TeacherAssignmentRepository()
    return await repo.list_for_teacher(teacher_id)


@router.delete("/assignments/{assignment_id}")
async def unassign_teacher(assignment_id: str):
    repo = TeacherAssignmentRepository()
    result = await repo.set_active(assignment_id, False)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return {"ok": True}


# ============================================================================
# Audit Helper & View Endpoints
# ============================================================================


async def _log_action(
    admin_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    details: Optional[str] = None,
):
    """Record an admin action in the audit log."""
    repo = AuditLogRepository()
    entry = AuditLogDB(
        id=repo.new_id(),
        admin_id=admin_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )
    await repo.create(entry)


@router.get("/audit-logs", response_model=List[AuditLogPublic])
async def list_audit_logs():
    repo = AuditLogRepository()
    return await repo.list_all()


@router.get(
    "/audit-logs/entity/{entity_type}/{entity_id}",
    response_model=List[AuditLogPublic],
)
async def list_entity_audit_logs(entity_type: str, entity_id: str):
    repo = AuditLogRepository()
    return await repo.list_by_entity(entity_type, entity_id)

