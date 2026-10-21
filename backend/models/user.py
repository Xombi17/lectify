"""Pydantic models for users."""
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Role = Literal["teacher", "student", "admin"]


PASSWORD_MIN_LENGTH = 8


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=PASSWORD_MIN_LENGTH, max_length=128)
    role: Role = "student"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=PASSWORD_MIN_LENGTH, max_length=128)


class PasswordReset(BaseModel):
    token: str
    new_password: str = Field(..., min_length=PASSWORD_MIN_LENGTH, max_length=128)


class ProfileUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)


class AdminUserCreate(BaseModel):
    """Admin-created account (the only way to get a teacher or admin account)."""
    name: str = Field(..., min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=PASSWORD_MIN_LENGTH, max_length=128)
    role: Role = "teacher"


class ResetLink(BaseModel):
    reset_path: str
    expires_in_minutes: int


class UserDB(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: Role
    password_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserPublic(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: Role
    created_at: datetime


class TokenBlacklistDB(BaseModel):
    id: str
    jti: str
    expires_at: datetime
    revoked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
