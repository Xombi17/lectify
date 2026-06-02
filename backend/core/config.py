"""Application configuration loaded from environment variables.

All settings come from environment / .env file. No hardcoded secrets.
"""
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


class Settings:
    # Database
    DATABASE_BACKEND: str = os.environ.get("DATABASE_BACKEND", "mongo")
    MONGO_URL: str = os.environ.get("MONGO_URL", "")
    DB_NAME: str = os.environ.get("DB_NAME", "lecturemind")
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "")  # SQL backend (postgres/sqlite)

    # CORS
    CORS_ORIGINS: str = os.environ.get("CORS_ORIGINS", "*")

    # JWT
    JWT_SECRET: str = os.environ.get("JWT_SECRET", "change-me")
    JWT_ALGORITHM: str = os.environ.get("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.environ.get("JWT_EXPIRE_MINUTES", "10080"))

    # Gemini
    GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    # Storage
    STORAGE_BACKEND: str = os.environ.get("STORAGE_BACKEND", "local")
    STORAGE_LOCAL_DIR: str = os.environ.get(
        "STORAGE_LOCAL_DIR", str(ROOT_DIR / "storage_data")
    )
    STORAGE_PUBLIC_BASE: str = os.environ.get("STORAGE_PUBLIC_BASE", "/api/storage")


@lru_cache
def get_settings() -> Settings:
    return Settings()
