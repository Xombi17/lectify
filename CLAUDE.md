# CLAUDE.md — Secondary Rules (Lectify)

## 1) Core Goal

Deliver a production-grade MVP with queue-driven processing and optimized code.

## 2) Rules

- Write optimized code by default.
- Use queue-driven pipelines for scale.
- No secrets in repo.
- Update docs when services/models change.

## graphify

The project has a full-stack knowledge graph at graphify-out/ covering **2429 nodes, 5903 edges** across both backend (67 Python files) and frontend (79 JSX/JS files).

**PRIMARY search tool** — use `graphify query` instead of `Read`/`Grep` for codebase questions. It returns a scoped subgraph with only relevant nodes, much smaller than full file reads.

| Command | When |
|---------|------|
| `graphify query "<question>"` | General codebase questions — "how does X work", "where is Y defined", "what connects to Z" |
| `graphify path "<A>" "<B>"` | Find relationships between two specific nodes |
| `graphify explain "<concept>"` | Focused deep-dive on one concept |
| Read graphify-out/GRAPH_REPORT.md | Only when query/path/explain don't surface enough context |

After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

## Prisma + Neon

- **Prisma is a dev-only tool** for database management (Studio, schema validation, db pull/push). Runtime queries still go through the Python backend's SQLAlchemy.
- Two connection strings in `.env`: `DATABASE_URL` (pooled via `-pooler` endpoint for app queries) and `DIRECT_URL` (non-pooled for Prisma migrations/Studio).
- Schema lives at [prisma/schema.prisma](prisma/schema.prisma) — keep it in sync with [backend/models/orm.py](backend/models/orm.py) if models change.
- Run `npx prisma studio` to open the database GUI.
- `npx prisma db push` syncs schema to Neon (safe for dev; use proper migrations in prod).

## Status

Living project status, updated after every feature lands.
**Last updated:** 2026-06-08 (after Phase 2 — Teacher Assignment + Student Enrollment)

### Build state vs ROADMAP.md

| Phase | Scope | Status | Notes |
|---|---|---|---|
| **1 — Admin APIs + RBAC (A.2)** | Admin CRUD for 7 hierarchy levels, RBAC, teacher assignment, audit log | **NOT STARTED** | Discuss/plan/execute needed |
| **2 — Teacher Assignment + Enrollment (A.3)** | TeacherAssignment CRUD, StudentEnrollment, Teacher Dashboard | **DONE** | 14 endpoints, full RBAC, 27 tests green |
| **3 — QR per Class + Scan-to-Enroll (A.4)** | QR generation, scan-to-enroll flow, analytics | **NOT STARTED** | Depends on Phase 2 |
| **4 — Admin Dashboard UI (A.5)** | React admin UI for hierarchy, assignments, QR | **NOT STARTED** | Depends on Phase 1 |
| **5 — Queue + Worker (C)** | Redis/RabbitMQ queue, worker pools, retry, DLQ | **NOT STARTED** | Processing currently inline (violates non-negotiable) |
| **6 — Transcription Integration (D ref.)** | Replace mock with Whisper API, confidence scoring, cost tracking | **NOT STARTED** | Depends on Phase 5 |
| **7 — Monitoring + Reliability (F)** | Prometheus, Grafana, SLA tracking, failure alerts | **NOT STARTED** | "95% same-day" SLA unmeasurable today |
| **8 — Auth Polish (I)** | Full RBAC enforcement, session refresh, audit logging | **PARTIAL** | `core/deps.py` has admin/teacher/student guards |
| **B — Recording + upload** | Upload, store, transcribe | **DONE** | Pre-GSD, complete |
| **D — AI pipeline** | Hierarchical chunking, embeddings, summary, notes, quiz, flashcards, exam-tag | **DONE** | `services/ai_service.py` (Gemini 2.5 Flash) |
| **E — Student features** | Dashboard, search, study, bookmarks, chat | **DONE** | Pre-GSD, complete |

### Phase status

| # | Phase | State |
|---|---|---|
| 1 | Admin APIs + RBAC (A.2) | Brief NOT written |
| 2 | Teacher Assignment + Enrollment (A.3) | **DONE** (3 plans, 14 endpoints, 27 tests) |
| 3 | QR generation + scan-to-enroll (A.4) | Brief NOT written |
| 4 | Admin Dashboard UI (A.5) | Brief NOT written |
| 5 | Queue + worker system (C) | Brief NOT written |
| 6 | Production transcription (D ref.) | Brief NOT written |
| 7 | Monitoring + reliability (F) | Brief NOT written |
| 8 | Auth polish (I) | Brief NOT written |

### Graph stats (latest)

- **2429 nodes**, **5900 edges**, **236 communities** (2026-06-08)
- Previous: 919 nodes / 2517 edges — new graph captures enrollment routes

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
