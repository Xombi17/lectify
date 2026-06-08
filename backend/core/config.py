"""Application configuration loaded from environment variables.

All settings come from environment / .env file. No hardcoded secrets.
"""
import os
import secrets
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


class Settings:
    # Database
    DATABASE_BACKEND: str = os.environ.get("DATABASE_BACKEND", "postgres")
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "")  # postgres:// or sqlite+aiosqlite://

    # CORS
    CORS_ORIGINS: str = os.environ.get("CORS_ORIGINS", "*")

    # JWT
    JWT_SECRET: str = os.environ.get("JWT_SECRET", secrets.token_urlsafe(32))
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

    # Groq Whisper (OpenAI-compatible, via Groq LPU inference)
    GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")
    WHISPER_MODEL: str = os.environ.get("WHISPER_MODEL", "whisper-large-v3-turbo")
    WHISPER_LANGUAGE: str = os.environ.get("WHISPER_LANGUAGE", "en")
    WHISPER_MAX_CONCURRENT: int = int(os.environ.get("WHISPER_MAX_CONCURRENT", "5"))
    WHISPER_COST_PER_MINUTE: float = float(os.environ.get("WHISPER_COST_PER_MINUTE", "0.00067"))

    # Transcription
    TRANSCRIPTION_PROVIDER: str = os.environ.get("TRANSCRIPTION_PROVIDER", "groq")
    TRANSCRIPTION_FALLBACK_PROVIDER: str = os.environ.get("TRANSCRIPTION_FALLBACK_PROVIDER", "gemini")

    # App
    APP_URL: str = os.environ.get("APP_URL", "http://localhost:5173")


@lru_cache
def get_settings() -> Settings:
    return Settings()
