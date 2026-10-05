"""Deterministic idempotent demo seeding script for Lectify on RDS / SQLite."""
import argparse
import asyncio
import getpass
import logging
import os
import sys
import uuid
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import hash_password
from core.sql_db import _engine, close_sql, session_maker
from models.orm import (
    BranchORM,
    ClassORM,
    DivisionORM,
    InstitutionORM,
    SemesterORM,
    StudentEnrollmentORM,
    SubjectORM,
    TeacherAssignmentORM,
    UserORM,
    YearORM,
)

logger = logging.getLogger(__name__)

NAMESPACE = uuid.NAMESPACE_DNS

ADMIN_EMAIL = "admin@demo.lectify"
TEACHER_EMAIL = "teacher@demo.lectify"
STUDENT_EMAIL = "student@demo.lectify"
INSTITUTION_CODE = "LECTIFY_DEMO"


def _deterministic_id(key: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"lectify.demo.{key}"))


async def _get_or_create(
    session: AsyncSession, model: Any, defaults: Optional[Dict[str, Any]] = None, **kwargs
) -> Tuple[Any, bool]:
    stmt = select(model).filter_by(**kwargs)
    res = await session.execute(stmt)
    instance = res.scalars().first()
    if instance is not None:
        return instance, False
    params = dict(kwargs)
    if defaults:
        params.update(defaults)
    instance = model(**params)
    session.add(instance)
    await session.flush()
    return instance, True


async def seed(
    session: AsyncSession,
    passwords: Dict[str, str],
    reset_passwords: bool = False,
) -> Dict[str, int]:
    """Seed the demo academic hierarchy and users idempotently.

    Credentials are never stored or logged in repository artifacts.
    """
    counts = {"created": 0, "existing": 0}

    # 1. Institution
    inst_id = _deterministic_id(f"institution.{INSTITUTION_CODE}")
    inst, created = await _get_or_create(
        session,
        InstitutionORM,
        defaults={"name": "Lectify Demonstration College", "address": "Campus Drive 1"},
        id=inst_id,
        code=INSTITUTION_CODE,
    )
    counts["created" if created else "existing"] += 1

    # 2. Year
    year_id = _deterministic_id(f"year.1.{inst.id}")
    year, created = await _get_or_create(
        session,
        YearORM,
        defaults={"name": "First Year (FE)"},
        id=year_id,
        institution_id=inst.id,
        number=1,
    )
    counts["created" if created else "existing"] += 1

    # 3. Branch
    branch_id = _deterministic_id(f"branch.CS.{inst.id}")
    branch, created = await _get_or_create(
        session,
        BranchORM,
        defaults={"name": "Computer Science & Engineering"},
        id=branch_id,
        institution_id=inst.id,
        code="CS",
    )
    counts["created" if created else "existing"] += 1

    # 4. Semester
    sem_id = _deterministic_id(f"semester.1.{year.id}")
    sem, created = await _get_or_create(
        session,
        SemesterORM,
        defaults={"label": "Semester 1"},
        id=sem_id,
        year_id=year.id,
        number=1,
    )
    counts["created" if created else "existing"] += 1

    # 5. Division
    div_id = _deterministic_id(f"division.A.{sem.id}")
    div, created = await _get_or_create(
        session,
        DivisionORM,
        defaults={"capacity": 60},
        id=div_id,
        semester_id=sem.id,
        name="Div A",
    )
    counts["created" if created else "existing"] += 1

    # 6. Subject
    sub_id = _deterministic_id(f"subject.CS101.{sem.id}")
    subject, created = await _get_or_create(
        session,
        SubjectORM,
        defaults={"name": "Introduction to Computer Science", "credits": 4},
        id=sub_id,
        semester_id=sem.id,
        code="CS101",
    )
    counts["created" if created else "existing"] += 1

    # 7. Class
    class_id = _deterministic_id(f"class.{div.id}.{subject.id}")
    cls, created = await _get_or_create(
        session,
        ClassORM,
        defaults={"name": "Div A · CS101"},
        id=class_id,
        division_id=div.id,
        subject_id=subject.id,
    )
    counts["created" if created else "existing"] += 1

    # 8. Users (Admin, Teacher, Student)
    user_specs = [
        ("admin", ADMIN_EMAIL, "Demo Admin", passwords["admin"]),
        ("teacher", TEACHER_EMAIL, "Demo Teacher", passwords["teacher"]),
        ("student", STUDENT_EMAIL, "Demo Student", passwords["student"]),
    ]

    users = {}
    for role, email, name, pw in user_specs:
        uid = _deterministic_id(f"user.{email}")
        stmt = select(UserORM).filter_by(email=email)
        res = await session.execute(stmt)
        user = res.scalars().first()
        if user is None:
            user = UserORM(
                id=uid,
                name=name,
                email=email,
                role=role,
                password_hash=hash_password(pw),
            )
            session.add(user)
            await session.flush()
            counts["created"] += 1
        else:
            if reset_passwords:
                user.password_hash = hash_password(pw)
                session.add(user)
                await session.flush()
            counts["existing"] += 1
        users[role] = user

    # 9. Student Enrollment
    enr_id = _deterministic_id(f"enrollment.{users['student'].id}.{cls.id}")
    _, created = await _get_or_create(
        session,
        StudentEnrollmentORM,
        id=enr_id,
        student_id=users["student"].id,
        class_id=cls.id,
    )
    counts["created" if created else "existing"] += 1

    # 10. Teacher Assignment
    ta_id = _deterministic_id(f"assignment.{users['teacher'].id}.{cls.id}")
    _, created = await _get_or_create(
        session,
        TeacherAssignmentORM,
        id=ta_id,
        teacher_id=users["teacher"].id,
        class_id=cls.id,
    )
    counts["created" if created else "existing"] += 1

    await session.commit()
    return counts


def _get_passwords() -> Dict[str, str]:
    pw_vars = {
        "admin": "DEMO_ADMIN_PASSWORD",
        "teacher": "DEMO_TEACHER_PASSWORD",
        "student": "DEMO_STUDENT_PASSWORD",
    }
    passwords = {}
    missing = []

    for role, var in pw_vars.items():
        val = os.environ.get(var)
        if val:
            passwords[role] = val
        else:
            if sys.stdin.isatty():
                prompt_val = getpass.getpass(f"Enter {var} (min 8 chars): ")
                if prompt_val:
                    passwords[role] = prompt_val
                else:
                    missing.append(var)
            else:
                missing.append(var)

    if missing:
        sys.stderr.write(
            f"Missing required password environment variable(s): {', '.join(missing)}\n"
        )
        sys.exit(2)

    for role, pw in passwords.items():
        if len(pw) < 8:
            sys.stderr.write(
                f"Password for {pw_vars[role]} must be at least 8 characters long.\n"
            )
            sys.exit(2)

    return passwords


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Seed demo college hierarchy and users.")
    parser.add_argument(
        "--reset-passwords",
        action="store_true",
        help="Reset passwords of existing demo users if they already exist",
    )
    args = parser.parse_args(argv)

    passwords = _get_passwords()

    async def _run():
        try:
            maker = session_maker()
            async with maker() as session:
                counts = await seed(session, passwords, reset_passwords=args.reset_passwords)
                sys.stdout.write(
                    f"Demo seeding finished: {counts['created']} entities created, {counts['existing']} already existed.\n"
                )
        finally:
            await close_sql()

    asyncio.run(_run())
    return 0


if __name__ == "__main__":
    sys.exit(main())
