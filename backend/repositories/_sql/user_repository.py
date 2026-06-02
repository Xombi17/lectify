"""User repository — SQLAlchemy (async) implementation.

Public surface MUST match `_mongo/user_repository.UserRepository` so callers
don't notice the swap.
"""
import uuid
from typing import Optional

from sqlalchemy import select

from core.sql_db import session_maker
from models.orm import UserORM
from models.user import UserDB


def _to_user(row: UserORM) -> UserDB:
    return UserDB(
        id=row.id,
        name=row.name,
        email=row.email,
        role=row.role,
        password_hash=row.password_hash,
        created_at=row.created_at,
    )


class UserRepository:
    async def ensure_indexes(self) -> None:
        # Handled by ORM column definitions (unique=True on email).
        return None

    async def create(self, user: UserDB) -> UserDB:
        async with session_maker()() as s, s.begin():
            s.add(UserORM(
                id=user.id,
                name=user.name,
                email=user.email,
                role=user.role,
                password_hash=user.password_hash,
                created_at=user.created_at,
            ))
        return user

    async def get_by_id(self, user_id: str) -> Optional[UserDB]:
        async with session_maker()() as s:
            row = await s.get(UserORM, user_id)
            return _to_user(row) if row else None

    async def get_by_email(self, email: str) -> Optional[UserDB]:
        async with session_maker()() as s:
            stmt = select(UserORM).where(UserORM.email == email.lower())
            row = (await s.execute(stmt)).scalar_one_or_none()
            return _to_user(row) if row else None

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())
