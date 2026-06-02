"""Main FastAPI entrypoint."""
import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.db import close_db
from core.sql_db import close_sql, init_models as init_sql_models
from repositories.attempt_repository import AttemptRepository
from repositories.bookmark_repository import BookmarkRepository
from repositories.chat_repository import ChatRepository
from repositories.flashcard_review_repository import FlashcardReviewRepository
from repositories.lecture_repository import LectureRepository
from repositories.user_repository import UserRepository
from routes.analytics import router as analytics_router
from routes.auth import router as auth_router
from routes.chat import router as chat_router
from routes.lectures import router as lectures_router
from routes.search import router as search_router
from routes.study import router as study_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ensure indexes/tables on startup
    try:
        if settings.DATABASE_BACKEND.lower() != "mongo":
            await init_sql_models()
            logger.info("SQL tables ready (%s)", settings.DATABASE_BACKEND)
        await UserRepository().ensure_indexes()
        await LectureRepository().ensure_indexes()
        await ChatRepository().ensure_indexes()
        await AttemptRepository().ensure_indexes()
        logger.info("Database indexes ready (backend=%s)", settings.DATABASE_BACKEND)
    except Exception:
        logger.exception("Failed to ensure indexes/tables")
    yield
    if settings.DATABASE_BACKEND.lower() == "mongo":
        await close_db()
    else:
        await close_sql()


app = FastAPI(title="LectureMind AI", lifespan=lifespan)

api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"service": "lecturemind-api", "status": "ok"}


@api_router.get("/health")
async def health():
    return {"status": "ok"}


api_router.include_router(auth_router)
api_router.include_router(lectures_router)
api_router.include_router(chat_router)
api_router.include_router(search_router)
api_router.include_router(analytics_router)
api_router.include_router(study_router)
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
