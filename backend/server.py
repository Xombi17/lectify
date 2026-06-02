"""Main FastAPI entrypoint."""
import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.db import close_db
from repositories.lecture_repository import LectureRepository
from repositories.user_repository import UserRepository
from routes.auth import router as auth_router
from routes.lectures import router as lectures_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ensure indexes on startup
    try:
        await UserRepository().ensure_indexes()
        await LectureRepository().ensure_indexes()
        logger.info("Mongo indexes ready")
    except Exception:
        logger.exception("Failed to ensure indexes")
    yield
    await close_db()


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
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
