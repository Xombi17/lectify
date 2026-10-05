"""Tests asserting parity between SQLAlchemy ORM and Prisma models."""
import re
from pathlib import Path
from sqlalchemy.orm import class_mapper

import pytest

from models.orm import JobORM, JobChunkORM, TimetableSlotORM, LectureORM

# Known Prisma relation types to ignore when checking scalar column parity
PRISMA_RELATION_TYPES = {
    "User", "Lecture", "Class", "Division", "Subject", "Semester", "Year", "Institution", "TimetableSlot",
    "ChatMessage", "QuizAttempt", "Bookmark", "FlashcardReview", "TeacherAssignment", "StudentEnrollment"
}

@pytest.mark.parametrize("orm_model, prisma_model_name, unique_constraint", [
    (JobORM, "Job", "@@unique([lectureId, stage, version])"),
    (JobChunkORM, "JobChunk", "@@unique([lectureId, version, chunkIndex])"),
    (TimetableSlotORM, "TimetableSlot", ""),
    (LectureORM, "Lecture", "")
])
def test_schema_parity(orm_model, prisma_model_name, unique_constraint):
    # Read Prisma schema
    prisma_path = Path(__file__).parent.parent.parent / "prisma" / "schema.prisma"
    content = prisma_path.read_text()
    
    # Extract model (match up to closing brace at start of line to avoid premature stop on default("{}"))
    model_match = re.search(rf"model\s+{prisma_model_name}\s*\{{(.*?)\n\}}", content, re.DOTALL)
    assert model_match, f"{prisma_model_name} model not found in Prisma schema"
    model_text = model_match.group(1)
    
    # Extract mapped fields (fields with @map("..."))
    prisma_fields = set()
    for line in model_text.splitlines():
        line = line.strip()
        if not line or line.startswith("//") or line.startswith("@@"):
            continue
        
        tokens = line.split()
        if len(tokens) >= 2:
            field_type = tokens[1].rstrip("?").rstrip("[]")
            if "@relation" in line or tokens[1].endswith("[]") or field_type in PRISMA_RELATION_TYPES:
                continue
        
        # Check for @map
        map_match = re.search(r'@map\("([^"]+)"\)', line)
        if map_match:
            prisma_fields.add(map_match.group(1))
        else:
            # Field name is the first word
            field_name = line.split()[0]
            prisma_fields.add(field_name)
    
    # Get ORM fields
    orm_fields = set()
    mapper = class_mapper(orm_model)
    for column in mapper.columns:
        orm_fields.add(column.name)
        
    assert orm_fields == prisma_fields, f"Schema mismatch! ORM: {orm_fields}, Prisma: {prisma_fields}"
    
    # Check for unique constraint if specified
    if unique_constraint:
        assert unique_constraint.replace(" ", "") in model_text.replace(" ", ""), f"Missing unique constraint in Prisma {prisma_model_name}"
