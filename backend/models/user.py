"""Pydantic models for users."""
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Role = Literal["teacher", "student"]


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    role: Role = "student"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


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


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
