# CLAUDE.md — Secondary Rules (Lectify)

## 1) Core Goal

Deliver a production-grade MVP with queue-driven processing and optimized code.

## 2) Rules

- Write optimized code by default.
- Use queue-driven pipelines for scale.
- No secrets in repo.
- Update docs when services/models change.

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
**Last updated:** 2026-06-08 (after Card 3 — Phase A.3 enrollment endpoints)

### Build state vs PRODUCTION_MVP_PLAN

| Phase | Scope | Status | Notes |
|---|---|---|---|
| **A — Academic hierarchy** | Institution/Year/Branch/Semester/Subject/Division/Class + admin CRUD + RBAC + QR enrollment | **PARTIAL** | Data layer done (Card 1). Phase A.3 enrollment endpoints done (Card 3). Admin APIs + QR pending. |
| **A.3 — Teacher Assignment + Enrollment** | TeacherAssignment CRUD, StudentEnrollment, Teacher Dashboard | **DONE** | 14 endpoints, full RBAC, 27 tests green |
| **B — Recording + upload** | Upload, store, transcribe | **DONE** | `routes/lectures.py` + `services/storage_service.py` |
| **C — Queue + worker** | Redis queue, retry, DLQ, priority | **NOT STARTED** | Processing currently inline (violates non-negotiable) |
| **D — AI pipeline** | Hierarchical chunking, embeddings, summary, notes, quiz, flashcards, exam-tag | **DONE** | `services/ai_service.py` (Gemini 2.5 Flash) |
| **E — Student features** | Dashboard, search, study, bookmarks, chat | **DONE** | `routes/study.py`, `routes/search.py`, `routes/dashboard.py` |
| **F — Monitoring** | Prometheus, /metrics, Grafana, SLA tracking | **NOT STARTED** | "95% lectures same-day" SLA unmeasurable today |
| **H — QR enrollment** | QR per class, scan-to-enroll | **NOT STARTED** | Card 4 |
| **I — Auth polish** | Admin role enforcement, RBAC across all routes | **PARTIAL** | `core/deps.py` has admin/teacher/student guards |

### Card status

| # | Card | State | Tests |
|---|---|---|---|
| 1 | Phase A.1 — Academic hierarchy data layer | **DONE** (Claude Code 494s, $3.36, 14 tests) + 5 more by hand | 14+5 academic + 8 baseline = **27 total** |
| 2 | Phase A.2 — Admin role + hierarchy CRUD + RBAC | Brief NOT written | — |
| 3 | Phase A.3 — TeacherAssignment + StudentEnrollment endpoints | **DONE** (Phase 2 execution: 3 waves, 3 plans, 14 endpoints, 27 tests) | 27 baseline |
| 4 | Phase A.4 — QR generation per class + scan-to-enroll | Brief NOT written | — |
| 5 | Phase A.5 — Admin UI (React) | Brief NOT written | — |
| 6 | Phase C — Queue + worker | Brief NOT written | — |
| 7 | Phase F — Monitoring | Brief NOT written | — |

### Graph cheat-sheet (top communities by size)

- **C0 (139)** — Academic hierarchy (this is the new code)
- **C1 (136)** — Lecture business logic + audio MIME normalization
- **C2 (103)** — FastAPI route handlers
- **C4 (65)** — Search routes + lexical/cosine scoring
- **C5 (64)** — Audio chunker + ffmpeg errors
- **C6 (51)** — Storage service ABC + MinIO impl
- **C8 (33)** — `server.py` entrypoint + lifespan

### Architectural invariants (DO NOT break)

1. **Read before edit.** (per AGENTS.md #4)
2. **Optimize from the start.** No later refactors expected.
3. **Repository pattern (SQL only).** All repos in `repositories/_sql/` with a thin re-export at `repositories/<name>_repository.py`. MongoDB was removed — only PostgreSQL/SQLite is supported.
4. **Pydantic triple pattern.** Every entity has `*Create` / `*DB` / `*Public` variants.
5. **Em-dash bytes (E2 80 94) break HTTP headers** (latin-1 in Starlette). All 27 occurrences in backend are cosmetic; do not introduce new ones in headers.
6. **Test against in-process aiosqlite** when DB is unavailable.

<!-- GSD:project-start source:PROJECT.md -->

## Project

Project not yet initialized. Run /gsd-new-project to set up.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->

## Technology Stack

Technology stack not yet documented. Will populate after codebase mapping or first phase.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
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
