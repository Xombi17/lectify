"""Admin routes — hierarchy CRUD, guarded by require_admin."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from core.deps import (
    AUDIT_ASSIGN_TEACHER,
    AUDIT_CREATE,
    AUDIT_DELETE,
    AUDIT_UNASSIGN_TEACHER,
    AUDIT_UPDATE,
    get_admin_user,
    log_audit,
    require_admin,
)
from models.academic import (
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
from models.user import UserPublic
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
async def create_institution(payload: InstitutionCreate, admin: UserPublic = Depends(get_admin_user)):
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
    result = await repo.create(institution)

    await log_audit(
        action=AUDIT_CREATE,
        entity_type="institution",
        entity_id=result.id,
        details=f"Created institution: {payload.name} ({payload.code})",
        admin_id=admin.id,
    )

    return result


@router.get("/institutions/{institution_id}", response_model=InstitutionPublic)
async def get_institution(institution_id: str):
    repo = InstitutionRepository()
    result = await repo.get_by_id(institution_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return result


@router.put("/institutions/{institution_id}", response_model=InstitutionPublic)
async def update_institution(institution_id: str, payload: InstitutionCreate, admin: UserPublic = Depends(get_admin_user)):
    repo = InstitutionRepository()
    result = await repo.update(institution_id, payload.model_dump())
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    await log_audit(
        action=AUDIT_UPDATE,
        entity_type="institution",
        entity_id=institution_id,
        details=f"Updated institution: {payload.name}",
        admin_id=admin.id,
    )

    return result


@router.delete("/institutions/{institution_id}")
async def delete_institution(institution_id: str, admin: UserPublic = Depends(get_admin_user)):
    repo = InstitutionRepository()
    entity = await repo.get_by_id(institution_id)
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    await log_audit(
        action=AUDIT_DELETE,
        entity_type="institution",
        entity_id=institution_id,
        details=f"Deleted institution: {entity.name}",
        admin_id=admin.id,
    )

    success = await repo.delete(institution_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return {"ok": True}


@router.get(
    "/institutions/{institution_id}/years",
    response_model=List[YearPublic],
)
async def list_institution_years(institution_id: str):
    """List all years for an institution."""
    repo = YearRepository()
    return await repo.list_by_institution(institution_id)


# ============================================================================
# Year
# ============================================================================


@router.get("/years", response_model=List[YearPublic])
async def list_years():
    repo = YearRepository()
    return await repo.list_all()


@router.post("/years", response_model=YearPublic, status_code=status.HTTP_201_CREATED)
async def create_year(payload: YearCreate, admin: UserPublic = Depends(get_admin_user)):
    repo = YearRepository()
    from models.academic import YearDB

    year = YearDB(
        id=repo.new_id(),
        institution_id=payload.institution_id,
        number=payload.number,
        name=payload.name,
    )
    result = await repo.create(year)

    await log_audit(
        action=AUDIT_CREATE,
        entity_type="year",
        entity_id=result.id,
        details=f"Created year {payload.number}: {payload.name}",
        admin_id=admin.id,
    )

    return result


@router.get("/years/{year_id}", response_model=YearPublic)
async def get_year(year_id: str):
    repo = YearRepository()
    result = await repo.get_by_id(year_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return result


@router.put("/years/{year_id}", response_model=YearPublic)
async def update_year(year_id: str, payload: YearCreate, admin: UserPublic = Depends(get_admin_user)):
    repo = YearRepository()
    result = await repo.update(year_id, payload.model_dump())
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    await log_audit(
        action=AUDIT_UPDATE,
        entity_type="year",
        entity_id=year_id,
        details=f"Updated year: {payload.name}",
        admin_id=admin.id,
    )

    return result


@router.delete("/years/{year_id}")
async def delete_year(year_id: str, admin: UserPublic = Depends(get_admin_user)):
    repo = YearRepository()
    entity = await repo.get_by_id(year_id)
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    await log_audit(
        action=AUDIT_DELETE,
        entity_type="year",
        entity_id=year_id,
        details=f"Deleted year: {entity.name}",
        admin_id=admin.id,
    )

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
async def create_branch(payload: BranchCreate, admin: UserPublic = Depends(get_admin_user)):
    repo = BranchRepository()
    from models.academic import BranchDB

    branch = BranchDB(
        id=repo.new_id(),
        institution_id=payload.institution_id,
        code=payload.code,
        name=payload.name,
    )
    result = await repo.create(branch)

    await log_audit(
        action=AUDIT_CREATE,
        entity_type="branch",
        entity_id=result.id,
        details=f"Created branch: {payload.name} ({payload.code})",
        admin_id=admin.id,
    )

    return result


@router.get("/branches/{branch_id}", response_model=BranchPublic)
async def get_branch(branch_id: str):
    repo = BranchRepository()
    result = await repo.get_by_id(branch_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return result


@router.put("/branches/{branch_id}", response_model=BranchPublic)
async def update_branch(branch_id: str, payload: BranchCreate, admin: UserPublic = Depends(get_admin_user)):
    repo = BranchRepository()
    result = await repo.update(branch_id, payload.model_dump())
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    await log_audit(
        action=AUDIT_UPDATE,
        entity_type="branch",
        entity_id=branch_id,
        details=f"Updated branch: {payload.name}",
        admin_id=admin.id,
    )

    return result


@router.delete("/branches/{branch_id}")
async def delete_branch(branch_id: str, admin: UserPublic = Depends(get_admin_user)):
    repo = BranchRepository()
    entity = await repo.get_by_id(branch_id)
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    await log_audit(
        action=AUDIT_DELETE,
        entity_type="branch",
        entity_id=branch_id,
        details=f"Deleted branch: {entity.name}",
        admin_id=admin.id,
    )

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
async def create_semester(payload: SemesterCreate, admin: UserPublic = Depends(get_admin_user)):
    repo = SemesterRepository()
    from models.academic import SemesterDB

    semester = SemesterDB(
        id=repo.new_id(),
        year_id=payload.year_id,
        number=payload.number,
        label=payload.label,
    )
    result = await repo.create(semester)

    await log_audit(
        action=AUDIT_CREATE,
        entity_type="semester",
        entity_id=result.id,
        details=f"Created semester {payload.number}: {payload.label}",
        admin_id=admin.id,
    )

    return result


@router.get("/semesters/{semester_id}", response_model=SemesterPublic)
async def get_semester(semester_id: str):
    repo = SemesterRepository()
    result = await repo.get_by_id(semester_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return result


@router.put("/semesters/{semester_id}", response_model=SemesterPublic)
async def update_semester(semester_id: str, payload: SemesterCreate, admin: UserPublic = Depends(get_admin_user)):
    repo = SemesterRepository()
    result = await repo.update(semester_id, payload.model_dump())
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    await log_audit(
        action=AUDIT_UPDATE,
        entity_type="semester",
        entity_id=semester_id,
        details=f"Updated semester: {payload.label}",
        admin_id=admin.id,
    )

    return result


@router.delete("/semesters/{semester_id}")
async def delete_semester(semester_id: str, admin: UserPublic = Depends(get_admin_user)):
    repo = SemesterRepository()
    entity = await repo.get_by_id(semester_id)
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    await log_audit(
        action=AUDIT_DELETE,
        entity_type="semester",
        entity_id=semester_id,
        details=f"Deleted semester: {entity.label}",
        admin_id=admin.id,
    )

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
async def create_subject(payload: SubjectCreate, admin: UserPublic = Depends(get_admin_user)):
    repo = SubjectRepository()
    from models.academic import SubjectDB

    subject = SubjectDB(
        id=repo.new_id(),
        semester_id=payload.semester_id,
        code=payload.code,
        name=payload.name,
        credits=payload.credits,
    )
    result = await repo.create(subject)

    await log_audit(
        action=AUDIT_CREATE,
        entity_type="subject",
        entity_id=result.id,
        details=f"Created subject: {payload.name} ({payload.code})",
        admin_id=admin.id,
    )

    return result


@router.get("/subjects/{subject_id}", response_model=SubjectPublic)
async def get_subject(subject_id: str):
    repo = SubjectRepository()
    result = await repo.get_by_id(subject_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return result


@router.put("/subjects/{subject_id}", response_model=SubjectPublic)
async def update_subject(subject_id: str, payload: SubjectCreate, admin: UserPublic = Depends(get_admin_user)):
    repo = SubjectRepository()
    result = await repo.update(subject_id, payload.model_dump())
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    await log_audit(
        action=AUDIT_UPDATE,
        entity_type="subject",
        entity_id=subject_id,
        details=f"Updated subject: {payload.name}",
        admin_id=admin.id,
    )

    return result


@router.delete("/subjects/{subject_id}")
async def delete_subject(subject_id: str, admin: UserPublic = Depends(get_admin_user)):
    repo = SubjectRepository()
    entity = await repo.get_by_id(subject_id)
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    await log_audit(
        action=AUDIT_DELETE,
        entity_type="subject",
        entity_id=subject_id,
        details=f"Deleted subject: {entity.name}",
        admin_id=admin.id,
    )

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
async def create_division(payload: DivisionCreate, admin: UserPublic = Depends(get_admin_user)):
    repo = DivisionRepository()
    from models.academic import DivisionDB

    division = DivisionDB(
        id=repo.new_id(),
        semester_id=payload.semester_id,
        name=payload.name,
        capacity=payload.capacity,
    )
    result = await repo.create(division)

    await log_audit(
        action=AUDIT_CREATE,
        entity_type="division",
        entity_id=result.id,
        details=f"Created division: {payload.name}",
        admin_id=admin.id,
    )

    return result


@router.get("/divisions/{division_id}", response_model=DivisionPublic)
async def get_division(division_id: str):
    repo = DivisionRepository()
    result = await repo.get_by_id(division_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return result


@router.put("/divisions/{division_id}", response_model=DivisionPublic)
async def update_division(division_id: str, payload: DivisionCreate, admin: UserPublic = Depends(get_admin_user)):
    repo = DivisionRepository()
    result = await repo.update(division_id, payload.model_dump())
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    await log_audit(
        action=AUDIT_UPDATE,
        entity_type="division",
        entity_id=division_id,
        details=f"Updated division: {payload.name}",
        admin_id=admin.id,
    )

    return result


@router.delete("/divisions/{division_id}")
async def delete_division(division_id: str, admin: UserPublic = Depends(get_admin_user)):
    repo = DivisionRepository()
    entity = await repo.get_by_id(division_id)
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    await log_audit(
        action=AUDIT_DELETE,
        entity_type="division",
        entity_id=division_id,
        details=f"Deleted division: {entity.name}",
        admin_id=admin.id,
    )

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
async def create_class(payload: ClassCreate, admin: UserPublic = Depends(get_admin_user)):
    repo = ClassRepository()
    from models.academic import ClassDB

    cls = ClassDB(
        id=repo.new_id(),
        division_id=payload.division_id,
        subject_id=payload.subject_id,
    )
    result = await repo.create(cls)

    await log_audit(
        action=AUDIT_CREATE,
        entity_type="class",
        entity_id=result.id,
        details=f"Created class: {result.id}",
        admin_id=admin.id,
    )

    return result


@router.get("/classes/{class_id}", response_model=ClassPublic)
async def get_class(class_id: str):
    repo = ClassRepository()
    result = await repo.get_by_id(class_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return result


@router.put("/classes/{class_id}", response_model=ClassPublic)
async def update_class(class_id: str, payload: ClassCreate, admin: UserPublic = Depends(get_admin_user)):
    repo = ClassRepository()
    result = await repo.update(class_id, payload.model_dump())
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    await log_audit(
        action=AUDIT_UPDATE,
        entity_type="class",
        entity_id=class_id,
        details=f"Updated class: {class_id}",
        admin_id=admin.id,
    )

    return result


@router.delete("/classes/{class_id}")
async def delete_class(class_id: str, admin: UserPublic = Depends(get_admin_user)):
    repo = ClassRepository()
    entity = await repo.get_by_id(class_id)
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    await log_audit(
        action=AUDIT_DELETE,
        entity_type="class",
        entity_id=class_id,
        details=f"Deleted class: {class_id}",
        admin_id=admin.id,
    )

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
async def assign_teacher(payload: TeacherAssignmentCreate, admin: UserPublic = Depends(get_admin_user)):
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
            await log_audit(
                action=AUDIT_ASSIGN_TEACHER,
                entity_type="assignment",
                entity_id=result.id,
                details=f"Reactivated teacher assignment: class={payload.class_id}, teacher={payload.teacher_id}",
                admin_id=admin.id,
            )
            return result

    from models.academic import TeacherAssignmentDB

    assignment = TeacherAssignmentDB(
        id=repo.new_id(),
        class_id=payload.class_id,
        teacher_id=payload.teacher_id,
        active=True,
    )
    result = await repo.create(assignment)

    await log_audit(
        action=AUDIT_ASSIGN_TEACHER,
        entity_type="assignment",
        entity_id=result.id,
        details=f"Assigned teacher {payload.teacher_id} to class {payload.class_id}",
        admin_id=admin.id,
    )

    return result


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
async def unassign_teacher(assignment_id: str, admin: UserPublic = Depends(get_admin_user)):
    repo = TeacherAssignmentRepository()
    result = await repo.set_active(assignment_id, False)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    await log_audit(
        action=AUDIT_UNASSIGN_TEACHER,
        entity_type="assignment",
        entity_id=assignment_id,
        details=f"Unassigned teacher (assignment: {assignment_id})",
        admin_id=admin.id,
    )

    return {"ok": True}


# ============================================================================
# Audit View Endpoints
# ============================================================================


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

