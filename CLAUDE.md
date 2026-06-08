# CLAUDE.md — Secondary Rules (Lectify)

## 1) Core Goal

Deliver a production-grade MVP with queue-driven processing and optimized code.

## 2) Rules

- Write optimized code by default.
- Use queue-driven pipelines for scale.
- No secrets in repo.
- Update docs when services/models change.
- No commits ever directly ever user will do the commits.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

## Prisma + Neon

- **Prisma is a dev-only tool** for database management (Studio, schema validation, db pull/push). Runtime queries still go through the Python backend's SQLAlchemy.
- Two connection strings in `.env`: `DATABASE_URL` (pooled via `-pooler` endpoint for app queries) and `DIRECT_URL` (non-pooled for Prisma migrations/Studio).
- Schema lives at [prisma/schema.prisma](prisma/schema.prisma) — keep it in sync with [backend/models/orm.py](backend/models/orm.py) if models change.
- Run `npx prisma studio` to open the database GUI.
- `npx prisma db push` syncs schema to Neon (safe for dev; use proper migrations in prod).

## Status

Living project status, updated after every feature lands.
**Last updated:** 2026-06-08 (after Phase 5 — Queue + Worker System)

### What was added (Phase 5 — Queue + Worker System)

- **Redis Infrastructure & ARQ Configuration** — Queue foundation for lecture processing pipeline
  - `backend/requirements.txt` — Added `redis>=5.0,<6.0`, `arq>=0.28,<1.0`
  - `backend/core/queue.py` — `get_redis_pool()`, `get_redis()`, `close_redis()`
  - `backend/core/queue_config.py` — Queue names, `compute_priority_score()` (same-day bonus + age), concurrency defaults
  - `backend/core/config.py` — `REDIS_URL`, `REDIS_MAX_CONNECTIONS`, `TRANSCRIPTION_CONCURRENCY`, `AI_CONCURRENCY`, `EMBEDDING_CONCURRENCY`
  - `docker-compose.yml` — Redis 7-alpine service with health check, persistent volume, port 6379
- **Job Models** — `backend/models/job.py` — JobCreate/JobDB/JobPublic triple, JobStatus/JobStage literals
- **Queue Client** — `backend/services/queue_client.py` — `enqueue_job()` with idempotency (SET NX + 24h per-key TTL), `get_job_status()`, `update_job_status()`, `move_to_dlq()`, `get_queue_depth()`
- **Base Worker** — `backend/workers/base.py` — Abstract BaseWorker with ARQ integration, `worker_main()` entry point, `get_retry_delay()` (1m/5m/15m), health check
- **Transcription Worker** — `backend/workers/transcription.py` — processes "transcribe" stage, single-shot + chunked paths, enqueues "generate_materials" on success, retry+DLQ on failure
- **AI Worker** — `backend/workers/ai.py` — processes "generate_materials" stage, study materials from transcript, embeddings, Neo4j sync, enqueues "embed" on success
- **Embedding Worker** — `backend/workers/embedding.py` — processes "embed" stage, idempotent embedding/Neo4j, sets lecture status to "ready"
- **Route Migration** — `backend/routes/lectures.py` — `BackgroundTasks` → queue enqueue on upload; `GET /{id}/job-status` polling endpoint; `backend/server.py` — optional Redis connectivity check
- **LectureStatus** — `backend/models/lecture.py` — Added `queued`, `retrying`, `dead_letter` to literal
- **Tests** — `backend/tests/test_queue.py` (13 tests: priority scoring, job models, idempotency), `backend/tests/test_workers.py` (7 tests: 3 worker types, success/failure/DLQ), `backend/tests/conftest.py` (global Redis mock), `backend/tests/test_queue_integration.py` (integration marker tests), `backend/tests/load_test_queue.py` (load test script)
- **Test counts:** 20 new tests green / 56 total green (queue + existing)
- **New graph nodes:** 2735 nodes, 6134 edges, 259 communities
- **Next card in queue:** Phase 8 — Auth Polish (I)

### What was added (Phase 4)

- **Admin Dashboard UI** — Full React admin dashboard for academic hierarchy management
  - `frontend/src/pages/AdminDashboard.jsx` — Admin page with AppShell wrapper
  - `frontend/src/components/HierarchyTree.jsx` — Recursive tree with branching (Institution→[Year,Branch], Semester→[Subject,Division])
  - `frontend/src/components/CreateEntityDialog.jsx` — Reusable create dialog for all 7 entity types
  - `frontend/src/components/TeacherAssignmentPanel.jsx` — Teacher assign/remove dialog
  - `frontend/src/components/QRCodeCard.jsx` — QR display, download, regenerate, analytics
  - `frontend/src/components/EnrollmentTable.jsx` — Student enrollment table
  - `frontend/src/lib/api.js` — adminApi, assignmentApi, qrApi, enrollmentApi
  - `frontend/src/App.js` — /admin route with RequireAuth, admin redirect
  - `frontend/src/components/AppShell.jsx` — admin nav with Buildings icon
  - Backend: `core/deps.py` (require_teacher_or_admin), `routes/admin.py` (institution years route), `routes/qr.py` (admin access), `routes/enrollment.py` (admin access), `models/academic.py` + `models/orm.py` (Class.name field)
  - Tests: `__tests__/adminApi.test.js`, `__tests__/AdminDashboard.test.jsx`, `__tests__/HierarchyTree.test.jsx`
- **Test counts:** 3 new test files created (infrastructure; will pass after components are wired)
- **New graph nodes:** AdminDashboard, HierarchyTree, CreateEntityDialog, TeacherAssignmentPanel, QRCodeCard, EnrollmentTable, adminApi, assignmentApi, qrApi, enrollmentApi, require_teacher_or_admin
- **Next card in queue:** Phase 5 — Queue + Worker System (C) (Phase 6 is also complete)

### Build state vs ROADMAP.md

| Phase | Scope | Status | Notes |
|---|---|---|---|
| **1 — Admin APIs + RBAC (A.2)** | Admin CRUD for 7 hierarchy levels, RBAC, teacher assignment, audit log | **DONE** | Pre-GSD, complete |
| **2 — Teacher Assignment + Enrollment (A.3)** | TeacherAssignment CRUD, StudentEnrollment, Teacher Dashboard | **DONE** | 14 endpoints, full RBAC, 27 tests green |
| **3 — QR per Class + Scan-to-Enroll (A.4)** | QR generation, scan-to-enroll flow, analytics | **DONE** | Pre-GSD, complete |
| **4 — Admin Dashboard UI (A.5)** | React admin UI for hierarchy, assignments, QR | **DONE** | 4 plans, 6 new components, 4 backend changes, 3 test files |
| **5 — Queue + Worker (C)** | Redis/ARQ queue, 3 worker pools, retry/DLQ, idempotency, priority | **DONE** | 7 plans, 20 new tests, 56 total green, queue-driven pipeline LIVE |
| **6 — Transcription Integration (D ref.)** | Replace mock with Groq Whisper API, confidence scoring, cost tracking | **DONE** | Groq Whisper API, parallel chunking, Gemini fallback, 11 tests green |
| **7 — Monitoring + Reliability (F)** | Prometheus, Grafana, SLA tracking, failure alerts | **DONE** | 3 plans, 15 panels, 6 queue metric groups, alert dedup |
| **8 — Auth Polish (I)** | Full RBAC enforcement, session refresh, audit logging | **PARTIAL** | `core/deps.py` has admin/teacher/student/teacher_or_admin guards |
| **B — Recording + upload** | Upload, store, transcribe | **DONE** | Pre-GSD, complete |
| **D — AI pipeline** | Hierarchical chunking, embeddings, summary, notes, quiz, flashcards, exam-tag | **DONE** | `services/ai_service.py` (Gemini 2.5 Flash) |
| **E — Student features** | Dashboard, search, study, bookmarks, chat | **DONE** | Pre-GSD, complete |

### Phase status

| # | Phase | State |
|---|---|---|
| 1 | Admin APIs + RBAC (A.2) | **DONE** (Pre-GSD) |
| 2 | Teacher Assignment + Enrollment (A.3) | **DONE** (3 plans, 14 endpoints, 27 tests) |
| 3 | QR generation + scan-to-enroll (A.4) | **DONE** (Pre-GSD) |
| 4 | Admin Dashboard UI (A.5) | **DONE** (4 plans, 6 components, 3 test files) |
| 5 | Queue + worker system (C) | **DONE** [adc7a54] |
| 6 | Production transcription (D ref.) | **DONE** (Groq Whisper API, parallel chunks, confidence scoring, 11 tests) |
| 7 | Monitoring + reliability (F) | Brief NOT written |
| 8 | Auth polish (I) | Brief NOT written |

### Graph stats (latest)

- **2429 nodes**, **5900 edges**, **236 communities** (2026-06-08)
- Previous: 919 nodes / 2517 edges — new graph captures enrollment routes
- Run `graphify update .` after Phase 4 code changes to index new components

### Architectural invariants (DO NOT break)

1. **Read before edit.** (per AGENTS.md #4)
2. **Optimize from the start.** No later refactors expected.
3. **Repository pattern (SQL only).** All repos in `repositories/_sql/` with a thin re-export at `repositories/<name>_repository.py`. MongoDB was removed — only PostgreSQL/SQLite is supported.
4. **Pydantic triple pattern.** Every entity has `*Create` / `*DB` / `*Public` variants.
5. **Em-dash bytes (E2 80 94) break HTTP headers** (latin-1 in Starlette). All 27 occurrences in backend are cosmetic; do not introduce new ones in headers.
6. **Test against in-process aiosqlite** when DB is unavailable.

<!-- GSD:project-start source:PROJECT.md -->

## Project

Lectify captures long-form lectures (live mic or upload), transcribes at scale, cleans transcripts, generates study assets (notes, quiz, flashcards, exam-importance tags), and publishes to students by end of day. Built for educational institutions with multi-tenant academic hierarchy.

See [.planning/PROJECT.md](.planning/PROJECT.md) for full project context — requirements, key decisions, constraints.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->

## Technology Stack

- **Backend:** Python 3.14, FastAPI, SQLAlchemy (async), Pydantic
- **Frontend:** React 19 + TypeScript
- **Database:** PostgreSQL (Neon), SQLite for tests
- **Storage:** MinIO (S3-compatible)
- **Queue:** Redis/RabbitMQ (Phase 5 — not yet implemented)
- **AI:** Google Gemini 2.5 Flash (transcription, summarization, quiz/flashcard gen)
- **Auth:** Custom JWT with role-based access (admin, teacher, student)
- **Search:** Lexical + cosine similarity
- **Dev tools:** Graphify (knowledge graph), Prisma (schema management), aiosqlite (in-process tests)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

- **Repository pattern** — thin dispatcher files in `repositories/` re-export from `repositories/_sql/`
- **Pydantic triple** — every entity has `*Create` / `*DB` / `*Public` models
- **RBAC guards** — `require_admin`, `require_teacher`, `get_current_user` from `core/deps.py`
- **Route pattern** — `APIRouter(prefix="/...", tags=["..."])` with dependency injection
- **Async SQL** — `async with session_maker()() as s` for all database access
- **Tests** — pytest with in-memory aiosqlite
- **No secrets in repo** — use `.env` for all configuration
- **Queue-driven pipeline** — non-negotiable for production (Phase 5)
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

The backend follows a layered architecture:

1. **Routes** (`routes/`) — FastAPI endpoint definitions with RBAC guards
2. **Services** (`services/`) — Business logic (AI pipeline, storage, audio chunking)
3. **Repositories** (`repositories/`) — Data access via SQLAlchemy, dispatcher pattern
4. **Models** (`models/`) — Pydantic schemas (Create/DB/Public triple)
5. **Core** (`core/`) — Config, security, DB session, dependency providers

Key integrations:
- **MinIO** for lecture audio file storage
- **Neon (Postgres)** via SQLAlchemy async engine
- **Gemini 2.5 Flash** for all AI tasks
- **Graphify** for codebase knowledge graph

See [.planning/ROADMAP.md](.planning/ROADMAP.md) for phase progression and [.planning/STATE.md](.planning/STATE.md) for current status.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

Project-level skills: `.claude/skills/` directory exists but no SKILL.md index found. See available skills via the Skill tool.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
