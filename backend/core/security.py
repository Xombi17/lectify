"""Password hashing + JWT token utilities."""
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import HTTPException

from core.config import get_settings

settings = get_settings()


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str, role: str, extra: Optional[dict] = None) -> str:
    import uuid

    now = datetime.now(timezone.utc)
    payload = {
        "jti": str(uuid.uuid4()),  # unique token identifier for revocation
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)).timestamp()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    # Enrollment / password-reset tokens share the signing key; they must never authenticate a session.
    if payload.get("type"):
        raise jwt.InvalidTokenError("Not an access token")
    return payload


def password_fingerprint(password_hash: str) -> str:
    """Short digest of the current hash: a reset link dies as soon as the password changes."""
    import hashlib

    return hashlib.sha256(password_hash.encode()).hexdigest()[:16]


def create_reset_token(user_id: str, password_hash: str, expires_minutes: int = 30) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "type": "pwreset",
        "pf": password_fingerprint(password_hash),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_reset_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Reset link has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=400, detail="Invalid reset link")
    if payload.get("type") != "pwreset":
        raise HTTPException(status_code=400, detail="Invalid reset link")
    return payload


def create_enrollment_token(class_id: str, qr_secret: str, expires_days: int = 30) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": class_id,
        "type": "enrollment",
        "qr_secret": qr_secret,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=expires_days)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_enrollment_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Enrollment token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=400, detail="Invalid enrollment token")
    if payload.get("type") != "enrollment":
        raise HTTPException(status_code=400, detail="Invalid token type")
    return payload
