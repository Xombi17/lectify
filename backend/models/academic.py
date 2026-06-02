"""Pydantic models for academic hierarchy entities."""
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


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
    code: str = Field(..., min_length=1, max_length=32)
    name: str = Field(..., min_length=1, max_length=120)
    credits: Optional[int] = Field(None, gt=0)


class SubjectDB(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    semester_id: str
    code: str
    name: str
    credits: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SubjectPublic(BaseModel):
    id: str
    semester_id: str
    code: str
    name: str
    credits: Optional[int]
    created_at: datetime


# ============================================================================
# Division
# ============================================================================
class DivisionCreate(BaseModel):
    semester_id: str
    name: str = Field(..., min_length=1, max_length=120)
    capacity: Optional[int] = Field(None, gt=0)


class DivisionDB(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    semester_id: str
    name: str
    capacity: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DivisionPublic(BaseModel):
    id: str
    semester_id: str
    name: str
    capacity: Optional[int]
    created_at: datetime


# ============================================================================
# Class
# ============================================================================
class ClassCreate(BaseModel):
    division_id: str
    subject_id: str


class ClassDB(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    division_id: str
    subject_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ClassPublic(BaseModel):
    id: str
    division_id: str
    subject_id: str
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
