"""Application configuration loaded from environment variables.

All settings come from environment / .env file. No hardcoded secrets.
"""
import os
import secrets
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
is_testing = "pytest" in sys.modules or (len(sys.argv) > 0 and "pytest" in sys.argv[0])
load_dotenv(ROOT_DIR / ".env", override=not is_testing)
if is_testing:
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"



class Settings:
    # Service identity (microservices split)
    SERVICE_NAME: str = os.environ.get("SERVICE_NAME", "monolith")

    # Database
    DATABASE_BACKEND: str = os.environ.get("DATABASE_BACKEND", "postgres")
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "")  # postgres:// or sqlite+aiosqlite://
    MONGO_URL: str = os.environ.get("MONGO_URL", "")
    DB_NAME: str = os.environ.get("DB_NAME", "lecturemind")

    # CORS
    CORS_ORIGINS: str = os.environ.get("CORS_ORIGINS", "*")

    # JWT
    JWT_SECRET: str = os.environ.get("JWT_SECRET", "change-me")
    JWT_ALGORITHM: str = os.environ.get("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.environ.get("JWT_EXPIRE_MINUTES", "10080"))

    # AI Provider selection
    AI_PROVIDER: str = os.environ.get("AI_PROVIDER", "gemini")  # "nim" | "gemini"

    # Gemini (used when AI_PROVIDER=gemini, or as transcription fallback)
    GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    # NVIDIA NIM (used when AI_PROVIDER=nim)
    NIM_API_KEY: str = os.environ.get("NIM_API_KEY", "")
    NIM_BASE_URL: str = os.environ.get("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    NIM_CHAT_MODEL: str = os.environ.get("NIM_CHAT_MODEL", "meta/llama-3.1-405b-instruct")
    NIM_EMBED_MODEL: str = os.environ.get("NIM_EMBED_MODEL", "nvidia/nv-embed-v1")

    # Groq Whisper
    GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")
    WHISPER_MODEL: str = os.environ.get("WHISPER_MODEL", "whisper-large-v3-turbo")
    WHISPER_LANGUAGE: str = os.environ.get("WHISPER_LANGUAGE", "en")
    WHISPER_MAX_CONCURRENT: int = int(os.environ.get("WHISPER_MAX_CONCURRENT", "5"))
    WHISPER_COST_PER_MINUTE: float = float(os.environ.get("WHISPER_COST_PER_MINUTE", "0.00067"))

    # Transcription
    TRANSCRIPTION_PROVIDER: str = os.environ.get("TRANSCRIPTION_PROVIDER", "groq")
    TRANSCRIPTION_FALLBACK_PROVIDER: str = os.environ.get("TRANSCRIPTION_FALLBACK_PROVIDER", "gemini")

    # Redis / Queue
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    REDIS_MAX_CONNECTIONS: int = int(os.environ.get("REDIS_MAX_CONNECTIONS", "20"))

    # Worker concurrency (overridable per deployment)
    TRANSCRIPTION_CONCURRENCY: int = int(os.environ.get("TRANSCRIPTION_CONCURRENCY", "3"))
    AI_CONCURRENCY: int = int(os.environ.get("AI_CONCURRENCY", "5"))
    EMBEDDING_CONCURRENCY: int = int(os.environ.get("EMBEDDING_CONCURRENCY", "10"))

    # Storage
    STORAGE_BACKEND: str = os.environ.get("STORAGE_BACKEND", "local")
    STORAGE_LOCAL_DIR: str = os.environ.get("STORAGE_LOCAL_DIR", str(ROOT_DIR / "storage_data"))
    STORAGE_PUBLIC_BASE: str = os.environ.get("STORAGE_PUBLIC_BASE", "/api/storage")

    # App
    APP_URL: str = os.environ.get("APP_URL", "http://localhost:5173")

    # Prometheus / Monitoring (Phase 7)
    PROMETHEUS_ENABLED: bool = os.environ.get("PROMETHEUS_ENABLED", "true") == "true"
    PROMETHEUS_METRICS_PATH: str = os.environ.get("PROMETHEUS_METRICS_PATH", "/metrics")

    # SLA (Phase 7)
    SLA_TARGET_PERCENT: float = float(os.environ.get("SLA_TARGET_PERCENT", "95.0"))
    SLA_ROLLING_DAYS: int = int(os.environ.get("SLA_ROLLING_DAYS", "7"))

    # Slack / Notifications (Phase 7)
    SLACK_WEBHOOK_URL: str = os.environ.get("SLACK_WEBHOOK_URL", "")
    DAILY_SUMMARY_ENABLED: bool = os.environ.get("DAILY_SUMMARY_ENABLED", "true") == "true"
    DAILY_SUMMARY_TIME: str = os.environ.get("DAILY_SUMMARY_TIME", "22:00")

    # Alerts (Phase 7)
    ALERT_QUEUE_DEPTH_THRESHOLD: int = int(os.environ.get("ALERT_QUEUE_DEPTH_THRESHOLD", "50"))
    ALERT_DLQ_GROWTH_THRESHOLD: int = int(os.environ.get("ALERT_DLQ_GROWTH_THRESHOLD", "10"))
    ALERT_SLA_BREACH_THRESHOLD: float = float(os.environ.get("ALERT_SLA_BREACH_THRESHOLD", "90.0"))
    ALERT_COOLDOWN_SECONDS: int = int(os.environ.get("ALERT_COOLDOWN_SECONDS", "300"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
