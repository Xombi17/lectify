# Migrating LectureMind AI from MongoDB → PostgreSQL

The Emergent preview uses MongoDB because that is what the managed environment
provides. The code base was structured behind a **repository pattern** so that
*the only files you need to change* to switch to PostgreSQL are inside
`backend/repositories/` and `backend/core/db.py`.

This guide walks through it step by step.

---

## 1. What stays the same

| Layer | Stays the same? |
|-------|-----------------|
| FastAPI routes (`backend/routes/*.py`) | ✅ Yes |
| Pydantic models (`backend/models/*.py`) | ✅ Yes |
| AI service (`backend/services/ai_service.py`) | ✅ Yes |
| Storage service (`backend/services/storage_service.py`) | ✅ Yes |
| Auth + JWT (`backend/core/security.py`, `core/deps.py`) | ✅ Yes |
| Frontend (`/app/frontend`) | ✅ Yes |

You touch ~3 backend files and add SQLAlchemy as a dependency.

---

## 2. What you change

### 2.1 Add Postgres dependencies

In `backend/requirements.txt` add:

```
sqlalchemy>=2.0
asyncpg>=0.29
alembic>=1.13
```

Drop `motor` and `pymongo` if you wish (they're harmless if left in).

### 2.2 Replace `backend/core/db.py`

```python
# backend/core/db.py  (Postgres version)
import os
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.environ["DATABASE_URL"]  # postgresql+asyncpg://user:pass@host:5432/db

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session

async def close_db() -> None:
    await engine.dispose()
```

### 2.3 Define SQLAlchemy ORM models (new file)

Create `backend/models/orm.py` mirroring the Pydantic models:

```python
from sqlalchemy import Column, String, Boolean, DateTime, JSON, ForeignKey, Float
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone

Base = declarative_base()

class UserORM(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    role = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class LectureORM(Base):
    __tablename__ = "lectures"
    id = Column(String, primary_key=True)
    teacher_id = Column(String, ForeignKey("users.id"), index=True, nullable=False)
    title = Column(String, nullable=False)
    subject = Column(String, nullable=True)
    semester = Column(String, nullable=True)
    audio_object_key = Column(String, nullable=False)
    audio_filename = Column(String, nullable=False)
    audio_mime = Column(String, nullable=False)
    duration_seconds = Column(Float, nullable=True)
    status = Column(String, default="uploaded")
    transcript = Column(String, nullable=True)
    materials = Column(JSON, default=dict)
    error_message = Column(String, nullable=True)
    published = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
```

### 2.4 Replace `backend/repositories/user_repository.py`

```python
from sqlalchemy import select
from core.db import SessionLocal
from models.orm import UserORM
from models.user import UserDB
import uuid

class UserRepository:
    @staticmethod
    def new_id(): return str(uuid.uuid4())

    async def ensure_indexes(self): pass  # handled by ORM

    async def create(self, user: UserDB) -> UserDB:
        async with SessionLocal() as s, s.begin():
            s.add(UserORM(**user.model_dump()))
        return user

    async def get_by_email(self, email):
        async with SessionLocal() as s:
            row = (await s.execute(select(UserORM).where(UserORM.email == email))).scalar_one_or_none()
            return UserDB(**row.__dict__) if row else None  # strip _sa_instance_state in production

    async def get_by_id(self, user_id):
        async with SessionLocal() as s:
            row = await s.get(UserORM, user_id)
            return UserDB(**{k: v for k, v in row.__dict__.items() if not k.startswith("_")}) if row else None
```

Apply the same pattern to `lecture_repository.py`.

### 2.5 Switch storage backend

In `.env` set:

```
STORAGE_BACKEND=s3
OBJECT_STORAGE_ENDPOINT=http://minio:9000
OBJECT_STORAGE_BUCKET=lecture-audio
OBJECT_STORAGE_ACCESS_KEY=minioadmin
OBJECT_STORAGE_SECRET_KEY=minioadmin
```

Then implement `S3Storage(StorageService)` in `services/storage_service.py`
using `boto3.client("s3", endpoint_url=...)` — `upload_file` to save,
`generate_presigned_url("get_object", ...)` to serve playback.

### 2.6 Run Alembic migrations

```bash
alembic init alembic
# edit alembic/env.py to point at your DATABASE_URL and target_metadata=Base.metadata
alembic revision --autogenerate -m "init"
alembic upgrade head
```

### 2.7 Drop in `docker-compose.yml`

The included `docker-compose.yml` already runs Postgres + MinIO + the backend
+ the frontend. Once steps 2.1–2.6 are done, `docker compose up --build` will
boot the whole stack with PostgreSQL as the primary database.

---

## 3. What about existing data?

If you want to migrate Mongo data:

```bash
mongoexport --uri="$MONGO_URL" --db=lecturemind --collection=users --out=users.json
mongoexport --uri="$MONGO_URL" --db=lecturemind --collection=lectures --out=lectures.json
```

Then write a tiny Python script that reads the JSONL files and inserts via
SQLAlchemy (~30 lines). Both schemas are identical except for `_id` → `id`
which is already handled in the Mongo repos.

---

## 4. Rollback

Re-set `DATABASE_URL` env var to empty and switch `core/db.py` back to the
Mongo version — the rest of the app is untouched.

---

If you only ever care about the **self-hosted Docker Compose** version,
implementing Postgres from day one is fine too: just replace `core/db.py` and
the two repositories before your first `docker compose up`.
