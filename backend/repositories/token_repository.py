"""Token blacklist repository — JTI-based revocation tracking."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select

from core.sql_db import session_maker
from models.orm import TokenBlacklistORM


class TokenRepository:
    """Manages the token blacklist table for JWT revocation."""

    async def blacklist_token(self, jti: str, expires_at: datetime) -> None:
        """Add a token to the blacklist."""
        entry = TokenBlacklistORM(
            id=str(uuid4()),
            jti=jti,
            expires_at=expires_at,
        )
        async with session_maker()() as s, s.begin():
            s.add(entry)

    async def is_blacklisted(self, jti: str) -> bool:
        """Check if a token has been blacklisted (and not yet expired)."""
        async with session_maker()() as s:
            result = await s.execute(
                select(TokenBlacklistORM).where(
                    TokenBlacklistORM.jti == jti,
                    TokenBlacklistORM.expires_at > datetime.now(timezone.utc),
                )
            )
            return result.scalar_one_or_none() is not None

    async def clean_expired(self) -> int:
        """Remove expired blacklist entries. Returns count removed."""
        async with session_maker()() as s, s.begin():
            result = await s.execute(
                TokenBlacklistORM.__table__.delete().where(
                    TokenBlacklistORM.expires_at <= datetime.now(timezone.utc)
                )
            )
            return result.rowcount
