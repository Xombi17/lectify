"""Load-test users: seed N students into the demo class, mint their JWTs offline.

    python -m scripts.load_users seed --count 200   # on an instance (SSM session, DB access)
    python -m scripts.load_users mint --count 200   # on the operator laptop, no DB

`mint` needs JWT_SECRET exported in the shell (from
`aws ssm get-parameter --name /lectify/JWT_SECRET --with-decryption`). The output
file holds valid student JWTs: it is gitignored and must be deleted after the test.
Run `seed_demo` first; seed needs LOAD_USER_PASSWORD (or a prompt).
"""
import argparse
import asyncio
import getpass
import json
import os
import sys
from pathlib import Path
from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import create_access_token, hash_password
from core.sql_db import close_sql, session_maker
from models.orm import StudentEnrollmentORM, TeacherAssignmentORM, UserORM
from scripts.seed_demo import TEACHER_EMAIL, _deterministic_id

DEFAULT_OUT = Path(__file__).resolve().parents[2] / "loadtest" / "out" / "tokens.json"


def load_email(i: int) -> str:
    return f"load{i:04d}@demo.lectify"


def load_user_id(i: int) -> str:
    return _deterministic_id(f"user.{load_email(i)}")


async def seed_load_users(session: AsyncSession, count: int, password: str) -> Dict[str, int]:
    teacher = (
        await session.execute(select(UserORM.id).where(UserORM.email == TEACHER_EMAIL))
    ).scalar_one_or_none()
    class_id = None
    if teacher:
        class_id = (
            await session.execute(
                select(TeacherAssignmentORM.class_id)
                .where(TeacherAssignmentORM.teacher_id == teacher, TeacherAssignmentORM.active.is_(True))
                .limit(1)
            )
        ).scalar_one_or_none()
    if not class_id:
        raise RuntimeError("demo class not found; run scripts.seed_demo first")

    emails = [load_email(i) for i in range(count)]
    enr_ids = {i: _deterministic_id(f"enrollment.{load_user_id(i)}.{class_id}") for i in range(count)}
    have_users = set(
        (await session.execute(select(UserORM.email).where(UserORM.email.in_(emails)))).scalars()
    )
    have_enr = set(
        (
            await session.execute(
                select(StudentEnrollmentORM.id).where(StudentEnrollmentORM.id.in_(list(enr_ids.values())))
            )
        ).scalars()
    )

    pw_hash = hash_password(password)  # one bcrypt for all users
    new_users = new_enr = 0
    for i in range(count):
        if load_email(i) not in have_users:
            session.add(
                UserORM(id=load_user_id(i), name=f"Load User {i}", email=load_email(i),
                        role="student", password_hash=pw_hash)
            )
            new_users += 1
    await session.flush()  # users before enrollments (FK)
    for i in range(count):
        if enr_ids[i] not in have_enr:
            session.add(StudentEnrollmentORM(id=enr_ids[i], class_id=class_id, student_id=load_user_id(i)))
            new_enr += 1
    await session.commit()
    return {"created": new_users + new_enr, "users": new_users, "enrollments": new_enr}


def mint_tokens(count: int) -> List[str]:
    return [create_access_token(load_user_id(i), "student") for i in range(count)]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("seed")
    s.add_argument("--count", type=int, default=200)
    m = sub.add_parser("mint")
    m.add_argument("--count", type=int, default=200)
    m.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = p.parse_args(argv)

    if args.cmd == "mint":
        tokens = mint_tokens(args.count)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        data = [{"email": load_email(i), "token": t} for i, t in enumerate(tokens)]
        fd = os.open(args.out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(data, f)
        os.chmod(args.out, 0o600)
        sys.stdout.write(f"Minted {len(tokens)} tokens -> {args.out}\n")
        return 0

    password = os.environ.get("LOAD_USER_PASSWORD") or (
        getpass.getpass("LOAD_USER_PASSWORD (min 8 chars): ") if sys.stdin.isatty() else ""
    )
    if len(password) < 8:
        sys.stderr.write("LOAD_USER_PASSWORD must be at least 8 characters.\n")
        return 2

    async def _run():
        try:
            async with session_maker()() as session:
                c = await seed_load_users(session, args.count, password)
                sys.stdout.write(f"Load users: {c['users']} users, {c['enrollments']} enrollments created.\n")
        finally:
            await close_sql()

    asyncio.run(_run())
    return 0


if __name__ == "__main__":
    sys.exit(main())
