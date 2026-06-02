"""Lecture repository — Mongo implementation behind the Repository contract."""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from core.db import get_db
from models.lecture import LectureDB, LectureSummary, StudyMaterials


def _to_lecture(doc: dict) -> LectureDB:
    doc.pop("_id", None)
    for field in ("created_at", "updated_at"):
        if isinstance(doc.get(field), str):
            doc[field] = datetime.fromisoformat(doc[field])
    if doc.get("materials") is None:
        doc["materials"] = StudyMaterials().model_dump()
    return LectureDB(**doc)


class LectureRepository:
    COLLECTION = "lectures"

    def __init__(self):
        self.db = get_db()
        self.col = self.db[self.COLLECTION]

    async def ensure_indexes(self) -> None:
        await self.col.create_index("teacher_id")
        await self.col.create_index("published")

    async def create(self, lecture: LectureDB) -> LectureDB:
        doc = lecture.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        doc["updated_at"] = doc["updated_at"].isoformat()
        await self.col.insert_one(doc)
        return lecture

    async def get_by_id(self, lecture_id: str) -> Optional[LectureDB]:
        doc = await self.col.find_one({"id": lecture_id}, {"_id": 0})
        return _to_lecture(doc) if doc else None

    async def list_by_teacher(self, teacher_id: str) -> List[LectureSummary]:
        cursor = self.col.find(
            {"teacher_id": teacher_id},
            {"_id": 0, "transcript": 0, "materials": 0},
        ).sort("created_at", -1)
        items = []
        async for doc in cursor:
            for f in ("created_at", "updated_at"):
                if isinstance(doc.get(f), str):
                    doc[f] = datetime.fromisoformat(doc[f])
            items.append(LectureSummary(**{k: doc.get(k) for k in LectureSummary.model_fields}))
        return items

    async def list_published(self) -> List[LectureSummary]:
        cursor = self.col.find(
            {"published": True},
            {"_id": 0, "transcript": 0, "materials": 0, "embedding": 0, "translations": 0},
        ).sort("created_at", -1)
        items = []
        async for doc in cursor:
            for f in ("created_at", "updated_at"):
                if isinstance(doc.get(f), str):
                    doc[f] = datetime.fromisoformat(doc[f])
            items.append(LectureSummary(**{k: doc.get(k) for k in LectureSummary.model_fields}))
        return items

    async def list_published_embeddings(self) -> list[dict]:
        """Return minimal docs needed for semantic ranking."""
        cursor = self.col.find(
            {"published": True},
            {"_id": 0, "id": 1, "title": 1, "subject": 1, "semester": 1,
             "embedding": 1, "materials.summary": 1, "materials.key_concepts": 1},
        )
        return [doc async for doc in cursor]

    async def update_fields(self, lecture_id: str, fields: dict) -> None:
        fields["updated_at"] = datetime.now(timezone.utc).isoformat()
        # Serialize StudyMaterials if present
        if "materials" in fields and hasattr(fields["materials"], "model_dump"):
            fields["materials"] = fields["materials"].model_dump()
        await self.col.update_one({"id": lecture_id}, {"$set": fields})

    async def delete(self, lecture_id: str) -> None:
        await self.col.delete_one({"id": lecture_id})

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())
