"""reembed_lectures: re-embeds lectures with a summary, skips empty ones, tolerates failures."""
import uuid
from datetime import datetime, timezone

import pytest

from models.lecture import LectureDB, StudyMaterials


class FakeAI:
    def __init__(self, fail_on=None):
        self.seeds, self.fail_on = [], fail_on

    async def embed(self, text):
        self.seeds.append(text)
        if self.fail_on and self.fail_on in text:
            raise RuntimeError("provider down")
        return [0.5, 0.5]


@pytest.mark.asyncio
async def test_reembed_all(monkeypatch):
    monkeypatch.setenv("DATABASE_BACKEND", "postgres")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

    from core.sql_db import init_models
    from repositories._sql.lecture_repository import LectureRepository
    from scripts.reembed_lectures import reembed_all

    await init_models()
    repo = LectureRepository()
    now = datetime.now(timezone.utc)

    async def make(summary, concepts):
        lec = LectureDB(
            id=f"lec_{uuid.uuid4().hex[:8]}", teacher_id="t", title="x", audio_object_key="k",
            audio_filename="a.mp3", audio_mime="audio/mpeg", status="ready",
            materials=StudyMaterials(summary=summary, key_concepts=concepts),
            embedding=[9.0], created_at=now, updated_at=now,
        )
        await repo.create(lec)
        return lec.id

    ok = await make("paging basics", ["tlb"])
    empty = await make("", [])
    bad = await make("will fail", [])

    ai = FakeAI(fail_on="will fail")
    done, _, failed = await reembed_all(ai, dry_run=True)
    assert (done, failed) == (2, 0)  # skipped count includes unrelated shared-DB rows
    assert (await repo.get_by_id(ok)).embedding == [9.0]  # dry run writes nothing

    done, _, failed = await reembed_all(ai)
    assert (done, failed) == (1, 1)
    assert (await repo.get_by_id(ok)).embedding == [0.5, 0.5]
    assert (await repo.get_by_id(empty)).embedding == [9.0]
    assert (await repo.get_by_id(bad)).embedding == [9.0]
    assert "paging basics tlb" in ai.seeds
