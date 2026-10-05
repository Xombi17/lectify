"""Main FastAPI entrypoint."""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from prometheus_fastapi_instrumentator import Instrumentator
from core.sql_db import close_sql, init_models
from repositories.attempt_repository import AttemptRepository
from repositories.bookmark_repository import BookmarkRepository
from repositories.chat_repository import ChatRepository
from repositories.flashcard_review_repository import FlashcardReviewRepository
from repositories.lecture_repository import LectureRepository
from repositories.user_repository import UserRepository
from routes.analytics import router as analytics_router
from routes.auth import router as auth_router
from routes.chat import router as chat_router
from routes.enrollment import router as enrollment_router
from routes.lectures import router as lectures_router
from routes.search import router as search_router
from routes.study import router as study_router
from routes.admin import router as admin_router
from routes.qr import router as qr_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings().validate()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ensure indexes/tables on startup
    try:
        await init_models()
        logger.info("SQL tables ready (%s)", settings.DATABASE_BACKEND)
        await UserRepository().ensure_indexes()
        await LectureRepository().ensure_indexes()
        await ChatRepository().ensure_indexes()
        await AttemptRepository().ensure_indexes()
        logger.info("Database indexes ready (backend=%s)", settings.DATABASE_BACKEND)
    except Exception:
        logger.exception("Failed to ensure indexes/tables")

    # Optional: verify Redis connectivity (non-fatal)
    try:
        from core.queue import get_redis
        redis = get_redis()
        await redis.ping()
        logger.info("Redis connection OK")
    except Exception as e:
        logger.warning("Redis not available at startup: %s (workers connect independently)", e)

    # Token cleanup background task — every 6 hours
    _token_cleanup_task = None

    async def _cleanup_expired_tokens():
        """Periodically clean expired token blacklist entries."""
        while True:
            try:
                from repositories.token_repository import TokenRepository
                repo = TokenRepository()
                removed = await repo.clean_expired()
                if removed:
                    logger.info("Cleaned %d expired token blacklist entries", removed)
            except Exception as e:
                logger.warning("Token cleanup failed: %s", e)
            await asyncio.sleep(6 * 3600)  # 6 hours

    _token_cleanup_task = asyncio.create_task(_cleanup_expired_tokens())
    logger.info("Token cleanup background task started (every 6h)")

    # Monitoring background loop — SLA checks + daily summary + alerts
    _monitor_task = None
    if settings.SLACK_SUMMARY_ENABLED and (settings.DAILY_SUMMARY_ENABLED or settings.ALERT_QUEUE_DEPTH_THRESHOLD > 0):

        async def _run_monitoring_loop():
            """Periodic monitoring — daily summary + alert checks."""
            from datetime import datetime, timezone

            from services.alert_service import alert_manager
            from services.monitoring_service import compute_daily_sla, generate_daily_summary, send_slack_webhook

            cfg = get_settings()

            # Wait for server to be fully up before starting checks
            await asyncio.sleep(30)

            while True:
                try:
                    today = datetime.now(timezone.utc).date()
                    try:
                        sla = await compute_daily_sla(today)
                        # Check SLA breach
                        await alert_manager.check_sla_breach(
                            sla["sla_percent"],
                            cfg.SLA_TARGET_PERCENT,
                            today.isoformat(),
                        )
                    except Exception as inner:
                        logger.warning("SLA check failed (non-fatal): %s", inner)

                    # Send daily summary at configured time (check every 5 min)
                    if cfg.DAILY_SUMMARY_ENABLED and cfg.SLACK_WEBHOOK_URL:
                        try:
                            summary_time = cfg.DAILY_SUMMARY_TIME.split(":")
                            target_hour, target_min = int(summary_time[0]), int(summary_time[1])
                            now = datetime.now(timezone.utc)
                            if now.hour == target_hour and now.minute == target_min:
                                summary = await generate_daily_summary(today)
                                await send_slack_webhook(summary)
                        except (ValueError, IndexError):
                            pass  # Invalid time format — silently skip

                except Exception:
                    logger.exception("Monitoring loop iteration failed")

                # Sleep 5 minutes between checks
                await asyncio.sleep(300)

        _monitor_task = asyncio.create_task(_run_monitoring_loop())
        logger.info("Monitoring background loop started")

    yield
    # Cancel background tasks on shutdown
    if _token_cleanup_task is not None:
        _token_cleanup_task.cancel()
    if _monitor_task is not None:
        _monitor_task.cancel()
    await close_sql()


app = FastAPI(title="LectureMind AI", lifespan=lifespan)

# Prometheus instrumentation — created at module level, exposed in lifespan
instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
)

api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"service": f"{settings.SERVICE_NAME}-service" if settings.SERVICE_NAME != "monolith" else "lecturemind-api", "status": "ok"}


@api_router.get("/health")
async def health():
    """Health check with real dependency connectivity probes."""
    from datetime import datetime, timezone

    from core.sql_db import session_maker
    from services.storage_service import get_storage

    checks = {}

    # Database check (all services need this)
    try:
        async with session_maker()() as s:
            from sqlalchemy import text
            await s.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    # Storage check (only monolith and ingestion/interaction need this)
    if settings.SERVICE_NAME in ("monolith", "ingestion", "interaction"):
        try:
            storage = get_storage()
            await storage.list_objects(prefix="health_check/", max_keys=1)
            checks["storage"] = "ok"
        except AttributeError:
            checks["storage"] = "ok"
        except Exception as e:
            checks["storage"] = f"error: {e}"

    # Redis check (only monolith and ingestion/interaction need this)
    if settings.SERVICE_NAME in ("monolith", "ingestion", "interaction"):
        try:
            from core.queue import get_redis
            redis = get_redis()
            await redis.ping()
            checks["redis"] = "ok"
        except Exception as e:
            checks["redis"] = f"error: {e}"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": overall, "checks": checks, "timestamp": datetime.now(timezone.utc).isoformat()}


# Conditional routing based on SERVICE_NAME
if settings.SERVICE_NAME == "auth":
    api_router.include_router(auth_router)
elif settings.SERVICE_NAME == "academic":
    api_router.include_router(admin_router)
    api_router.include_router(enrollment_router)
    api_router.include_router(qr_router)
elif settings.SERVICE_NAME == "interaction":
    api_router.include_router(chat_router)
    api_router.include_router(study_router)
elif settings.SERVICE_NAME == "ingestion":
    api_router.include_router(lectures_router)
elif settings.SERVICE_NAME == "search":
    api_router.include_router(search_router)
else:
    # default monolith behavior
    api_router.include_router(auth_router)
    api_router.include_router(lectures_router)
    api_router.include_router(chat_router)
    api_router.include_router(enrollment_router)
    api_router.include_router(search_router)
    api_router.include_router(analytics_router)
    api_router.include_router(study_router)
    api_router.include_router(admin_router)
    api_router.include_router(qr_router)

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus instrumentation — must happen BEFORE lifespan starts
if settings.PROMETHEUS_ENABLED:
    instrumentator.instrument(app).expose(app, endpoint=settings.PROMETHEUS_METRICS_PATH)
    logger.info("Prometheus metrics enabled at %s", settings.PROMETHEUS_METRICS_PATH)
