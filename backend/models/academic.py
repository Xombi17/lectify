"""Pydantic models for academic hierarchy entities."""
from datetime import date, datetime, timezone
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


# ============================================================================
# Institution
# ============================================================================
class InstitutionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    code: str = Field(..., min_length=1, max_length=32)
    address: Optional[str] = Field(None, max_length=500)


class InstitutionDB(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    code: str
    address: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class InstitutionPublic(BaseModel):
    id: str
    name: str
    code: str
    address: Optional[str]
    created_at: datetime


# ============================================================================
# Year
# ============================================================================
class YearCreate(BaseModel):
    institution_id: str
    number: int = Field(..., gt=0, le=10)
    name: str = Field(..., min_length=1, max_length=120)


class YearDB(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    institution_id: str
    number: int
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class YearPublic(BaseModel):
    id: str
    institution_id: str
    number: int
    name: str
    created_at: datetime


# ============================================================================
# Branch
# ============================================================================
class BranchCreate(BaseModel):
    institution_id: str
    code: str = Field(..., min_length=1, max_length=32)
    name: str = Field(..., min_length=1, max_length=120)


class BranchDB(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    institution_id: str
    code: str
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BranchPublic(BaseModel):
    id: str
    institution_id: str
    code: str
    name: str
    created_at: datetime


# ============================================================================
# Semester
# ============================================================================
class SemesterCreate(BaseModel):
    year_id: str
    number: int = Field(..., gt=0, le=12)
    label: str = Field(..., min_length=1, max_length=120)


class SemesterDB(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    year_id: str
    number: int
    label: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SemesterPublic(BaseModel):
    id: str
    year_id: str
    number: int
    label: str
    created_at: datetime


# ============================================================================
# Subject
# ============================================================================
class SubjectCreate(BaseModel):
    semester_id: str
    branch_id: Optional[str] = None
    code: str = Field(..., min_length=1, max_length=32)
    name: str = Field(..., min_length=1, max_length=120)
    credits: Optional[int] = Field(None, gt=0)
    category: Optional[str] = Field(None, max_length=32)


class SubjectDB(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    semester_id: str
    branch_id: Optional[str] = None
    code: str
    name: str
    credits: Optional[int] = None
    category: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SubjectPublic(BaseModel):
    id: str
    semester_id: str
    branch_id: Optional[str]
    code: str
    name: str
    credits: Optional[int]
    category: Optional[str]
    created_at: datetime


# ============================================================================
# Batch (graduating cohort)
# ============================================================================
class BatchCreate(BaseModel):
    institution_id: str
    admission_year: int = Field(..., gt=1900, le=2100)
    graduating_year: int = Field(..., gt=1900, le=2100)
    name: str = Field(..., min_length=1, max_length=120)


class BatchDB(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    institution_id: str
    admission_year: int
    graduating_year: int
    name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BatchPublic(BaseModel):
    id: str
    institution_id: str
    admission_year: int
    graduating_year: int
    name: str
    created_at: datetime


# ============================================================================
# Division
# ============================================================================
class DivisionCreate(BaseModel):
    # Legacy placement (semester of the curriculum). Optional now.
    semester_id: Optional[str] = None
    # Cohort placement (department × graduating batch). Both required together.
    branch_id: Optional[str] = None
    batch_id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=120)
    capacity: Optional[int] = Field(None, gt=0)

    @model_validator(mode="after")
    def _require_placement(self):
        if self.semester_id is None and (self.branch_id is None or self.batch_id is None):
            raise ValueError("Division needs semester_id or (branch_id + batch_id)")
        return self


class DivisionDB(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    semester_id: Optional[str] = None
    branch_id: Optional[str] = None
    batch_id: Optional[str] = None
    name: str
    capacity: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DivisionPublic(BaseModel):
    id: str
    semester_id: Optional[str]
    branch_id: Optional[str]
    batch_id: Optional[str]
    name: str
    capacity: Optional[int]
    created_at: datetime


# ============================================================================
# BatchSemester (cohort progression — where a batch is in curriculum time)
# ============================================================================
class BatchSemesterCreate(BaseModel):
    batch_id: str
    semester_id: str
    academic_year: str = Field(..., min_length=4, max_length=9)  # e.g. "2026-27"
    starts_on: date
    ends_on: date


class BatchSemesterDB(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    batch_id: str
    semester_id: str
    academic_year: str
    starts_on: date
    ends_on: date
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BatchSemesterPublic(BaseModel):
    id: str
    batch_id: str
    semester_id: str
    academic_year: str
    starts_on: date
    ends_on: date
    created_at: datetime


# ============================================================================
# Class (teaching instance)
# ============================================================================
class ClassCreate(BaseModel):
    division_id: str
    subject_id: str
    batch_semester_id: Optional[str] = None
    name: Optional[str] = Field(None, max_length=120)  # Display name for admin UI


class ClassDB(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    division_id: str
    subject_id: str
    batch_semester_id: Optional[str] = None
    name: Optional[str] = None  # Display name for admin UI
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ClassPublic(BaseModel):
    id: str
    division_id: str
    subject_id: str
    batch_semester_id: Optional[str]
    name: Optional[str]  # Display name for admin UI
    created_at: datetime


# ============================================================================
# TeacherAssignment
# ============================================================================
class TeacherAssignmentCreate(BaseModel):
    class_id: str
    teacher_id: str
    active: bool = True


class TeacherAssignmentDB(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    class_id: str
    teacher_id: str
    active: bool = True
    assigned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TeacherAssignmentPublic(BaseModel):
    id: str
    class_id: str
    teacher_id: str
    active: bool
    assigned_at: datetime


# ============================================================================
# StudentEnrollment
# ============================================================================
class AuditLogCreate(BaseModel):
    admin_id: str
    action: str = Field(..., pattern=r"^(create|update|delete|publish|unpublish|generate|assign_teacher|unassign_teacher)$")
    entity_type: str
    entity_id: str
    details: Optional[str] = None


class AuditLogDB(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    admin_id: str
    action: str
    entity_type: str
    entity_id: str
    details: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditLogPublic(BaseModel):
    id: str
    admin_id: str
    action: str
    entity_type: str
    entity_id: str
    details: Optional[str]
    created_at: datetime


class StudentEnrollmentCreate(BaseModel):
    class_id: str
    student_id: str


class StudentEnrollmentDB(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    class_id: str
    student_id: str
    enrolled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StudentEnrollmentPublic(BaseModel):
    id: str
    class_id: str
    student_id: str
    enrolled_at: datetime


# ============================================================================
# QR Code Models
# ============================================================================
class QRCodeCreate(BaseModel):
    class_id: str


class QRCodeDB(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    class_id: str
    token_secret: str
    svg_key: str
    png_key: Optional[str] = None
    scan_count: int = 0
    enrollment_count: int = 0
    is_active: bool = True
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    generated_by: str


class QRCodePublic(BaseModel):
    id: str
    class_id: str
    svg_url: str
    png_url: Optional[str] = None
    scan_count: int
    enrollment_count: int
    is_active: bool
    generated_at: datetime


class QRAnalytics(BaseModel):
    qr_id: str
    class_id: str
    scan_count: int
    enrollment_count: int
    conversion_rate: float
    generated_at: datetime
    is_active: bool
    scan_count_per_day: Optional[int] = None
    enrollment_count_per_day: Optional[int] = None


# ============================================================================
# Enrollment Request (for student self-enrollment)
# ============================================================================
class EnrollRequest(BaseModel):
    class_id: str
    token: Optional[str] = None


# ============================================================================
# Teacher Dashboard Summary Models
# ============================================================================
class TeacherClassSummary(BaseModel):
    class_id: str
    subject_name: str
    division_name: str
    semester_label: str
    year_number: int
    institution_name: str
    assignment_active: bool
    assignment_id: str


class EnrolledStudent(BaseModel):
    student_id: str
    student_name: str
    student_email: str
    enrolled_at: datetime
    enrollment_id: str
