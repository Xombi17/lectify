"""Batch entity + cohort-placed division tests against in-memory SQLite."""
import asyncio
import sys
import uuid
from datetime import datetime, timezone

import pytest

sys.path.insert(0, "/app/backend")


@pytest.fixture(autouse=True)
def _sql_env(monkeypatch):
    """Force SQL backend with aiosqlite in-memory for this module."""
    monkeypatch.setenv("DATABASE_BACKEND", "postgres")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    import importlib

    from core import config as cfg

    cfg.get_settings.cache_clear()
    importlib.reload(cfg)
    import core.sql_db as sdb

    importlib.reload(sdb)
    import repositories._sql.academic_repository as ar

    importlib.reload(ar)
    yield
    cfg.get_settings.cache_clear()


def _arun(coro):
    return asyncio.run(coro)


def _now():
    return datetime.now(timezone.utc)


class TestBatchRepository:
    def test_create_and_list_by_institution(self):
        async def go():
            from core.sql_db import close_sql, init_models
            from models.academic import BatchDB, InstitutionDB
            from repositories._sql.academic_repository import BatchRepository, InstitutionRepository

            await init_models()
            inst = InstitutionDB(id=str(uuid.uuid4()), name="Uni", code="U1", created_at=_now())
            await InstitutionRepository().create(inst)

            repo = BatchRepository()
            b28 = BatchDB(id=str(uuid.uuid4()), institution_id=inst.id,
                          admission_year=2024, graduating_year=2028,
                          name="Batch of 2028", created_at=_now())
            b29 = BatchDB(id=str(uuid.uuid4()), institution_id=inst.id,
                          admission_year=2025, graduating_year=2029,
                          name="Batch of 2029", created_at=_now())
            await repo.create(b28)
            await repo.create(b29)

            rows = await repo.list_by_institution(inst.id)
            assert sorted(r.graduating_year for r in rows) == [2028, 2029]

            got = await repo.get_by_id(b28.id)
            assert got.name == "Batch of 2028"

            updated = await repo.update(b28.id, {"name": "Batch of 2028 (rev)"})
            assert updated.name == "Batch of 2028 (rev)"

            assert await repo.delete(b29.id) is True
            assert await repo.get_by_id(b29.id) is None
            await close_sql()

        _arun(go())


class TestCohortDivisions:
    def _seed(self):
        from models.academic import BatchDB, BranchDB, DivisionDB, InstitutionDB
        inst = InstitutionDB(id=str(uuid.uuid4()), name="Uni", code="U2", created_at=_now())
        branch = BranchDB(id=str(uuid.uuid4()), institution_id=inst.id,
                          code="CSE", name="Computer Science and Engineering", created_at=_now())
        batch = BatchDB(id=str(uuid.uuid4()), institution_id=inst.id,
                        admission_year=2025, graduating_year=2029,
                        name="Batch of 2029", created_at=_now())
        return inst, branch, batch

    def test_division_by_branch_and_batch(self):
        async def go():
            from core.sql_db import close_sql, init_models
            from models.academic import DivisionDB
            from repositories._sql.academic_repository import (
                BatchRepository, BranchRepository, DivisionRepository, InstitutionRepository,
            )

            await init_models()
            inst, branch, batch = self._seed()
            await InstitutionRepository().create(inst)
            await BranchRepository().create(branch)
            await BatchRepository().create(batch)

            repo = DivisionRepository()
            for name in ("CSE A", "CSE B"):
                await repo.create(DivisionDB(
                    id=str(uuid.uuid4()), semester_id=None,
                    branch_id=branch.id, batch_id=batch.id,
                    name=name, created_at=_now(),
                ))

            assert len(await repo.list_by_branch(branch.id)) == 2
            assert len(await repo.list_by_batch(batch.id)) == 2
            both = await repo.list_by_branch_batch(branch.id, batch.id)
            assert sorted(d.name for d in both) == ["CSE A", "CSE B"]
            await close_sql()

        _arun(go())

    def test_division_placement_validator(self):
        from models.academic import DivisionCreate

        # Legacy semester placement still valid
        ok = DivisionCreate(semester_id="sem-1", name="Div A")
        assert ok.semester_id == "sem-1"

        # Cohort placement valid
        ok = DivisionCreate(branch_id="br-1", batch_id="ba-1", name="CSE A")
        assert ok.branch_id == "br-1"

        # Neither placement rejected
        with pytest.raises(Exception):
            DivisionCreate(name="Nowhere")

        # Half cohort placement rejected
        with pytest.raises(Exception):
            DivisionCreate(branch_id="br-1", name="Half")


class TestBranchSubjects:
    def test_subject_branch_scoping_and_category(self):
        async def go():
            from core.sql_db import close_sql, init_models
            from models.academic import BranchDB, InstitutionDB, SemesterDB, SubjectDB, YearDB
            from repositories._sql.academic_repository import (
                BranchRepository, InstitutionRepository, SemesterRepository,
                SubjectRepository, YearRepository,
            )

            await init_models()
            inst = InstitutionDB(id=str(uuid.uuid4()), name="Uni", code="U3", created_at=_now())
            await InstitutionRepository().create(inst)
            branch = BranchDB(id=str(uuid.uuid4()), institution_id=inst.id,
                              code="CSE", name="CSE", created_at=_now())
            await BranchRepository().create(branch)
            year = YearDB(id=str(uuid.uuid4()), institution_id=inst.id,
                          number=1, name="First Year", created_at=_now())
            await YearRepository().create(year)
            sem_id = str(uuid.uuid4())
            await SemesterRepository().create(SemesterDB(
                id=sem_id, year_id=year.id, number=3, label="Semester 3", created_at=_now()))

            repo = SubjectRepository()
            await repo.create(SubjectDB(
                id=str(uuid.uuid4()), semester_id=sem_id, branch_id=branch.id,
                code="CSE-S3-01", name="Data Structures", category="mandatory",
                created_at=_now()))
            await repo.create(SubjectDB(
                id=str(uuid.uuid4()), semester_id=sem_id, branch_id=branch.id,
                code="CSE-S3-02", name="Open Elective", category="elective",
                created_at=_now()))

            assert len(await repo.list_by_branch(branch.id)) == 2
            scoped = await repo.list_by_semester_branch(sem_id, branch.id)
            assert sorted(s.name for s in scoped) == ["Data Structures", "Open Elective"]
            cats = {s.name: s.category for s in scoped}
            assert cats == {"Data Structures": "mandatory", "Open Elective": "elective"}
            await close_sql()

        _arun(go())


class TestBatchProgression:
    def test_current_semester_derived_from_dates(self):
        import datetime as dt

        async def go():
            from core.sql_db import close_sql, init_models
            from models.academic import BatchDB, BatchSemesterDB, InstitutionDB, SemesterDB, YearDB
            from repositories._sql.academic_repository import (
                BatchRepository, BatchSemesterRepository, InstitutionRepository,
                SemesterRepository, YearRepository,
            )

            await init_models()
            inst = InstitutionDB(id=str(uuid.uuid4()), name="Uni", code="U4", created_at=_now())
            await InstitutionRepository().create(inst)
            batch = BatchDB(id=str(uuid.uuid4()), institution_id=inst.id,
                            admission_year=2024, graduating_year=2028,
                            name="Batch of 2028", created_at=_now())
            await BatchRepository().create(batch)
            year = YearDB(id=str(uuid.uuid4()), institution_id=inst.id,
                          number=3, name="Third Year", created_at=_now())
            await YearRepository().create(year)
            sem_id = str(uuid.uuid4())
            await SemesterRepository().create(SemesterDB(
                id=sem_id, year_id=year.id, number=5, label="Semester 5", created_at=_now()))

            repo = BatchSemesterRepository()
            today = dt.date.today()
            row = BatchSemesterDB(
                id=str(uuid.uuid4()), batch_id=batch.id, semester_id=sem_id,
                academic_year="2026-27",
                starts_on=today - dt.timedelta(days=30),
                ends_on=today + dt.timedelta(days=60),
                created_at=_now(),
            )
            await repo.create(row)

            rows = await repo.list_by_batch(batch.id)
            current = [r for r in rows if r.starts_on <= today <= r.ends_on]
            assert len(current) == 1
            assert current[0].semester_id == sem_id
            assert current[0].academic_year == "2026-27"
            await close_sql()

        _arun(go())

    def test_class_teaching_instance_uniqueness(self):
        async def go():
            import sqlalchemy.exc
            from core.sql_db import close_sql, init_models
            from models.academic import (
                BatchDB, BatchSemesterDB, BranchDB, ClassDB, DivisionDB,
                InstitutionDB, SemesterDB, SubjectDB, YearDB,
            )
            from repositories._sql.academic_repository import (
                BatchRepository, BatchSemesterRepository, BranchRepository,
                ClassRepository, DivisionRepository, InstitutionRepository,
                SemesterRepository, SubjectRepository, YearRepository,
            )
            import datetime as dt

            await init_models()
            inst = InstitutionDB(id=str(uuid.uuid4()), name="Uni", code="U5", created_at=_now())
            await InstitutionRepository().create(inst)
            branch = BranchDB(id=str(uuid.uuid4()), institution_id=inst.id,
                              code="CSE", name="CSE", created_at=_now())
            await BranchRepository().create(branch)
            batch = BatchDB(id=str(uuid.uuid4()), institution_id=inst.id,
                            admission_year=2025, graduating_year=2029,
                            name="Batch of 2029", created_at=_now())
            await BatchRepository().create(batch)
            year = YearDB(id=str(uuid.uuid4()), institution_id=inst.id,
                          number=2, name="Second Year", created_at=_now())
            await YearRepository().create(year)
            sem_id = str(uuid.uuid4())
            await SemesterRepository().create(SemesterDB(
                id=sem_id, year_id=year.id, number=3, label="Semester 3", created_at=_now()))
            bs_id = str(uuid.uuid4())
            await BatchSemesterRepository().create(BatchSemesterDB(
                id=bs_id, batch_id=batch.id, semester_id=sem_id,
                academic_year="2026-27", starts_on=dt.date(2026, 7, 1),
                ends_on=dt.date(2026, 12, 31), created_at=_now()))
            div_id = str(uuid.uuid4())
            await DivisionRepository().create(DivisionDB(
                id=div_id, semester_id=None, branch_id=branch.id, batch_id=batch.id,
                name="CSE A", created_at=_now()))
            subj_id = str(uuid.uuid4())
            await SubjectRepository().create(SubjectDB(
                id=subj_id, semester_id=sem_id, branch_id=branch.id,
                code="CSE-S3-01", name="DBMS", category="mandatory", created_at=_now()))

            repo = ClassRepository()
            # Same division+subject in the same period: allowed once...
            await repo.create(ClassDB(
                id=str(uuid.uuid4()), division_id=div_id, subject_id=subj_id,
                batch_semester_id=bs_id, created_at=_now()))
            # ...but not twice.
            with pytest.raises(sqlalchemy.exc.IntegrityError):
                await repo.create(ClassDB(
                    id=str(uuid.uuid4()), division_id=div_id, subject_id=subj_id,
                    batch_semester_id=bs_id, created_at=_now()))
            await close_sql()

        _arun(go())
