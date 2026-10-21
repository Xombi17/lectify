"""Application configuration loaded from environment variables.

All settings come from environment / .env file. No hardcoded secrets.
"""

import os
import secrets
import sys
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
is_testing = "pytest" in sys.modules or (len(sys.argv) > 0 and "pytest" in sys.argv[0])
load_dotenv(ROOT_DIR / ".env", override=not is_testing)
if is_testing:
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from core.ssm_overlay import apply_ssm_overlay

apply_ssm_overlay()

if not is_testing:
    from core.db_secret import apply_db_secret_overlay

    apply_db_secret_overlay()


DEV_ENVS = ("dev", "test", "local")


class Settings:
    def __init__(self):
        self.ENV: str = os.environ.get("ENV", "production")
        # Service identity (microservices split)
        self.SERVICE_NAME: str = os.environ.get("SERVICE_NAME", "monolith")

        # Database
        self.DB_AUTO_CREATE: bool = (
            os.environ.get("DB_AUTO_CREATE", "true").lower() == "true"
        )
        self.DATABASE_BACKEND: str = os.environ.get("DATABASE_BACKEND", "postgres")
        self.DATABASE_URL: str = os.environ.get("DATABASE_URL", "")
        self.MONGO_URL: str = os.environ.get("MONGO_URL", "")
        self.DB_NAME: str = os.environ.get("DB_NAME", "lecturemind")

        # CORS
        self.CORS_ORIGINS: str = os.environ.get(
            "CORS_ORIGINS", "http://localhost:5173,http://localhost:3000"
        )

        # JWT
        self.JWT_SECRET: str = os.environ.get("JWT_SECRET", "change-me")
        self.JWT_ALGORITHM: str = os.environ.get("JWT_ALGORITHM", "HS256")
        self.JWT_EXPIRE_MINUTES: int = int(
            os.environ.get("JWT_EXPIRE_MINUTES", "10080")
        )

        # AI Provider selection
        self.AI_PROVIDER: str = os.environ.get("AI_PROVIDER", "gemini")

        # Gemini
        self.GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
        self.GEMINI_EMBED_MODEL: str = os.environ.get("GEMINI_EMBED_MODEL", "gemini-embedding-001")
        self.GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-3.7-flash")
        # Ordered failover chain (comma-separated). When the primary model
        # 429s/503s, calls fall through to the next model instead of sleeping
        # through a backoff. Empty = primary only (previous behavior).
        self.GEMINI_FALLBACK_MODELS: list = [
            m.strip() for m in os.environ.get("GEMINI_FALLBACK_MODELS", "").split(",") if m.strip()
        ]

        # NVIDIA NIM
        self.NIM_API_KEY: str = os.environ.get("NIM_API_KEY", "")
        self.NIM_BASE_URL: str = os.environ.get(
            "NIM_BASE_URL", "https://integrate.api.nvidia.com/v1"
        )
        self.NIM_CHAT_MODEL: str = os.environ.get(
            "NIM_CHAT_MODEL", "nvidia/nemotron-3-super-120b-a12b"
        )
        self.NIM_EMBED_MODEL: str = os.environ.get(
            "NIM_EMBED_MODEL", "nvidia/nv-embed-v1"
        )

        # Groq Whisper
        self.GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")
        self.WHISPER_MODEL: str = os.environ.get(
            "WHISPER_MODEL", "whisper-large-v3-turbo"
        )
        self.WHISPER_LANGUAGE: str = os.environ.get("WHISPER_LANGUAGE", "en")
        self.WHISPER_MAX_CONCURRENT: int = int(
            os.environ.get("WHISPER_MAX_CONCURRENT", "5")
        )
        self.WHISPER_COST_PER_MINUTE: float = float(
            os.environ.get("WHISPER_COST_PER_MINUTE", "0.00067")
        )

        # Transcription
        self.TRANSCRIPTION_PROVIDER: str = os.environ.get(
            "TRANSCRIPTION_PROVIDER", "groq"
        )
        self.TRANSCRIPTION_FALLBACK_PROVIDER: str = os.environ.get(
            "TRANSCRIPTION_FALLBACK_PROVIDER", "gemini"
        )

        # Phase 19 providers
        self.DEEPGRAM_API_KEY: str = os.environ.get("DEEPGRAM_API_KEY", "")
        self.DEEPGRAM_MODEL: str = os.environ.get("DEEPGRAM_MODEL", "nova-3")
        self.DEEPGRAM_LANGUAGE: str = os.environ.get("DEEPGRAM_LANGUAGE", "multi")
        self.DEEPGRAM_KEYTERMS: list = [
            k.strip() for k in os.environ.get("DEEPGRAM_KEYTERMS", "").split(",") if k.strip()
        ]
        self.DEEPGRAM_COST_PER_MINUTE: float = float(
            os.environ.get("DEEPGRAM_COST_PER_MINUTE", "0.0043")
        )
        self.DEEPGRAM_TIMEOUT_S: float = float(os.environ.get("DEEPGRAM_TIMEOUT_S", "600"))
        self.NAGA_AI_API_KEY: str = os.environ.get("NAGA_AI_API_KEY", "")
        self.NAGA_BASE_URL: str = os.environ.get("NAGA_BASE_URL", "https://api.naga.ac/v1")
        self.NAGA_CHAT_MODEL: str = os.environ.get(
            "NAGA_CHAT_MODEL", "nemotron-3-super-120b-a12b:free"
        )
        self.NAGA_WHISPER_MODEL: str = os.environ.get(
            "NAGA_WHISPER_MODEL", "whisper-large-v3:free"
        )
        # Radox AI: OpenAI-compatible gateway (https://radoxai.com/docs). The model id is not guessed:
        # list ids with `curl -H "Authorization: Bearer $RADOX_API_KEY" https://radoxai.com/v1/models`
        # and set RADOX_CHAT_MODEL. The provider is skipped until both key and model are set.
        self.RADOX_API_KEY: str = os.environ.get("RADOX_API_KEY", "")
        self.RADOX_BASE_URL: str = os.environ.get("RADOX_BASE_URL", "https://radoxai.com/v1")
        self.RADOX_CHAT_MODEL: str = os.environ.get("RADOX_CHAT_MODEL", "")
        # Groq's free OpenAI-compatible LLM endpoint; reuses GROQ_API_KEY (already used for Whisper)
        self.GROQ_BASE_URL: str = os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
        # Checked live against this key's GET /models (llama-3.3-70b-versatile no longer exists there)
        self.GROQ_LLM_MODEL: str = os.environ.get("GROQ_LLM_MODEL", "openai/gpt-oss-120b")
        # OpenRouter: OpenAI-compatible, many free ":free" models. Default checked live with this key
        # (JSON mode, ~1 s); `openrouter/free` auto-routes across free models if you prefer that.
        self.OPENROUTER_API_KEY: str = os.environ.get("OPENROUTER_API_KEY", "")
        self.OPENROUTER_BASE_URL: str = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.OPENROUTER_CHAT_MODEL: str = os.environ.get(
            "OPENROUTER_CHAT_MODEL", "minimax/minimax-m3.1-flash:free"
        )
        # Cloudflare Workers AI via its OpenAI-compatible endpoint. Needs an account id and an API token
        # with the "Workers AI" permission; skipped until both are set. Free tier is 10k neurons/day.
        self.CLOUDFLARE_ACCOUNT_ID: str = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
        self.CLOUDFLARE_API_TOKEN: str = os.environ.get("CLOUDFLARE_API_TOKEN", "")
        self.CLOUDFLARE_CHAT_MODEL: str = os.environ.get(
            "CLOUDFLARE_CHAT_MODEL", "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
        )
        # Extra Cloudflare models, each a separate chain member (cloudflare2, cloudflare3) so the round robin
        # spreads load across them and each gets its own cooldown. All checked live on the free plan.
        self.CLOUDFLARE_CHAT_MODEL_2: str = os.environ.get("CLOUDFLARE_CHAT_MODEL_2", "@cf/google/gemma-4-26b-a4b-it")
        self.CLOUDFLARE_CHAT_MODEL_3: str = os.environ.get(
            "CLOUDFLARE_CHAT_MODEL_3", "@cf/meta/llama-4-scout-17b-16e-instruct"
        )
        self.CLOUDFLARE_BASE_URL: str = os.environ.get(
            "CLOUDFLARE_BASE_URL",
            f"https://api.cloudflare.com/client/v4/accounts/{self.CLOUDFLARE_ACCOUNT_ID}/ai/v1",
        )
        # Round robin across every configured LLM provider (set LLM_ROUND_ROBIN=0 for strict priority order)
        self.LLM_ROUND_ROBIN: bool = os.environ.get("LLM_ROUND_ROBIN", "1").strip().lower() not in ("0", "false", "no")
        self.TRANSCRIPTION_PROVIDERS: list = [
            p.strip().lower()
            for p in os.environ.get("TRANSCRIPTION_PROVIDERS", "deepgram,naga,gemini").split(",")
            if p.strip()
        ]
        self.LLM_PROVIDERS: list = [
            p.strip().lower()
            # Providers without a key are skipped. Verified-working free ones first (groq, openrouter), then
            # naga (small daily budget), radox (needs credit), gemini, and nim last (its function 404s today)
            for p in os.environ.get("LLM_PROVIDERS", "groq,cloudflare,cloudflare2,cloudflare3,openrouter,naga,radox,gemini,nim").split(",")
            if p.strip()
        ]
        self.PROVIDER_COOLDOWN_SECONDS: float = float(
            os.environ.get("PROVIDER_COOLDOWN_SECONDS", "60")
        )
        self.LLM_TIMEOUT_S: float = float(os.environ.get("LLM_TIMEOUT_S", "120"))

        # Queue
        self.QUEUE_BACKEND: str = os.environ.get("QUEUE_BACKEND", "memory")
        self.QUEUE_MAX_RECEIVES: int = int(os.environ.get("QUEUE_MAX_RECEIVES", "5"))
        self.QUEUE_URL_TRANSCRIBE: str = os.environ.get("QUEUE_URL_TRANSCRIBE", "")
        self.QUEUE_URL_MATERIALS: str = os.environ.get("QUEUE_URL_MATERIALS", "")
        self.QUEUE_URL_EMBED: str = os.environ.get("QUEUE_URL_EMBED", "")
        self.QUEUE_URL_DLQ: str = os.environ.get("QUEUE_URL_DLQ", "")
        self.AWS_REGION: str = os.environ.get("AWS_REGION", "us-east-1")
        self.DRAIN_TIMEOUT_SECONDS: float = float(
            os.environ.get("DRAIN_TIMEOUT_SECONDS", "90")
        )

        # Worker concurrency
        self.TRANSCRIPTION_CONCURRENCY: int = int(
            os.environ.get("TRANSCRIPTION_CONCURRENCY", "3")
        )
        self.AI_CONCURRENCY: int = int(os.environ.get("AI_CONCURRENCY", "5"))
        self.EMBEDDING_CONCURRENCY: int = int(
            os.environ.get("EMBEDDING_CONCURRENCY", "10")
        )

        # Storage
        self.STORAGE_BACKEND: str = os.environ.get("STORAGE_BACKEND", "local")
        self.STORAGE_LOCAL_DIR: str = os.environ.get(
            "STORAGE_LOCAL_DIR", str(ROOT_DIR / "storage_data")
        )
        self.STORAGE_PUBLIC_BASE: str = os.environ.get(
            "STORAGE_PUBLIC_BASE", "/api/storage"
        )

        # App
        # Empty = derive from the requesting browser's origin (see routes/qr.py _app_base_url)
        self.APP_URL: str = os.environ.get("APP_URL", "")

        # Prometheus / Monitoring
        self.PROMETHEUS_ENABLED: bool = (
            os.environ.get("PROMETHEUS_ENABLED", "true") == "true"
        )
        self.PROMETHEUS_METRICS_PATH: str = os.environ.get(
            "PROMETHEUS_METRICS_PATH", "/metrics"
        )

        # SLA
        self.SLA_TARGET_PERCENT: float = float(
            os.environ.get("SLA_TARGET_PERCENT", "95.0")
        )
        self.SLA_ROLLING_DAYS: int = int(os.environ.get("SLA_ROLLING_DAYS", "7"))

        # Slack / Notifications
        self.SLACK_WEBHOOK_URL: str = os.environ.get("SLACK_WEBHOOK_URL", "")
        self.DAILY_SUMMARY_ENABLED: bool = (
            os.environ.get("DAILY_SUMMARY_ENABLED", "true") == "true"
        )
        self.DAILY_SUMMARY_TIME: str = os.environ.get("DAILY_SUMMARY_TIME", "22:00")
        self.LECTURE_READY_TOPIC_ARN: str = os.environ.get(
            "LECTURE_READY_TOPIC_ARN", ""
        )

        # Alerts
        self.ALERT_QUEUE_DEPTH_THRESHOLD: int = int(
            os.environ.get("ALERT_QUEUE_DEPTH_THRESHOLD", "50")
        )
        self.ALERT_DLQ_GROWTH_THRESHOLD: int = int(
            os.environ.get("ALERT_DLQ_GROWTH_THRESHOLD", "10")
        )
        self.ALERT_SLA_BREACH_THRESHOLD: float = float(
            os.environ.get("ALERT_SLA_BREACH_THRESHOLD", "90.0")
        )
        self.ALERT_COOLDOWN_SECONDS: int = int(
            os.environ.get("ALERT_COOLDOWN_SECONDS", "300")
        )

        # Features & Worker Pool
        self.FEATURE_FLASHCARDS_ENABLED: bool = (
            os.environ.get("FEATURE_FLASHCARDS_ENABLED", "true").lower() == "true"
        )
        self.FEATURE_RATE_LIMIT: bool = (
            os.environ.get("FEATURE_RATE_LIMIT", "false").lower() == "true"
        )
        self.WORKER_POOL_SIZE: int = int(os.environ.get("WORKER_POOL_SIZE", "10"))
        self.RATE_LIMIT_MAX_WAITS: int = int(
            os.environ.get("RATE_LIMIT_MAX_WAITS", "5")
        )
        self.RATE_LIMIT_MAX_SLEEP_MARGIN_S: int = int(
            os.environ.get("RATE_LIMIT_MAX_SLEEP_MARGIN_S", "30")
        )

        # New configs
        self.DB_POOL_SIZE: int = int(os.environ.get("DB_POOL_SIZE", "5"))
        self.DB_MAX_OVERFLOW: int = int(os.environ.get("DB_MAX_OVERFLOW", "2"))
        self.SSM_PREFIX: str = os.environ.get("SSM_PREFIX", "")
        self.NEO4J_SYNC_ENABLED: bool = (
            os.environ.get("NEO4J_SYNC_ENABLED", str(self.ENV in DEV_ENVS)).lower()
            == "true"
        )
        self.SLACK_SUMMARY_ENABLED: bool = (
            os.environ.get("SLACK_SUMMARY_ENABLED", str(self.ENV in DEV_ENVS)).lower()
            == "true"
        )

    def validate(self):
        if self.JWT_SECRET in ("", "change-me") and self.ENV not in DEV_ENVS:
            raise RuntimeError("JWT_SECRET must be set in production")
        if "*" in self.CORS_ORIGINS and self.ENV not in DEV_ENVS:
            raise RuntimeError("CORS_ORIGINS cannot contain '*' in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
