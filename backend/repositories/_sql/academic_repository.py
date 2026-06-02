"""Academic hierarchy repositories - SQLAlchemy (async) implementation."""
import uuid
from typing import List, Optional

from sqlalchemy import select

from core.sql_db import session_maker
from models.academic import (
    InstitutionDB,
    YearDB,
    BranchDB,
    SemesterDB,
    SubjectDB,
    DivisionDB,
    ClassDB,
    TeacherAssignmentDB,
    StudentEnrollmentDB,
)
from models.orm import (
    InstitutionORM,
    YearORM,
    BranchORM,
    SemesterORM,
    SubjectORM,
    DivisionORM,
    ClassORM,
    TeacherAssignmentORM,
    StudentEnrollmentORM,
)


# ============================================================================
# Institution Repository
# ============================================================================
def _to_institution(row: InstitutionORM) -> InstitutionDB:
    return InstitutionDB(
        id=row.id,
        name=row.name,
        code=row.code,
        address=row.address,
        created_at=row.created_at,
    )


class InstitutionRepository:
    async def ensure_indexes(self) -> None:
        return None  # ORM column indexes handle this

    async def create(self, institution: InstitutionDB) -> InstitutionDB:
        async with session_maker()() as s, s.begin():
            s.add(InstitutionORM(
                id=institution.id,
                name=institution.name,
                code=institution.code,
                address=institution.address,
                created_at=institution.created_at,
            ))
        return institution

    async def get_by_id(self, institution_id: str) -> Optional[InstitutionDB]:
        async with session_maker()() as s:
            row = await s.get(InstitutionORM, institution_id)
            return _to_institution(row) if row else None

    async def get_by_code(self, code: str) -> Optional[InstitutionDB]:
        async with session_maker()() as s:
            stmt = select(InstitutionORM).where(InstitutionORM.code == code)
            row = (await s.execute(stmt)).scalar_one_or_none()
            return _to_institution(row) if row else None

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())


# ============================================================================
# Year Repository
# ============================================================================
def _to_year(row: YearORM) -> YearDB:
    return YearDB(
        id=row.id,
        institution_id=row.institution_id,
        number=row.number,
        name=row.name,
        created_at=row.created_at,
    )


class YearRepository:
    async def ensure_indexes(self) -> None:
        return None

    async def create(self, year: YearDB) -> YearDB:
        async with session_maker()() as s, s.begin():
            s.add(YearORM(
                id=year.id,
                institution_id=year.institution_id,
                number=year.number,
                name=year.name,
                created_at=year.created_at,
            ))
        return year

    async def get_by_id(self, year_id: str) -> Optional[YearDB]:
        async with session_maker()() as s:
            row = await s.get(YearORM, year_id)
            return _to_year(row) if row else None

    async def list_by_institution(self, institution_id: str) -> List[YearDB]:
        async with session_maker()() as s:
            stmt = select(YearORM).where(YearORM.institution_id == institution_id)
            rows = (await s.execute(stmt)).scalars().all()
            return [_to_year(r) for r in rows]

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())


# ============================================================================
# Branch Repository
# ============================================================================
def _to_branch(row: BranchORM) -> BranchDB:
    return BranchDB(
        id=row.id,
        institution_id=row.institution_id,
        code=row.code,
        name=row.name,
        created_at=row.created_at,
    )


class BranchRepository:
    async def ensure_indexes(self) -> None:
        return None

    async def create(self, branch: BranchDB) -> BranchDB:
        async with session_maker()() as s, s.begin():
            s.add(BranchORM(
                id=branch.id,
                institution_id=branch.institution_id,
                code=branch.code,
                name=branch.name,
                created_at=branch.created_at,
            ))
        return branch

    async def get_by_id(self, branch_id: str) -> Optional[BranchDB]:
        async with session_maker()() as s:
            row = await s.get(BranchORM, branch_id)
            return _to_branch(row) if row else None

    async def list_by_institution(self, institution_id: str) -> List[BranchDB]:
        async with session_maker()() as s:
            stmt = select(BranchORM).where(BranchORM.institution_id == institution_id)
            rows = (await s.execute(stmt)).scalars().all()
            return [_to_branch(r) for r in rows]

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())


# ============================================================================
# Semester Repository
# ============================================================================
def _to_semester(row: SemesterORM) -> SemesterDB:
    return SemesterDB(
        id=row.id,
        year_id=row.year_id,
        number=row.number,
        label=row.label,
        created_at=row.created_at,
    )


class SemesterRepository:
    async def ensure_indexes(self) -> None:
        return None

    async def create(self, semester: SemesterDB) -> SemesterDB:
        async with session_maker()() as s, s.begin():
            s.add(SemesterORM(
                id=semester.id,
                year_id=semester.year_id,
                number=semester.number,
                label=semester.label,
                created_at=semester.created_at,
            ))
        return semester

    async def get_by_id(self, semester_id: str) -> Optional[SemesterDB]:
        async with session_maker()() as s:
            row = await s.get(SemesterORM, semester_id)
            return _to_semester(row) if row else None

    async def list_by_year(self, year_id: str) -> List[SemesterDB]:
        async with session_maker()() as s:
            stmt = select(SemesterORM).where(SemesterORM.year_id == year_id)
            rows = (await s.execute(stmt)).scalars().all()
            return [_to_semester(r) for r in rows]

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())


# ============================================================================
# Subject Repository
# ============================================================================
def _to_subject(row: SubjectORM) -> SubjectDB:
    return SubjectDB(
        id=row.id,
        semester_id=row.semester_id,
        code=row.code,
        name=row.name,
        credits=row.credits,
        created_at=row.created_at,
    )


class SubjectRepository:
    async def ensure_indexes(self) -> None:
        return None

    async def create(self, subject: SubjectDB) -> SubjectDB:
        async with session_maker()() as s, s.begin():
            s.add(SubjectORM(
                id=subject.id,
                semester_id=subject.semester_id,
                code=subject.code,
                name=subject.name,
                credits=subject.credits,
                created_at=subject.created_at,
            ))
        return subject

    async def get_by_id(self, subject_id: str) -> Optional[SubjectDB]:
        async with session_maker()() as s:
            row = await s.get(SubjectORM, subject_id)
            return _to_subject(row) if row else None

    async def list_by_semester(self, semester_id: str) -> List[SubjectDB]:
        async with session_maker()() as s:
            stmt = select(SubjectORM).where(SubjectORM.semester_id == semester_id)
            rows = (await s.execute(stmt)).scalars().all()
            return [_to_subject(r) for r in rows]

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())


# ============================================================================
# Division Repository
# ============================================================================
def _to_division(row: DivisionORM) -> DivisionDB:
    return DivisionDB(
        id=row.id,
        semester_id=row.semester_id,
        name=row.name,
        capacity=row.capacity,
        created_at=row.created_at,
    )


class DivisionRepository:
    async def ensure_indexes(self) -> None:
        return None

    async def create(self, division: DivisionDB) -> DivisionDB:
        async with session_maker()() as s, s.begin():
            s.add(DivisionORM(
                id=division.id,
                semester_id=division.semester_id,
                name=division.name,
                capacity=division.capacity,
                created_at=division.created_at,
            ))
        return division

    async def get_by_id(self, division_id: str) -> Optional[DivisionDB]:
        async with session_maker()() as s:
            row = await s.get(DivisionORM, division_id)
            return _to_division(row) if row else None

    async def list_by_semester(self, semester_id: str) -> List[DivisionDB]:
        async with session_maker()() as s:
            stmt = select(DivisionORM).where(DivisionORM.semester_id == semester_id)
            rows = (await s.execute(stmt)).scalars().all()
            return [_to_division(r) for r in rows]

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())


# ============================================================================
# Class Repository
# ============================================================================
def _to_class(row: ClassORM) -> ClassDB:
    return ClassDB(
        id=row.id,
        division_id=row.division_id,
        subject_id=row.subject_id,
        created_at=row.created_at,
    )


class ClassRepository:
    async def ensure_indexes(self) -> None:
        return None

    async def create(self, cls: ClassDB) -> ClassDB:
        async with session_maker()() as s, s.begin():
            s.add(ClassORM(
                id=cls.id,
                division_id=cls.division_id,
                subject_id=cls.subject_id,
                created_at=cls.created_at,
            ))
        return cls

    async def get_by_id(self, class_id: str) -> Optional[ClassDB]:
        async with session_maker()() as s:
            row = await s.get(ClassORM, class_id)
            return _to_class(row) if row else None

    async def list_by_division(self, division_id: str) -> List[ClassDB]:
        async with session_maker()() as s:
            stmt = select(ClassORM).where(ClassORM.division_id == division_id)
            rows = (await s.execute(stmt)).scalars().all()
            return [_to_class(r) for r in rows]

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())


# ============================================================================
# TeacherAssignment Repository
# ============================================================================
def _to_teacher_assignment(row: TeacherAssignmentORM) -> TeacherAssignmentDB:
    return TeacherAssignmentDB(
        id=row.id,
        class_id=row.class_id,
        teacher_id=row.teacher_id,
        active=row.active,
        assigned_at=row.assigned_at,
    )


class TeacherAssignmentRepository:
    async def ensure_indexes(self) -> None:
        return None

    async def create(self, assignment: TeacherAssignmentDB) -> TeacherAssignmentDB:
        async with session_maker()() as s, s.begin():
            s.add(TeacherAssignmentORM(
                id=assignment.id,
                class_id=assignment.class_id,
                teacher_id=assignment.teacher_id,
                active=assignment.active,
                assigned_at=assignment.assigned_at,
            ))
        return assignment

    async def get_by_id(self, assignment_id: str) -> Optional[TeacherAssignmentDB]:
        async with session_maker()() as s:
            row = await s.get(TeacherAssignmentORM, assignment_id)
            return _to_teacher_assignment(row) if row else None

    async def list_for_class(self, class_id: str) -> List[TeacherAssignmentDB]:
        async with session_maker()() as s:
            stmt = select(TeacherAssignmentORM).where(
                (TeacherAssignmentORM.class_id == class_id) &
                (TeacherAssignmentORM.active.is_(True))
            )
            rows = (await s.execute(stmt)).scalars().all()
            return [_to_teacher_assignment(r) for r in rows]

    async def list_for_teacher(self, teacher_id: str) -> List[TeacherAssignmentDB]:
        async with session_maker()() as s:
            stmt = select(TeacherAssignmentORM).where(
                (TeacherAssignmentORM.teacher_id == teacher_id) &
                (TeacherAssignmentORM.active.is_(True))
            )
            rows = (await s.execute(stmt)).scalars().all()
            return [_to_teacher_assignment(r) for r in rows]

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())


# ============================================================================
# StudentEnrollment Repository
# ============================================================================
def _to_student_enrollment(row: StudentEnrollmentORM) -> StudentEnrollmentDB:
    return StudentEnrollmentDB(
        id=row.id,
        class_id=row.class_id,
        student_id=row.student_id,
        enrolled_at=row.enrolled_at,
    )


class StudentEnrollmentRepository:
    async def ensure_indexes(self) -> None:
        return None

    async def create(self, enrollment: StudentEnrollmentDB) -> StudentEnrollmentDB:
        async with session_maker()() as s, s.begin():
            s.add(StudentEnrollmentORM(
                id=enrollment.id,
                class_id=enrollment.class_id,
                student_id=enrollment.student_id,
                enrolled_at=enrollment.enrolled_at,
            ))
        return enrollment

    async def get_by_id(self, enrollment_id: str) -> Optional[StudentEnrollmentDB]:
        async with session_maker()() as s:
            row = await s.get(StudentEnrollmentORM, enrollment_id)
            return _to_student_enrollment(row) if row else None

    async def list_for_class(self, class_id: str) -> List[StudentEnrollmentDB]:
        async with session_maker()() as s:
            stmt = select(StudentEnrollmentORM).where(StudentEnrollmentORM.class_id == class_id)
            rows = (await s.execute(stmt)).scalars().all()
            return [_to_student_enrollment(r) for r in rows]

    async def list_for_student(self, student_id: str) -> List[StudentEnrollmentDB]:
        async with session_maker()() as s:
            stmt = select(StudentEnrollmentORM).where(StudentEnrollmentORM.student_id == student_id)
            rows = (await s.execute(stmt)).scalars().all()
            return [_to_student_enrollment(r) for r in rows]

    async def find_existing(self, class_id: str, student_id: str) -> Optional[StudentEnrollmentDB]:
        async with session_maker()() as s:
            stmt = select(StudentEnrollmentORM).where(
                (StudentEnrollmentORM.class_id == class_id) &
                (StudentEnrollmentORM.student_id == student_id)
            )
            row = (await s.execute(stmt)).scalar_one_or_none()
            return _to_student_enrollment(row) if row else None

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())
