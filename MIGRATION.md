# Migrating LectureMind AI from MongoDB → PostgreSQL

The Emergent preview uses MongoDB because that is what the managed environment
provides. The code is now structured so the swap is **a single env-var flip**:
set `DATABASE_BACKEND=postgres` + `DATABASE_URL=...` and you're done.

---

## TL;DR

```bash
# Self-host with Postgres + MinIO:
cp .env.docker.example .env
# fill in GEMINI_API_KEY and JWT_SECRET
docker compose up --build
```

The provided `docker-compose.yml` already wires this up:

| Service     | Image                 | What it stores                          |
|-------------|-----------------------|-----------------------------------------|
| `postgres`  | postgres:16-alpine    | users / lectures / chat / attempts      |
| `minio`     | minio/minio:latest    | uploaded lecture audio (S3-compatible)  |
| `backend`   | (built from ./backend) | FastAPI (ffmpeg baked into the image)  |
| `frontend`  | (built from ./frontend) | nginx serving the React build         |

---

## How the swap works (architecture)

Two pluggable layers were designed for this:

### 1. Repository pattern (`backend/repositories/`)

```
repositories/
├── _mongo/                ← original MongoDB implementations
│   ├── user_repository.py
│   ├── lecture_repository.py
│   ├── chat_repository.py
│   └── attempt_repository.py
├── _sql/                  ← SQLAlchemy-async implementations (Postgres, SQLite)
│   ├── user_repository.py
│   ├── lecture_repository.py
│   ├── chat_repository.py
│   └── attempt_repository.py
├── user_repository.py     ← thin dispatcher (re-exports based on env)
├── lecture_repository.py
├── chat_repository.py
└── attempt_repository.py
```

Routes / services import `from repositories.user_repository import UserRepository`
exactly as before. The dispatcher picks the right implementation:

```python
# repositories/user_repository.py
from core.config import get_settings
if get_settings().DATABASE_BACKEND.lower() == "mongo":
    from repositories._mongo.user_repository import UserRepository
else:
    from repositories._sql.user_repository import UserRepository
```

### 2. Storage abstraction (`backend/services/storage_service.py`)

```
StorageService (ABC)
├── LocalStorage     ← writes files under STORAGE_LOCAL_DIR (preview)
└── S3Storage        ← MinIO / Cloudflare R2 / AWS S3 (self-host)
```

Same dispatch pattern via `STORAGE_BACKEND=local|s3`.

---

## Env variables

### Preview (Emergent / MongoDB / local FS)
```env
DATABASE_BACKEND=mongo
MONGO_URL=mongodb://localhost:27017
DB_NAME=lecturemind

STORAGE_BACKEND=local
STORAGE_LOCAL_DIR=/app/backend/storage_data
```

### Self-host (PostgreSQL + MinIO)
```env
DATABASE_BACKEND=postgres
DATABASE_URL=postgresql+asyncpg://USER:PASS@postgres:5432/lecturemind

STORAGE_BACKEND=s3
OBJECT_STORAGE_BUCKET=lecture-audio
OBJECT_STORAGE_ENDPOINT=http://minio:9000        # omit for AWS
OBJECT_STORAGE_REGION=us-east-1
OBJECT_STORAGE_ACCESS_KEY=minioadmin
OBJECT_STORAGE_SECRET_KEY=minioadmin
```

The backend boots tables idempotently via SQLAlchemy `Base.metadata.create_all`.
For production you should add Alembic migrations on top — they generate
cleanly from `models/orm.py`:

```bash
pip install alembic
alembic init alembic
# edit alembic/env.py: target_metadata = models.orm.Base.metadata
alembic revision --autogenerate -m "init"
alembic upgrade head
```

---

## What stays the same

| Layer | Changes when you swap? |
|-------|------------------------|
| FastAPI routes (`backend/routes/*.py`) | ✅ No |
| Pydantic models (`backend/models/*.py`) | ✅ No |
| AI service (`backend/services/ai_service.py`) | ✅ No |
| Auth + JWT (`backend/core/security.py`, `core/deps.py`) | ✅ No |
| Frontend (`/app/frontend`) | ✅ No |

You only set env vars. No code changes.

---

## Schema

The PostgreSQL schema is defined in `backend/models/orm.py` (SQLAlchemy 2.0
typed mappings). Tables: `users`, `lectures`, `chat_messages`, `quiz_attempts`.
JSON columns hold `materials`, `translations`, and `embedding` to mirror the
nested shape the Mongo backend uses — no information is lost across the swap.

---

## Migrating existing Mongo data

If you've already accumulated data in Mongo and want to move it across:

```bash
mongoexport --uri="$MONGO_URL" --db=lecturemind --collection=users     --out=users.jsonl
mongoexport --uri="$MONGO_URL" --db=lecturemind --collection=lectures  --out=lectures.jsonl
mongoexport --uri="$MONGO_URL" --db=lecturemind --collection=chat_messages --out=chats.jsonl
mongoexport --uri="$MONGO_URL" --db=lecturemind --collection=quiz_attempts --out=attempts.jsonl
```

Then a tiny Python script can load each JSONL line into the SQLAlchemy ORM —
field names are identical, only `_id` (Mongo) → `id` (already mapped) differs.

---

## Rollback

Set `DATABASE_BACKEND=mongo` + `MONGO_URL=...` and restart. The Mongo
implementations are still in the codebase and the dispatcher will pick them
automatically.
