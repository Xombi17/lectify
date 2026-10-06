"""Seed Fr. CRCE academic structure: branches, batches, years, semesters, divisions.

Idempotent — safe to re-run. Uses deterministic uuid5 ids so repeated runs
upsert instead of duplicating.

Usage (from repo root):
    cd backend && ENV=dev DATABASE_URL='sqlite+aiosqlite:///./lecturemind.db' \\
        .venv/bin/python -m scripts.seed_crce
"""
import asyncio
import logging
import sys
import uuid

sys.path.insert(0, ".")

from datetime import date

from sqlalchemy import inspect, text

from core.sql_db import _engine, close_sql, init_models, session_maker
from models.orm import Base

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

NAMESPACE = uuid.NAMESPACE_DNS

INSTITUTION_CODE = "FRCRCE"
INSTITUTION_NAME = "Fr. Conceicao Rodrigues College of Engineering"

BRANCHES = [
    ("COMPS", "Computer Engineering"),
    ("CSE", "Computer Science and Engineering"),
    ("ECS", "Electronics and Computer Science"),
    ("MECH", "Mechanical Engineering"),
]

BATCHES = [
    # (graduating_year, admission_year, name)
    (2028, 2024, "Batch of 2028"),
    (2029, 2025, "Batch of 2029"),
]

YEAR_NAMES = {1: "First Year", 2: "Second Year", 3: "Third Year", 4: "Fourth Year"}

# (branch_code, graduating_year) -> division names
DIVISION_MATRIX = {
    ("COMPS", 2028): ["COMPS A", "COMPS B", "COMPS C"],
    ("COMPS", 2029): ["COMPS A", "COMPS B", "COMPS C"],
    ("CSE", 2028): ["CSE"],
    ("CSE", 2029): ["CSE A", "CSE B", "CSE C"],
    ("ECS", 2028): ["ECS"],
    ("ECS", 2029): ["ECS"],
    ("MECH", 2028): ["Mechanical"],
    ("MECH", 2029): ["Mechanical"],
}


def _uid(*parts: str) -> str:
    return str(uuid.uuid5(NAMESPACE, "lectify.crce." + ".".join(parts)))


async def _ensure_ddl() -> None:
    """Additive migration for dev SQLite/Postgres: batches table + division columns."""
    await init_models()  # creates missing tables (batches); never alters existing ones
    eng = _engine()
    async with eng.begin() as conn:
        def _inspect(sync_conn):
            insp = inspect(sync_conn)
            div_cols = {c["name"]: c for c in insp.get_columns("divisions")}
            try:
                class_cols = {c["name"] for c in insp.get_columns("classes")}
                class_count = sync_conn.execute(text("SELECT COUNT(*) FROM classes")).scalar()
            except Exception:
                class_cols, class_count = set(), 0
            div_count = sync_conn.execute(text("SELECT COUNT(*) FROM divisions")).scalar()
            return div_cols, div_count, class_cols, class_count
        div_cols, div_count, class_cols, class_count = await conn.run_sync(_inspect)
        for col, ddl_type in (("branch_id", "VARCHAR(64)"), ("batch_id", "VARCHAR(64)")):
            if col not in div_cols:
                logger.info("Adding divisions.%s", col)
                await conn.execute(text(f"ALTER TABLE divisions ADD COLUMN {col} {ddl_type}"))
        # Legacy tables were created with divisions.semester_id NOT NULL.
        # Cohort divisions carry branch+batch instead, so relax it. The table
        # is rebuilt (safe: refuse if it already holds rows).
        sem = div_cols.get("semester_id")
        if sem is not None and not sem.get("nullable", True):
            if div_count:
                raise RuntimeError(
                    f"divisions table holds {div_count} rows with legacy NOT NULL "
                    "semester_id — migrate manually instead of auto-rebuilding."
                )
            logger.info("Rebuilding empty divisions table with nullable semester_id")
            await conn.run_sync(lambda sc: Base.metadata.tables["divisions"].drop(sc))
            await conn.run_sync(lambda sc: Base.metadata.tables["divisions"].create(sc))
        # Classes gained batch_semester_id (teaching instances). Rebuild when
        # the column is missing — safe only while the table is empty.
        if "batch_semester_id" not in class_cols:
            if class_count:
                raise RuntimeError(
                    f"classes table holds {class_count} legacy rows — migrate manually."
                )
            logger.info("Rebuilding empty classes table with batch_semester_id")
            await conn.run_sync(lambda sc: Base.metadata.tables["classes"].drop(sc, checkfirst=True))
            await conn.run_sync(lambda sc: Base.metadata.tables["classes"].create(sc))


async def _get_or_create(session, model, key, defaults):
    from sqlalchemy import select

    stmt = select(model).filter_by(**key)
    row = (await session.execute(stmt)).scalars().first()
    if row is not None:
        return row, False
    row = model(**key, **defaults)
    session.add(row)
    await session.flush()
    return row, True


async def seed() -> dict:
    from sqlalchemy import select as sa_select

    from models.orm import BatchORM, BatchSemesterORM, BranchORM, DivisionORM, InstitutionORM, SemesterORM, YearORM

    counts = {"created": 0, "existing": 0}

    def tally(created: bool):
        counts["created" if created else "existing"] += 1

    maker = session_maker()
    async with maker() as s:
        # Single-college app: adopt the existing institution if there is
        # exactly one (e.g. created earlier via the admin UI), so we never
        # fork the hierarchy into a duplicate college.
        existing = (await s.execute(sa_select(InstitutionORM))).scalars().all()
        if len(existing) == 1:
            inst = existing[0]
            logger.info("Adopting existing institution %r (code %s)", inst.name, inst.code)
            counts["existing"] += 1
        else:
            inst, created = await _get_or_create(
                s, InstitutionORM, {"code": INSTITUTION_CODE},
                {"id": _uid("institution"), "name": INSTITUTION_NAME, "address": "Mumbai"},
            )
            tally(created)
        institution_id = inst.id

        branches = {}
        for code, name in BRANCHES:
            b, created = await _get_or_create(
                s, BranchORM, {"institution_id": institution_id, "code": code},
                {"id": _uid("branch", code), "name": name},
            )
            tally(created)
            branches[code] = b

        batches = {}
        for grad, adm, name in BATCHES:
            b, created = await _get_or_create(
                s, BatchORM, {"institution_id": institution_id, "graduating_year": grad},
                {"id": _uid("batch", str(grad)), "admission_year": adm, "name": name},
            )
            tally(created)
            batches[grad] = b

        # Years 1-4 + semesters 1-8 (curriculum skeleton for future subjects)
        for number in (1, 2, 3, 4):
            y, created = await _get_or_create(
                s, YearORM, {"institution_id": institution_id, "number": number},
                {"id": _uid("year", str(number)), "name": YEAR_NAMES[number]},
            )
            tally(created)
            for sem_no in (2 * number - 1, 2 * number):
                sem, created = await _get_or_create(
                    s, SemesterORM, {"year_id": y.id, "number": sem_no},
                    {"id": _uid("semester", str(sem_no)), "label": f"Semester {sem_no}"},
                )
                tally(created)

        # Divisions: cohort-based (branch × batch), no semester placement
        for (branch_code, grad), names in DIVISION_MATRIX.items():
            branch = branches[branch_code]
            batch = batches[grad]
            for name in names:
                _, created = await _get_or_create(
                    s, DivisionORM,
                    {"branch_id": branch.id, "batch_id": batch.id, "name": name},
                    {"id": _uid("division", branch_code, str(grad), name), "semester_id": None},
                )
                tally(created)

        # Cohort progression: map each batch onto semesters 1-8 with Mumbai
        # University-style windows (odd sem Jul-Dec, even sem Jan-Jun).
        # "Current semester" is derived from these dates, never stored.
        sem_by_number = {}
        for y in (await s.execute(sa_select(SemesterORM))).scalars().all():
            sem_by_number[y.number] = y
        for grad, batch in batches.items():
            adm = batch.admission_year
            for n in range(1, 9):
                start_year = adm + (n - 1) // 2
                if n % 2 == 1:
                    starts, ends = date(start_year, 7, 1), date(start_year, 12, 31)
                else:
                    starts, ends = date(start_year + 1, 1, 1), date(start_year + 1, 6, 30)
                ay = f"{start_year}-{str(start_year + 1)[-2:]}"
                _, created = await _get_or_create(
                    s, BatchSemesterORM,
                    {"batch_id": batch.id, "semester_id": sem_by_number[n].id},
                    {"id": _uid("batchsemester", str(grad), str(n)),
                     "academic_year": ay, "starts_on": starts, "ends_on": ends},
                )
                tally(created)

        await s.commit()
    return counts


async def main() -> int:
    await _ensure_ddl()
    try:
        counts = await seed()
    finally:
        await close_sql()
    print(f"Fr. CRCE seeding finished: {counts['created']} created, {counts['existing']} already existed.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
