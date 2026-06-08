"""Academic hierarchy repositories - MongoDB implementation."""
import uuid
from typing import List, Optional

from core.db import get_db
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


# ============================================================================
# Institution Repository
# ============================================================================
def _to_institution(doc: dict) -> InstitutionDB:
    doc.pop("_id", None)
    if isinstance(doc.get("created_at"), str):
        from datetime import datetime
        doc["created_at"] = datetime.fromisoformat(doc["created_at"])
    return InstitutionDB(**doc)


class InstitutionRepository:
    COLLECTION = "institutions"

    def __init__(self):
        self.db = get_db()
        self.col = self.db[self.COLLECTION]

    async def ensure_indexes(self) -> None:
        await self.col.create_index("code", unique=True)

    async def create(self, institution: InstitutionDB) -> InstitutionDB:
        doc = institution.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        await self.col.insert_one(doc)
        return institution

    async def get_by_id(self, institution_id: str) -> Optional[InstitutionDB]:
        doc = await self.col.find_one({"id": institution_id}, {"_id": 0})
        return _to_institution(doc) if doc else None

    async def get_by_code(self, code: str) -> Optional[InstitutionDB]:
        doc = await self.col.find_one({"code": code}, {"_id": 0})
        return _to_institution(doc) if doc else None

    async def list_all(self) -> List[InstitutionDB]:
        cursor = self.col.find({}, {"_id": 0})
        docs = await cursor.to_list(length=None)
        return [_to_institution(d) for d in docs]

    async def update(self, institution_id: str, fields: dict) -> Optional[InstitutionDB]:
        if not fields:
            return await self.get_by_id(institution_id)
        result = await self.col.update_one({"id": institution_id}, {"$set": fields})
        if result.matched_count == 0:
            return None
        return await self.get_by_id(institution_id)

    async def delete(self, institution_id: str) -> bool:
        result = await self.col.delete_one({"id": institution_id})
        return result.deleted_count > 0

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())


# ============================================================================
# Year Repository
# ============================================================================
def _to_year(doc: dict) -> YearDB:
    doc.pop("_id", None)
    if isinstance(doc.get("created_at"), str):
        from datetime import datetime
        doc["created_at"] = datetime.fromisoformat(doc["created_at"])
    return YearDB(**doc)


class YearRepository:
    COLLECTION = "years"

    def __init__(self):
        self.db = get_db()
        self.col = self.db[self.COLLECTION]

    async def ensure_indexes(self) -> None:
        await self.col.create_index([("institution_id", 1), ("number", 1)], unique=True)

    async def create(self, year: YearDB) -> YearDB:
        doc = year.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        await self.col.insert_one(doc)
        return year

    async def get_by_id(self, year_id: str) -> Optional[YearDB]:
        doc = await self.col.find_one({"id": year_id}, {"_id": 0})
        return _to_year(doc) if doc else None

    async def list_by_institution(self, institution_id: str) -> List[YearDB]:
        cursor = self.col.find({"institution_id": institution_id}, {"_id": 0})
        docs = await cursor.to_list(length=None)
        return [_to_year(d) for d in docs]

    async def list_all(self) -> List[YearDB]:
        cursor = self.col.find({}, {"_id": 0})
        docs = await cursor.to_list(length=None)
        return [_to_year(d) for d in docs]

    async def update(self, year_id: str, fields: dict) -> Optional[YearDB]:
        if not fields:
            return await self.get_by_id(year_id)
        result = await self.col.update_one({"id": year_id}, {"$set": fields})
        if result.matched_count == 0:
            return None
        return await self.get_by_id(year_id)

    async def delete(self, year_id: str) -> bool:
        result = await self.col.delete_one({"id": year_id})
        return result.deleted_count > 0

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())


# ============================================================================
# Branch Repository
# ============================================================================
def _to_branch(doc: dict) -> BranchDB:
    doc.pop("_id", None)
    if isinstance(doc.get("created_at"), str):
        from datetime import datetime
        doc["created_at"] = datetime.fromisoformat(doc["created_at"])
    return BranchDB(**doc)


class BranchRepository:
    COLLECTION = "branches"

    def __init__(self):
        self.db = get_db()
        self.col = self.db[self.COLLECTION]

    async def ensure_indexes(self) -> None:
        await self.col.create_index([("institution_id", 1), ("code", 1)], unique=True)

    async def create(self, branch: BranchDB) -> BranchDB:
        doc = branch.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        await self.col.insert_one(doc)
        return branch

    async def get_by_id(self, branch_id: str) -> Optional[BranchDB]:
        doc = await self.col.find_one({"id": branch_id}, {"_id": 0})
        return _to_branch(doc) if doc else None

    async def list_by_institution(self, institution_id: str) -> List[BranchDB]:
        cursor = self.col.find({"institution_id": institution_id}, {"_id": 0})
        docs = await cursor.to_list(length=None)
        return [_to_branch(d) for d in docs]

    async def list_all(self) -> List[BranchDB]:
        cursor = self.col.find({}, {"_id": 0})
        docs = await cursor.to_list(length=None)
        return [_to_branch(d) for d in docs]

    async def update(self, branch_id: str, fields: dict) -> Optional[BranchDB]:
        if not fields:
            return await self.get_by_id(branch_id)
        result = await self.col.update_one({"id": branch_id}, {"$set": fields})
        if result.matched_count == 0:
            return None
        return await self.get_by_id(branch_id)

    async def delete(self, branch_id: str) -> bool:
        result = await self.col.delete_one({"id": branch_id})
        return result.deleted_count > 0

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())


# ============================================================================
# Semester Repository
# ============================================================================
def _to_semester(doc: dict) -> SemesterDB:
    doc.pop("_id", None)
    if isinstance(doc.get("created_at"), str):
        from datetime import datetime
        doc["created_at"] = datetime.fromisoformat(doc["created_at"])
    return SemesterDB(**doc)


class SemesterRepository:
    COLLECTION = "semesters"

    def __init__(self):
        self.db = get_db()
        self.col = self.db[self.COLLECTION]

    async def ensure_indexes(self) -> None:
        await self.col.create_index([("year_id", 1), ("number", 1)], unique=True)

    async def create(self, semester: SemesterDB) -> SemesterDB:
        doc = semester.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        await self.col.insert_one(doc)
        return semester

    async def get_by_id(self, semester_id: str) -> Optional[SemesterDB]:
        doc = await self.col.find_one({"id": semester_id}, {"_id": 0})
        return _to_semester(doc) if doc else None

    async def list_by_year(self, year_id: str) -> List[SemesterDB]:
        cursor = self.col.find({"year_id": year_id}, {"_id": 0})
        docs = await cursor.to_list(length=None)
        return [_to_semester(d) for d in docs]

    async def list_all(self) -> List[SemesterDB]:
        cursor = self.col.find({}, {"_id": 0})
        docs = await cursor.to_list(length=None)
        return [_to_semester(d) for d in docs]

    async def update(self, semester_id: str, fields: dict) -> Optional[SemesterDB]:
        if not fields:
            return await self.get_by_id(semester_id)
        result = await self.col.update_one({"id": semester_id}, {"$set": fields})
        if result.matched_count == 0:
            return None
        return await self.get_by_id(semester_id)

    async def delete(self, semester_id: str) -> bool:
        result = await self.col.delete_one({"id": semester_id})
        return result.deleted_count > 0

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())


# ============================================================================
# Subject Repository
# ============================================================================
def _to_subject(doc: dict) -> SubjectDB:
    doc.pop("_id", None)
    if isinstance(doc.get("created_at"), str):
        from datetime import datetime
        doc["created_at"] = datetime.fromisoformat(doc["created_at"])
    return SubjectDB(**doc)


class SubjectRepository:
    COLLECTION = "subjects"

    def __init__(self):
        self.db = get_db()
        self.col = self.db[self.COLLECTION]

    async def ensure_indexes(self) -> None:
        await self.col.create_index([("semester_id", 1), ("code", 1)], unique=True)

    async def create(self, subject: SubjectDB) -> SubjectDB:
        doc = subject.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        await self.col.insert_one(doc)
        return subject

    async def get_by_id(self, subject_id: str) -> Optional[SubjectDB]:
        doc = await self.col.find_one({"id": subject_id}, {"_id": 0})
        return _to_subject(doc) if doc else None

    async def list_by_semester(self, semester_id: str) -> List[SubjectDB]:
        cursor = self.col.find({"semester_id": semester_id}, {"_id": 0})
        docs = await cursor.to_list(length=None)
        return [_to_subject(d) for d in docs]

    async def list_all(self) -> List[SubjectDB]:
        cursor = self.col.find({}, {"_id": 0})
        docs = await cursor.to_list(length=None)
        return [_to_subject(d) for d in docs]

    async def update(self, subject_id: str, fields: dict) -> Optional[SubjectDB]:
        if not fields:
            return await self.get_by_id(subject_id)
        result = await self.col.update_one({"id": subject_id}, {"$set": fields})
        if result.matched_count == 0:
            return None
        return await self.get_by_id(subject_id)

    async def delete(self, subject_id: str) -> bool:
        result = await self.col.delete_one({"id": subject_id})
        return result.deleted_count > 0

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())


# ============================================================================
# Division Repository
# ============================================================================
def _to_division(doc: dict) -> DivisionDB:
    doc.pop("_id", None)
    if isinstance(doc.get("created_at"), str):
        from datetime import datetime
        doc["created_at"] = datetime.fromisoformat(doc["created_at"])
    return DivisionDB(**doc)


class DivisionRepository:
    COLLECTION = "divisions"

    def __init__(self):
        self.db = get_db()
        self.col = self.db[self.COLLECTION]

    async def ensure_indexes(self) -> None:
        await self.col.create_index([("semester_id", 1), ("name", 1)], unique=True)

    async def create(self, division: DivisionDB) -> DivisionDB:
        doc = division.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        await self.col.insert_one(doc)
        return division

    async def get_by_id(self, division_id: str) -> Optional[DivisionDB]:
        doc = await self.col.find_one({"id": division_id}, {"_id": 0})
        return _to_division(doc) if doc else None

    async def list_by_semester(self, semester_id: str) -> List[DivisionDB]:
        cursor = self.col.find({"semester_id": semester_id}, {"_id": 0})
        docs = await cursor.to_list(length=None)
        return [_to_division(d) for d in docs]

    async def list_all(self) -> List[DivisionDB]:
        cursor = self.col.find({}, {"_id": 0})
        docs = await cursor.to_list(length=None)
        return [_to_division(d) for d in docs]

    async def update(self, division_id: str, fields: dict) -> Optional[DivisionDB]:
        if not fields:
            return await self.get_by_id(division_id)
        result = await self.col.update_one({"id": division_id}, {"$set": fields})
        if result.matched_count == 0:
            return None
        return await self.get_by_id(division_id)

    async def delete(self, division_id: str) -> bool:
        result = await self.col.delete_one({"id": division_id})
        return result.deleted_count > 0

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())


# ============================================================================
# Class Repository
# ============================================================================
def _to_class(doc: dict) -> ClassDB:
    doc.pop("_id", None)
    if isinstance(doc.get("created_at"), str):
        from datetime import datetime
        doc["created_at"] = datetime.fromisoformat(doc["created_at"])
    return ClassDB(**doc)


class ClassRepository:
    COLLECTION = "classes"

    def __init__(self):
        self.db = get_db()
        self.col = self.db[self.COLLECTION]

    async def ensure_indexes(self) -> None:
        await self.col.create_index([("division_id", 1), ("subject_id", 1)], unique=True)

    async def create(self, cls: ClassDB) -> ClassDB:
        doc = cls.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        await self.col.insert_one(doc)
        return cls

    async def get_by_id(self, class_id: str) -> Optional[ClassDB]:
        doc = await self.col.find_one({"id": class_id}, {"_id": 0})
        return _to_class(doc) if doc else None

    async def list_by_division(self, division_id: str) -> List[ClassDB]:
        cursor = self.col.find({"division_id": division_id}, {"_id": 0})
        docs = await cursor.to_list(length=None)
        return [_to_class(d) for d in docs]

    async def list_all(self) -> List[ClassDB]:
        cursor = self.col.find({}, {"_id": 0})
        docs = await cursor.to_list(length=None)
        return [_to_class(d) for d in docs]

    async def update(self, class_id: str, fields: dict) -> Optional[ClassDB]:
        if not fields:
            return await self.get_by_id(class_id)
        result = await self.col.update_one({"id": class_id}, {"$set": fields})
        if result.matched_count == 0:
            return None
        return await self.get_by_id(class_id)

    async def delete(self, class_id: str) -> bool:
        result = await self.col.delete_one({"id": class_id})
        return result.deleted_count > 0

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())


# ============================================================================
# TeacherAssignment Repository
# ============================================================================
def _to_teacher_assignment(doc: dict) -> TeacherAssignmentDB:
    doc.pop("_id", None)
    if isinstance(doc.get("assigned_at"), str):
        from datetime import datetime
        doc["assigned_at"] = datetime.fromisoformat(doc["assigned_at"])
    return TeacherAssignmentDB(**doc)


class TeacherAssignmentRepository:
    COLLECTION = "teacher_assignments"

    def __init__(self):
        self.db = get_db()
        self.col = self.db[self.COLLECTION]

    async def ensure_indexes(self) -> None:
        await self.col.create_index([("class_id", 1), ("teacher_id", 1)], unique=True)

    async def create(self, assignment: TeacherAssignmentDB) -> TeacherAssignmentDB:
        doc = assignment.model_dump()
        doc["assigned_at"] = doc["assigned_at"].isoformat()
        await self.col.insert_one(doc)
        return assignment

    async def get_by_id(self, assignment_id: str) -> Optional[TeacherAssignmentDB]:
        doc = await self.col.find_one({"id": assignment_id}, {"_id": 0})
        return _to_teacher_assignment(doc) if doc else None

    async def list_for_class(self, class_id: str) -> List[TeacherAssignmentDB]:
        cursor = self.col.find({"class_id": class_id, "active": True}, {"_id": 0})
        docs = await cursor.to_list(length=None)
        return [_to_teacher_assignment(d) for d in docs]

    async def list_for_teacher(self, teacher_id: str) -> List[TeacherAssignmentDB]:
        cursor = self.col.find({"teacher_id": teacher_id, "active": True}, {"_id": 0})
        docs = await cursor.to_list(length=None)
        return [_to_teacher_assignment(d) for d in docs]

    async def find_existing(self, class_id: str, teacher_id: str, *, active_only: bool = True) -> Optional[TeacherAssignmentDB]:
        query = {"class_id": class_id, "teacher_id": teacher_id}
        if active_only:
            query["active"] = True
        doc = await self.col.find_one(query, {"_id": 0})
        return _to_teacher_assignment(doc) if doc else None

    async def set_active(self, assignment_id: str, active: bool) -> Optional[TeacherAssignmentDB]:
        result = await self.col.update_one({"id": assignment_id}, {"$set": {"active": active}})
        if result.matched_count == 0:
            return None
        return await self.get_by_id(assignment_id)

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())


# ============================================================================
# StudentEnrollment Repository
# ============================================================================
def _to_student_enrollment(doc: dict) -> StudentEnrollmentDB:
    doc.pop("_id", None)
    if isinstance(doc.get("enrolled_at"), str):
        from datetime import datetime
        doc["enrolled_at"] = datetime.fromisoformat(doc["enrolled_at"])
    return StudentEnrollmentDB(**doc)


class StudentEnrollmentRepository:
    COLLECTION = "student_enrollments"

    def __init__(self):
        self.db = get_db()
        self.col = self.db[self.COLLECTION]

    async def ensure_indexes(self) -> None:
        await self.col.create_index([("class_id", 1), ("student_id", 1)], unique=True)

    async def create(self, enrollment: StudentEnrollmentDB) -> StudentEnrollmentDB:
        doc = enrollment.model_dump()
        doc["enrolled_at"] = doc["enrolled_at"].isoformat()
        await self.col.insert_one(doc)
        return enrollment

    async def get_by_id(self, enrollment_id: str) -> Optional[StudentEnrollmentDB]:
        doc = await self.col.find_one({"id": enrollment_id}, {"_id": 0})
        return _to_student_enrollment(doc) if doc else None

    async def list_for_class(self, class_id: str) -> List[StudentEnrollmentDB]:
        cursor = self.col.find({"class_id": class_id}, {"_id": 0})
        docs = await cursor.to_list(length=None)
        return [_to_student_enrollment(d) for d in docs]

    async def list_for_student(self, student_id: str) -> List[StudentEnrollmentDB]:
        cursor = self.col.find({"student_id": student_id}, {"_id": 0})
        docs = await cursor.to_list(length=None)
        return [_to_student_enrollment(d) for d in docs]

    async def find_existing(self, class_id: str, student_id: str) -> Optional[StudentEnrollmentDB]:
        doc = await self.col.find_one({"class_id": class_id, "student_id": student_id}, {"_id": 0})
        return _to_student_enrollment(doc) if doc else None

    async def delete(self, enrollment_id: str) -> bool:
        result = await self.col.delete_one({"id": enrollment_id})
        return result.deleted_count > 0

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())
