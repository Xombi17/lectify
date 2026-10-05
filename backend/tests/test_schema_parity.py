"""Tests asserting parity between SQLAlchemy ORM and Prisma models."""
import re
from pathlib import Path
from sqlalchemy.orm import class_mapper

from models.orm import JobORM

def test_job_schema_parity():
    # Read Prisma schema
    prisma_path = Path(__file__).parent.parent.parent / "prisma" / "schema.prisma"
    content = prisma_path.read_text()
    
    # Extract Job model
    job_model_match = re.search(r"model Job \{(.*?)\}", content, re.DOTALL)
    assert job_model_match, "Job model not found in Prisma schema"
    job_model_text = job_model_match.group(1)
    
    # Extract mapped fields (fields with @map("..."))
    prisma_fields = set()
    for line in job_model_text.splitlines():
        line = line.strip()
        if not line or line.startswith("//") or line.startswith("@@"):
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
    mapper = class_mapper(JobORM)
    for column in mapper.columns:
        orm_fields.add(column.name)
        
    assert orm_fields == prisma_fields, f"Schema mismatch! ORM: {orm_fields}, Prisma: {prisma_fields}"
    
    # Check for unique constraint
    assert "@@unique([lectureId, stage, version])" in job_model_text or "@@unique([lectureId,stage,version])" in job_model_text.replace(" ", "")
