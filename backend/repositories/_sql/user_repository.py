"""User repository — SQLAlchemy (async) implementation.
"""
import uuid
from typing import Optional

from sqlalchemy import func, select

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

    async def list_by_role(self, role: str) -> list[UserDB]:
        async with session_maker()() as s:
            stmt = select(UserORM).where(UserORM.role == role).order_by(UserORM.name)
            return [_to_user(r) for r in (await s.execute(stmt)).scalars().all()]

    async def search(
        self, role: Optional[str] = None, q: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> list[UserDB]:
        async with session_maker()() as s:
            stmt = select(UserORM)
            if role:
                stmt = stmt.where(UserORM.role == role)
            if q and q.strip():
                like = f"%{q.strip().lower()}%"
                stmt = stmt.where(func.lower(UserORM.name).like(like) | func.lower(UserORM.email).like(like))
            stmt = stmt.order_by(UserORM.name).limit(limit).offset(offset)
            return [_to_user(r) for r in (await s.execute(stmt)).scalars().all()]

    async def update_name(self, user_id: str, name: str) -> Optional[UserDB]:
        async with session_maker()() as s, s.begin():
            row = await s.get(UserORM, user_id)
            if row is None:
                return None
            row.name = name
            return _to_user(row)

    async def update_password_hash(self, user_id: str, password_hash: str) -> bool:
        async with session_maker()() as s, s.begin():
            row = await s.get(UserORM, user_id)
            if row is None:
                return False
            row.password_hash = password_hash
            return True

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())
