"""Academic hierarchy repository tests against in-memory SQLite."""
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
    # Reload _sql academic_repository module
    import repositories._sql.academic_repository as ar
    importlib.reload(ar)
    yield
    cfg.get_settings.cache_clear()


def _arun(coro):
    return asyncio.run(coro)


# ===========================================================================
# Institution Repository Tests
# ===========================================================================
class TestSqlInstitutionRepository:
    def test_create_and_get_by_id(self):
        async def go():
            from core.sql_db import init_models, close_sql
            from repositories._sql.academic_repository import InstitutionRepository
            from models.academic import InstitutionDB

            await init_models()
            repo = InstitutionRepository()
            inst = InstitutionDB(
                id=str(uuid.uuid4()),
                name="Test University",
                code="TU001",
                address="123 Main St",
                created_at=datetime.now(timezone.utc),
            )
            await repo.create(inst)

            got = await repo.get_by_id(inst.id)
            assert got is not None
            assert got.name == "Test University"
            assert got.code == "TU001"
            assert got.address == "123 Main St"
            await close_sql()
        _arun(go())

    def test_get_by_code(self):
        async def go():
            from core.sql_db import init_models, close_sql
            from repositories._sql.academic_repository import InstitutionRepository
            from models.academic import InstitutionDB

            await init_models()
            repo = InstitutionRepository()
            inst = InstitutionDB(
                id=str(uuid.uuid4()),
                name="Code Test Uni",
                code="CTU",
                created_at=datetime.now(timezone.utc),
            )
            await repo.create(inst)

            got = await repo.get_by_code("CTU")
            assert got is not None
            assert got.name == "Code Test Uni"
            await close_sql()
        _arun(go())


# ===========================================================================
# Year Repository Tests
# ===========================================================================
class TestSqlYearRepository:
    def test_create_and_get_by_id(self):
        async def go():
            from core.sql_db import init_models, close_sql
            from repositories._sql.academic_repository import InstitutionRepository, YearRepository
            from models.academic import InstitutionDB, YearDB

            await init_models()
            inst_repo = InstitutionRepository()
            inst = InstitutionDB(
                id=str(uuid.uuid4()),
                name="Inst1",
                code="I1",
                created_at=datetime.now(timezone.utc),
            )
            await inst_repo.create(inst)

            year_repo = YearRepository()
            year = YearDB(
                id=str(uuid.uuid4()),
                institution_id=inst.id,
                number=1,
                name="First Year",
                created_at=datetime.now(timezone.utc),
            )
            await year_repo.create(year)

            got = await year_repo.get_by_id(year.id)
            assert got is not None
            assert got.number == 1
            assert got.name == "First Year"
            assert got.institution_id == inst.id
            await close_sql()
        _arun(go())

    def test_list_by_institution(self):
        async def go():
            from core.sql_db import init_models, close_sql
            from repositories._sql.academic_repository import InstitutionRepository, YearRepository
            from models.academic import InstitutionDB, YearDB

            await init_models()
            inst_repo = InstitutionRepository()
            inst = InstitutionDB(id=str(uuid.uuid4()), name="I", code="I", created_at=datetime.now(timezone.utc))
            await inst_repo.create(inst)

            year_repo = YearRepository()
            y1 = YearDB(id=str(uuid.uuid4()), institution_id=inst.id, number=1, name="Y1", created_at=datetime.now(timezone.utc))
            y2 = YearDB(id=str(uuid.uuid4()), institution_id=inst.id, number=2, name="Y2", created_at=datetime.now(timezone.utc))
            await year_repo.create(y1)
            await year_repo.create(y2)

            years = await year_repo.list_by_institution(inst.id)
            assert len(years) == 2
            assert {y.number for y in years} == {1, 2}
            await close_sql()
        _arun(go())


# ===========================================================================
# Branch Repository Tests
# ===========================================================================
class TestSqlBranchRepository:
    def test_create_and_get_by_id(self):
        async def go():
            from core.sql_db import init_models, close_sql
            from repositories._sql.academic_repository import InstitutionRepository, BranchRepository
            from models.academic import InstitutionDB, BranchDB

            await init_models()
            inst_repo = InstitutionRepository()
            inst = InstitutionDB(id=str(uuid.uuid4()), name="I", code="I", created_at=datetime.now(timezone.utc))
            await inst_repo.create(inst)

            branch_repo = BranchRepository()
            branch = BranchDB(
                id=str(uuid.uuid4()),
                institution_id=inst.id,
                code="CS",
                name="Computer Science",
                created_at=datetime.now(timezone.utc),
            )
            await branch_repo.create(branch)

            got = await branch_repo.get_by_id(branch.id)
            assert got is not None
            assert got.code == "CS"
            assert got.name == "Computer Science"
            await close_sql()
        _arun(go())

    def test_list_by_institution(self):
        async def go():
            from core.sql_db import init_models, close_sql
            from repositories._sql.academic_repository import InstitutionRepository, BranchRepository
            from models.academic import InstitutionDB, BranchDB

            await init_models()
            inst_repo = InstitutionRepository()
            inst = InstitutionDB(id=str(uuid.uuid4()), name="I", code="I", created_at=datetime.now(timezone.utc))
            await inst_repo.create(inst)

            branch_repo = BranchRepository()
            b1 = BranchDB(id=str(uuid.uuid4()), institution_id=inst.id, code="CS", name="CS", created_at=datetime.now(timezone.utc))
            b2 = BranchDB(id=str(uuid.uuid4()), institution_id=inst.id, code="EE", name="EE", created_at=datetime.now(timezone.utc))
            await branch_repo.create(b1)
            await branch_repo.create(b2)

            branches = await branch_repo.list_by_institution(inst.id)
            assert len(branches) == 2
            assert {b.code for b in branches} == {"CS", "EE"}
            await close_sql()
        _arun(go())


# ===========================================================================
# Semester Repository Tests
# ===========================================================================
class TestSqlSemesterRepository:
    def test_create_and_get_by_id(self):
        async def go():
            from core.sql_db import init_models, close_sql
            from repositories._sql.academic_repository import InstitutionRepository, YearRepository, SemesterRepository
            from models.academic import InstitutionDB, YearDB, SemesterDB

            await init_models()
            inst_repo = InstitutionRepository()
            inst = InstitutionDB(id=str(uuid.uuid4()), name="I", code="I", created_at=datetime.now(timezone.utc))
            await inst_repo.create(inst)

            year_repo = YearRepository()
            year = YearDB(id=str(uuid.uuid4()), institution_id=inst.id, number=1, name="Y1", created_at=datetime.now(timezone.utc))
            await year_repo.create(year)

            sem_repo = SemesterRepository()
            sem = SemesterDB(
                id=str(uuid.uuid4()),
                year_id=year.id,
                number=1,
                label="Fall 2025",
                created_at=datetime.now(timezone.utc),
            )
            await sem_repo.create(sem)

            got = await sem_repo.get_by_id(sem.id)
            assert got is not None
            assert got.number == 1
            assert got.label == "Fall 2025"
            await close_sql()
        _arun(go())

    def test_list_by_year(self):
        async def go():
            from core.sql_db import init_models, close_sql
            from repositories._sql.academic_repository import InstitutionRepository, YearRepository, SemesterRepository
            from models.academic import InstitutionDB, YearDB, SemesterDB

            await init_models()
            inst_repo = InstitutionRepository()
            inst = InstitutionDB(id=str(uuid.uuid4()), name="I", code="I", created_at=datetime.now(timezone.utc))
            await inst_repo.create(inst)

            year_repo = YearRepository()
            year = YearDB(id=str(uuid.uuid4()), institution_id=inst.id, number=1, name="Y1", created_at=datetime.now(timezone.utc))
            await year_repo.create(year)

            sem_repo = SemesterRepository()
            s1 = SemesterDB(id=str(uuid.uuid4()), year_id=year.id, number=1, label="S1", created_at=datetime.now(timezone.utc))
            s2 = SemesterDB(id=str(uuid.uuid4()), year_id=year.id, number=2, label="S2", created_at=datetime.now(timezone.utc))
            await sem_repo.create(s1)
            await sem_repo.create(s2)

            sems = await sem_repo.list_by_year(year.id)
            assert len(sems) == 2
            assert {s.number for s in sems} == {1, 2}
            await close_sql()
        _arun(go())


# ===========================================================================
# Subject Repository Tests
# ===========================================================================
class TestSqlSubjectRepository:
    def test_create_and_get_by_id(self):
        async def go():
            from core.sql_db import init_models, close_sql
            from repositories._sql.academic_repository import (
                InstitutionRepository, YearRepository, SemesterRepository, SubjectRepository
            )
            from models.academic import InstitutionDB, YearDB, SemesterDB, SubjectDB

            await init_models()
            inst = InstitutionDB(id=str(uuid.uuid4()), name="I", code="I", created_at=datetime.now(timezone.utc))
            await InstitutionRepository().create(inst)
            year = YearDB(id=str(uuid.uuid4()), institution_id=inst.id, number=1, name="Y1", created_at=datetime.now(timezone.utc))
            await YearRepository().create(year)
            sem = SemesterDB(id=str(uuid.uuid4()), year_id=year.id, number=1, label="S1", created_at=datetime.now(timezone.utc))
            await SemesterRepository().create(sem)

            subj_repo = SubjectRepository()
            subj = SubjectDB(
                id=str(uuid.uuid4()),
                semester_id=sem.id,
                code="CS301",
                name="Data Structures",
                credits=3,
                created_at=datetime.now(timezone.utc),
            )
            await subj_repo.create(subj)

            got = await subj_repo.get_by_id(subj.id)
            assert got is not None
            assert got.code == "CS301"
            assert got.name == "Data Structures"
            assert got.credits == 3
            await close_sql()
        _arun(go())

    def test_list_by_semester(self):
        async def go():
            from core.sql_db import init_models, close_sql
            from repositories._sql.academic_repository import (
                InstitutionRepository, YearRepository, SemesterRepository, SubjectRepository
            )
            from models.academic import InstitutionDB, YearDB, SemesterDB, SubjectDB

            await init_models()
            inst = InstitutionDB(id=str(uuid.uuid4()), name="I", code="I", created_at=datetime.now(timezone.utc))
            await InstitutionRepository().create(inst)
            year = YearDB(id=str(uuid.uuid4()), institution_id=inst.id, number=1, name="Y1", created_at=datetime.now(timezone.utc))
            await YearRepository().create(year)
            sem = SemesterDB(id=str(uuid.uuid4()), year_id=year.id, number=1, label="S1", created_at=datetime.now(timezone.utc))
            await SemesterRepository().create(sem)

            subj_repo = SubjectRepository()
            s1 = SubjectDB(id=str(uuid.uuid4()), semester_id=sem.id, code="CS301", name="DS", credits=3, created_at=datetime.now(timezone.utc))
            s2 = SubjectDB(id=str(uuid.uuid4()), semester_id=sem.id, code="CS302", name="Algo", credits=4, created_at=datetime.now(timezone.utc))
            await subj_repo.create(s1)
            await subj_repo.create(s2)

            subjs = await subj_repo.list_by_semester(sem.id)
            assert len(subjs) == 2
            assert {s.code for s in subjs} == {"CS301", "CS302"}
            await close_sql()
        _arun(go())


# ===========================================================================
# Division Repository Tests
# ===========================================================================
class TestSqlDivisionRepository:
    def test_create_and_get_by_id(self):
        async def go():
            from core.sql_db import init_models, close_sql
            from repositories._sql.academic_repository import (
                InstitutionRepository, YearRepository, SemesterRepository, DivisionRepository
            )
            from models.academic import InstitutionDB, YearDB, SemesterDB, DivisionDB

            await init_models()
            inst = InstitutionDB(id=str(uuid.uuid4()), name="I", code="I", created_at=datetime.now(timezone.utc))
            await InstitutionRepository().create(inst)
            year = YearDB(id=str(uuid.uuid4()), institution_id=inst.id, number=1, name="Y1", created_at=datetime.now(timezone.utc))
            await YearRepository().create(year)
            sem = SemesterDB(id=str(uuid.uuid4()), year_id=year.id, number=1, label="S1", created_at=datetime.now(timezone.utc))
            await SemesterRepository().create(sem)

            div_repo = DivisionRepository()
            div = DivisionDB(
                id=str(uuid.uuid4()),
                semester_id=sem.id,
                name="Division A",
                capacity=60,
                created_at=datetime.now(timezone.utc),
            )
            await div_repo.create(div)

            got = await div_repo.get_by_id(div.id)
            assert got is not None
            assert got.name == "Division A"
            assert got.capacity == 60
            await close_sql()
        _arun(go())

    def test_list_by_semester(self):
        async def go():
            from core.sql_db import init_models, close_sql
            from repositories._sql.academic_repository import (
                InstitutionRepository, YearRepository, SemesterRepository, DivisionRepository
            )
            from models.academic import InstitutionDB, YearDB, SemesterDB, DivisionDB

            await init_models()
            inst = InstitutionDB(id=str(uuid.uuid4()), name="I", code="I", created_at=datetime.now(timezone.utc))
            await InstitutionRepository().create(inst)
            year = YearDB(id=str(uuid.uuid4()), institution_id=inst.id, number=1, name="Y1", created_at=datetime.now(timezone.utc))
            await YearRepository().create(year)
            sem = SemesterDB(id=str(uuid.uuid4()), year_id=year.id, number=1, label="S1", created_at=datetime.now(timezone.utc))
            await SemesterRepository().create(sem)

            div_repo = DivisionRepository()
            d1 = DivisionDB(id=str(uuid.uuid4()), semester_id=sem.id, name="A", capacity=60, created_at=datetime.now(timezone.utc))
            d2 = DivisionDB(id=str(uuid.uuid4()), semester_id=sem.id, name="B", capacity=60, created_at=datetime.now(timezone.utc))
            await div_repo.create(d1)
            await div_repo.create(d2)

            divs = await div_repo.list_by_semester(sem.id)
            assert len(divs) == 2
            assert {d.name for d in divs} == {"A", "B"}
            await close_sql()
        _arun(go())


# ===========================================================================
# Class Repository Tests
# ===========================================================================
class TestSqlClassRepository:
    def test_create_and_get_by_id(self):
        async def go():
            from core.sql_db import init_models, close_sql
            from repositories._sql.academic_repository import (
                InstitutionRepository, YearRepository, SemesterRepository,
                SubjectRepository, DivisionRepository, ClassRepository
            )
            from models.academic import InstitutionDB, YearDB, SemesterDB, SubjectDB, DivisionDB, ClassDB

            await init_models()
            inst = InstitutionDB(id=str(uuid.uuid4()), name="I", code="I", created_at=datetime.now(timezone.utc))
            await InstitutionRepository().create(inst)
            year = YearDB(id=str(uuid.uuid4()), institution_id=inst.id, number=1, name="Y1", created_at=datetime.now(timezone.utc))
            await YearRepository().create(year)
            sem = SemesterDB(id=str(uuid.uuid4()), year_id=year.id, number=1, label="S1", created_at=datetime.now(timezone.utc))
            await SemesterRepository().create(sem)
            subj = SubjectDB(id=str(uuid.uuid4()), semester_id=sem.id, code="CS301", name="DS", created_at=datetime.now(timezone.utc))
            await SubjectRepository().create(subj)
            div = DivisionDB(id=str(uuid.uuid4()), semester_id=sem.id, name="A", created_at=datetime.now(timezone.utc))
            await DivisionRepository().create(div)

            cls_repo = ClassRepository()
            cls = ClassDB(
                id=str(uuid.uuid4()),
                division_id=div.id,
                subject_id=subj.id,
                created_at=datetime.now(timezone.utc),
            )
            await cls_repo.create(cls)

            got = await cls_repo.get_by_id(cls.id)
            assert got is not None
            assert got.division_id == div.id
            assert got.subject_id == subj.id
            await close_sql()
        _arun(go())

    def test_list_by_division(self):
        async def go():
            from core.sql_db import init_models, close_sql
            from repositories._sql.academic_repository import (
                InstitutionRepository, YearRepository, SemesterRepository,
                SubjectRepository, DivisionRepository, ClassRepository
            )
            from models.academic import InstitutionDB, YearDB, SemesterDB, SubjectDB, DivisionDB, ClassDB

            await init_models()
            inst = InstitutionDB(id=str(uuid.uuid4()), name="I", code="I", created_at=datetime.now(timezone.utc))
            await InstitutionRepository().create(inst)
            year = YearDB(id=str(uuid.uuid4()), institution_id=inst.id, number=1, name="Y1", created_at=datetime.now(timezone.utc))
            await YearRepository().create(year)
            sem = SemesterDB(id=str(uuid.uuid4()), year_id=year.id, number=1, label="S1", created_at=datetime.now(timezone.utc))
            await SemesterRepository().create(sem)
            s1 = SubjectDB(id=str(uuid.uuid4()), semester_id=sem.id, code="CS301", name="DS", created_at=datetime.now(timezone.utc))
            s2 = SubjectDB(id=str(uuid.uuid4()), semester_id=sem.id, code="CS302", name="Algo", created_at=datetime.now(timezone.utc))
            await SubjectRepository().create(s1)
            await SubjectRepository().create(s2)
            div = DivisionDB(id=str(uuid.uuid4()), semester_id=sem.id, name="A", created_at=datetime.now(timezone.utc))
            await DivisionRepository().create(div)

            cls_repo = ClassRepository()
            c1 = ClassDB(id=str(uuid.uuid4()), division_id=div.id, subject_id=s1.id, created_at=datetime.now(timezone.utc))
            c2 = ClassDB(id=str(uuid.uuid4()), division_id=div.id, subject_id=s2.id, created_at=datetime.now(timezone.utc))
            await cls_repo.create(c1)
            await cls_repo.create(c2)

            classes = await cls_repo.list_by_division(div.id)
            assert len(classes) == 2
            assert {c.subject_id for c in classes} == {s1.id, s2.id}
            await close_sql()
        _arun(go())


# ===========================================================================
# TeacherAssignment Repository Tests
# ===========================================================================
class TestSqlTeacherAssignmentRepository:
    def test_create_and_get_by_id(self):
        async def go():
            from core.sql_db import init_models, close_sql
            from repositories._sql.academic_repository import (
                InstitutionRepository, YearRepository, SemesterRepository,
                SubjectRepository, DivisionRepository, ClassRepository,
                TeacherAssignmentRepository,
            )
            from models.academic import (
                InstitutionDB, YearDB, SemesterDB, SubjectDB, DivisionDB,
                ClassDB, TeacherAssignmentDB,
            )

            await init_models()
            inst = InstitutionDB(id=str(uuid.uuid4()), name="I", code="I", created_at=datetime.now(timezone.utc))
            await InstitutionRepository().create(inst)
            year = YearDB(id=str(uuid.uuid4()), institution_id=inst.id, number=1, name="Y1", created_at=datetime.now(timezone.utc))
            await YearRepository().create(year)
            sem = SemesterDB(id=str(uuid.uuid4()), year_id=year.id, number=1, label="S1", created_at=datetime.now(timezone.utc))
            await SemesterRepository().create(sem)
            subj = SubjectDB(id=str(uuid.uuid4()), semester_id=sem.id, code="CS301", name="DS", created_at=datetime.now(timezone.utc))
            await SubjectRepository().create(subj)
            div = DivisionDB(id=str(uuid.uuid4()), semester_id=sem.id, name="A", created_at=datetime.now(timezone.utc))
            await DivisionRepository().create(div)
            cls = ClassDB(id=str(uuid.uuid4()), division_id=div.id, subject_id=subj.id, created_at=datetime.now(timezone.utc))
            await ClassRepository().create(cls)

            ta_repo = TeacherAssignmentRepository()
            ta = TeacherAssignmentDB(
                id=str(uuid.uuid4()),
                class_id=cls.id,
                teacher_id="teacher-uuid-1",
                active=True,
                assigned_at=datetime.now(timezone.utc),
            )
            await ta_repo.create(ta)

            got = await ta_repo.get_by_id(ta.id)
            assert got is not None
            assert got.class_id == cls.id
            assert got.teacher_id == "teacher-uuid-1"
            assert got.active is True
            await close_sql()
        _arun(go())

    def test_list_for_class_and_for_teacher(self):
        async def go():
            from core.sql_db import init_models, close_sql
            from repositories._sql.academic_repository import (
                InstitutionRepository, YearRepository, SemesterRepository,
                SubjectRepository, DivisionRepository, ClassRepository,
                TeacherAssignmentRepository,
            )
            from models.academic import (
                InstitutionDB, YearDB, SemesterDB, SubjectDB, DivisionDB,
                ClassDB, TeacherAssignmentDB,
            )

            await init_models()
            inst = InstitutionDB(id=str(uuid.uuid4()), name="I", code="I2", created_at=datetime.now(timezone.utc))
            await InstitutionRepository().create(inst)
            year = YearDB(id=str(uuid.uuid4()), institution_id=inst.id, number=1, name="Y1", created_at=datetime.now(timezone.utc))
            await YearRepository().create(year)
            sem = SemesterDB(id=str(uuid.uuid4()), year_id=year.id, number=1, label="S1", created_at=datetime.now(timezone.utc))
            await SemesterRepository().create(sem)
            s1 = SubjectDB(id=str(uuid.uuid4()), semester_id=sem.id, code="S1", name="DS", created_at=datetime.now(timezone.utc))
            s2 = SubjectDB(id=str(uuid.uuid4()), semester_id=sem.id, code="S2", name="Algo", created_at=datetime.now(timezone.utc))
            await SubjectRepository().create(s1)
            await SubjectRepository().create(s2)
            div = DivisionDB(id=str(uuid.uuid4()), semester_id=sem.id, name="A", created_at=datetime.now(timezone.utc))
            await DivisionRepository().create(div)
            c1 = ClassDB(id=str(uuid.uuid4()), division_id=div.id, subject_id=s1.id, created_at=datetime.now(timezone.utc))
            c2 = ClassDB(id=str(uuid.uuid4()), division_id=div.id, subject_id=s2.id, created_at=datetime.now(timezone.utc))
            await ClassRepository().create(c1)
            await ClassRepository().create(c2)

            ta_repo = TeacherAssignmentRepository()
            now = datetime.now(timezone.utc)
            # Two teachers on c1, one teacher on c2; one inactive row to verify filter
            await ta_repo.create(TeacherAssignmentDB(id=str(uuid.uuid4()), class_id=c1.id, teacher_id="T1", active=True, assigned_at=now))
            await ta_repo.create(TeacherAssignmentDB(id=str(uuid.uuid4()), class_id=c1.id, teacher_id="T2", active=True, assigned_at=now))
            await ta_repo.create(TeacherAssignmentDB(id=str(uuid.uuid4()), class_id=c1.id, teacher_id="T3", active=False, assigned_at=now))
            await ta_repo.create(TeacherAssignmentDB(id=str(uuid.uuid4()), class_id=c2.id, teacher_id="T1", active=True, assigned_at=now))

            c1_list = await ta_repo.list_for_class(c1.id)
            assert len(c1_list) == 2  # active only
            assert {t.teacher_id for t in c1_list} == {"T1", "T2"}

            c2_list = await ta_repo.list_for_class(c2.id)
            assert len(c2_list) == 1
            assert c2_list[0].teacher_id == "T1"

            t1_list = await ta_repo.list_for_teacher("T1")
            assert len(t1_list) == 2
            assert {t.class_id for t in t1_list} == {c1.id, c2.id}

            t3_list = await ta_repo.list_for_teacher("T3")
            assert t3_list == []  # inactive excluded
            await close_sql()
        _arun(go())


# ===========================================================================
# StudentEnrollment Repository Tests
# ===========================================================================
class TestSqlStudentEnrollmentRepository:
    def test_create_and_list_for_class_and_student(self):
        async def go():
            from core.sql_db import init_models, close_sql
            from repositories._sql.academic_repository import (
                InstitutionRepository, YearRepository, SemesterRepository,
                SubjectRepository, DivisionRepository, ClassRepository,
                StudentEnrollmentRepository,
            )
            from models.academic import (
                InstitutionDB, YearDB, SemesterDB, SubjectDB, DivisionDB,
                ClassDB, StudentEnrollmentDB,
            )

            await init_models()
            inst = InstitutionDB(id=str(uuid.uuid4()), name="I", code="I3", created_at=datetime.now(timezone.utc))
            await InstitutionRepository().create(inst)
            year = YearDB(id=str(uuid.uuid4()), institution_id=inst.id, number=1, name="Y1", created_at=datetime.now(timezone.utc))
            await YearRepository().create(year)
            sem = SemesterDB(id=str(uuid.uuid4()), year_id=year.id, number=1, label="S1", created_at=datetime.now(timezone.utc))
            await SemesterRepository().create(sem)
            subj = SubjectDB(id=str(uuid.uuid4()), semester_id=sem.id, code="S1", name="DS", created_at=datetime.now(timezone.utc))
            await SubjectRepository().create(subj)
            div = DivisionDB(id=str(uuid.uuid4()), semester_id=sem.id, name="A", created_at=datetime.now(timezone.utc))
            await DivisionRepository().create(div)
            cls = ClassDB(id=str(uuid.uuid4()), division_id=div.id, subject_id=subj.id, created_at=datetime.now(timezone.utc))
            await ClassRepository().create(cls)

            se_repo = StudentEnrollmentRepository()
            e1 = StudentEnrollmentDB(id=str(uuid.uuid4()), class_id=cls.id, student_id="S-A", enrolled_at=datetime.now(timezone.utc))
            e2 = StudentEnrollmentDB(id=str(uuid.uuid4()), class_id=cls.id, student_id="S-B", enrolled_at=datetime.now(timezone.utc))
            await se_repo.create(e1)
            await se_repo.create(e2)

            got = await se_repo.get_by_id(e1.id)
            assert got is not None
            assert got.class_id == cls.id
            assert got.student_id == "S-A"

            class_list = await se_repo.list_for_class(cls.id)
            assert len(class_list) == 2
            assert {e.student_id for e in class_list} == {"S-A", "S-B"}

            student_list = await se_repo.list_for_student("S-A")
            assert len(student_list) == 1
            assert student_list[0].class_id == cls.id
            await close_sql()
        _arun(go())

    def test_find_existing_for_idempotency(self):
        async def go():
            from core.sql_db import init_models, close_sql
            from repositories._sql.academic_repository import (
                InstitutionRepository, YearRepository, SemesterRepository,
                SubjectRepository, DivisionRepository, ClassRepository,
                StudentEnrollmentRepository,
            )
            from models.academic import (
                InstitutionDB, YearDB, SemesterDB, SubjectDB, DivisionDB,
                ClassDB, StudentEnrollmentDB,
            )

            await init_models()
            inst = InstitutionDB(id=str(uuid.uuid4()), name="I", code="I4", created_at=datetime.now(timezone.utc))
            await InstitutionRepository().create(inst)
            year = YearDB(id=str(uuid.uuid4()), institution_id=inst.id, number=1, name="Y1", created_at=datetime.now(timezone.utc))
            await YearRepository().create(year)
            sem = SemesterDB(id=str(uuid.uuid4()), year_id=year.id, number=1, label="S1", created_at=datetime.now(timezone.utc))
            await SemesterRepository().create(sem)
            subj = SubjectDB(id=str(uuid.uuid4()), semester_id=sem.id, code="S1", name="DS", created_at=datetime.now(timezone.utc))
            await SubjectRepository().create(subj)
            div = DivisionDB(id=str(uuid.uuid4()), semester_id=sem.id, name="A", created_at=datetime.now(timezone.utc))
            await DivisionRepository().create(div)
            cls = ClassDB(id=str(uuid.uuid4()), division_id=div.id, subject_id=subj.id, created_at=datetime.now(timezone.utc))
            await ClassRepository().create(cls)

            se_repo = StudentEnrollmentRepository()

            # Before any enrollment, find_existing returns None
            assert await se_repo.find_existing(cls.id, "S-X") is None

            # Create first enrollment
            e = StudentEnrollmentDB(id=str(uuid.uuid4()), class_id=cls.id, student_id="S-X", enrolled_at=datetime.now(timezone.utc))
            await se_repo.create(e)

            # find_existing now returns the enrollment
            found = await se_repo.find_existing(cls.id, "S-X")
            assert found is not None
            assert found.class_id == cls.id
            assert found.student_id == "S-X"

            # Attempting to create a duplicate enrollment should raise IntegrityError
            # (unique constraint on class_id + student_id)
            e2 = StudentEnrollmentDB(id=str(uuid.uuid4()), class_id=cls.id, student_id="S-X", enrolled_at=datetime.now(timezone.utc))
            try:
                await se_repo.create(e2)
                assert False, "Expected IntegrityError for duplicate enrollment"
            except Exception as ex:
                assert "UNIQUE constraint failed" in str(ex) or "IntegrityError" in type(ex).__name__

            await close_sql()
        _arun(go())


# ===========================================================================
# Dispatcher Tests (verify SQL branch selected when DATABASE_BACKEND != mongo)
# ===========================================================================
class TestDispatcher:
    def test_dispatcher_returns_sql_for_all_nine_entities(self):
        # Settings is already monkeypatched to DATABASE_BACKEND=postgres by
        # the _sql_env autouse fixture, and the SQL branch is imported lazily
        # at module load time. Re-import fresh to pick up the patched env.
        from repositories import (
            institution_repository, year_repository, branch_repository,
            semester_repository, subject_repository, division_repository,
            class_repository, teacher_assignment_repository, student_enrollment_repository,
        )
        from repositories._sql.academic_repository import (
            InstitutionRepository as SqlInst,
            YearRepository as SqlYear,
            BranchRepository as SqlBranch,
            SemesterRepository as SqlSem,
            SubjectRepository as SqlSubj,
            DivisionRepository as SqlDiv,
            ClassRepository as SqlClass,
            TeacherAssignmentRepository as SqlTA,
            StudentEnrollmentRepository as SqlSE,
        )

        # Each dispatcher module exposes exactly one *Repository class with the
        # same name as the SQL impl (the Mongo impl also has the same name,
        # which is the point of the dispatcher).
        assert institution_repository.InstitutionRepository is SqlInst
        assert year_repository.YearRepository is SqlYear
        assert branch_repository.BranchRepository is SqlBranch
        assert semester_repository.SemesterRepository is SqlSem
        assert subject_repository.SubjectRepository is SqlSubj
        assert division_repository.DivisionRepository is SqlDiv
        assert class_repository.ClassRepository is SqlClass
        assert teacher_assignment_repository.TeacherAssignmentRepository is SqlTA
        assert student_enrollment_repository.StudentEnrollmentRepository is SqlSE
