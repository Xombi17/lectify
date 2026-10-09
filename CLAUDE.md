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
**Last updated:** 2026-10-09 (frontend redesign on `feat/frontend-redesign`)

### What was added (Frontend redesign — full role-based app surface)

- **Replacement visual system and shell** (`frontend/src/index.css`, `frontend/src/components/AppShell.jsx`, `frontend/tailwind.config.js`): introduced the compact academic index system with Noto Sans, signal-red focus/state, graphite shell rail, responsive mobile navigation, visible focus states, selection/scrollbar styling, and shared panel/data-row primitives.
- **Public and role-based surfaces** (`frontend/src/cra-pages/LandingPage.jsx`, `AuthPage.jsx`, `StudentDashboard.jsx`, `TeacherDashboard.jsx`, `UploadLecturePage.jsx`, `LectureDetailPage.jsx`, `ReviewPage.jsx`, `BookmarksPage.jsx`, `AdminDashboard.jsx`): redesigned the landing, auth, student, teacher, admin, upload, lecture study, review, and saved-item flows while preserving API calls, roles, test IDs, async states, and class-scoped behavior.
- **Flow hardening** (`frontend/app/layout.tsx`, auth/protected layouts, `frontend/src/lib/auth.jsx`, lecture metadata route, `frontend/next.config.mjs`): moved auth context to the root, removed React Router/Next Router mixing from active App Router pages, preserved login redirect targets, fixed invalid JSX wrappers, added PDF export handling, and added a branded favicon.
- **Test and design artifacts** (`PRODUCT.md`, `DESIGN.md`, `.impeccable/`, `frontend/vitest.config.mjs`): recorded product truth and visual direction, configured stable single-worker Vitest execution, and ran the mechanical Impeccable detector with no findings.
- **Test counts (new green / total green):** 0 new frontend tests / 15 frontend tests passing; production build passing; public/protected route smoke checks passing (protected routes correctly redirect to `/login?redirect=...`).
- **New graph nodes:** graphify updated to 3,384 nodes / 8,111 edges / 172 communities; `graphify explain "AppShell"` and `graphify explain "Button"` confirm the redesigned shell and control primitive are indexed.
- **Next card in queue:** Phase 16 verification (human UAT of the live upload-to-ready flow and DLQ redrive), followed by Phase 17.

### What was added (Phase 16 — Presigned Upload & End-to-End Pipeline, Plans 01-03)

- **Backend presigned trio (16-01)** (`backend/routes/lectures.py`, `backend/models/lecture.py`, `backend/tests/test_upload_presign.py`):
  - `POST /lectures/upload-url` with teacher/admin + assignment check, MIME/size validation, server-built `classes/{class_id}/lectures/{lecture_id}/recording/{safe}` keys, `uploading` rows, 900s presigned POST, 501 on LocalStorage.
  - `POST /lectures/{id}/upload-complete` with owner check, head_object verification (409 missing, 413+delete on 0/oversize, 400 MIME mismatch), single transcribe enqueue, idempotent re-call.
  - `GET /lectures/{id}/audio-url` behind `verify_lecture_access` with 900s presigned GET and 501 fallback; `uploading` mapped to queued-like job status.
- **Browser-direct frontend (16-02)** (`frontend/src/lib/api.js`, `frontend/src/lib/lectureStatus.js`, `frontend/src/lib/uploadTransport.js`, `UploadLecturePage.jsx`, `LectureDetailPage.jsx`, `uploadS3.test.js`):
  - `uploadToS3` XHR helper (fields-first FormData, progress), uploadUrl→S3→uploadComplete flow with Verifying state, 501 multipart fallback notice, documented 409/413/CORS error copy.
  - Ready/Processing/Failed pills per UI-SPEC, extended 4s poll to uploading/queued/retrying, presigned audio preferred with blob fallback, dead_letter hides player.
- **DLQ proof + redrive + docs (16-03)** (`backend/workers/transcription.py`, `POST /lectures/{id}/retry`, `infra/cdk/scripts/redrive-dlq.sh`, `infra/cdk/README.md` §10, `docs/SPEC_UPLOAD.md`):
  - Env-gated `FORCE_FAIL_LECTURE_ID` hook (aws/demo/staging only), `receive_count` 5 dead_letter unit proof, admin-only retry with version-bumped job, executable redrive script via `start-message-move-task`, SPEC contract + VER-01/VER-02 operator checklist.
- **Test counts (new green / total green):**
  - Backend: 20 new (test_upload_presign.py) / 213 passed, 3 skipped full suite.
  - Frontend: 9 new (uploadS3.test.js) / 15 passed full suite.
  - CDK: 10 passed (test_data.py + test_secrets_hygiene.py, unchanged).
- **Next card in queue:** Phase 16 pending verify-work (human UAT: live ALB upload-to-ready + DLQ redrive); then Phase 17.

### What was added (Phase 15 — Compute Tier & Delivery, Plans 01-06)

- **Compute Tier & Delivery Infrastructure** (`infra/cdk/lectify_cdk/compute_stack.py`, `compute_iam.py`, `infra/cdk/app.py`, `infra/cdk/Makefile`, `infra/cdk/scripts/vendor-ffmpeg.sh`, `infra/cdk/bootstrap/`):
  - Internet-facing Application Load Balancer with priority 10 `/api/*` routing rule forwarding to API target group (port 8000) and default forwarding to Web target group (port 3000) with independent shallow `/healthz` health checks.
  - Hardened EC2 Launch Templates for Web and Worker tiers enforcing IMDSv2 (`require_imdsv2=True`, `http_put_response_hop_limit=1`), 20GB encrypted gp3 root EBS volumes, public IPs for direct outbound egress, and Session Manager IAM access with no SSH key pairs.
  - AutoScalingGroups with Web ASG (min 1, max 2, desired 1, 300s ELB grace period) attached to both target groups and Worker ASG (min 1, max 3 hard-cap `WORKER_MAX`, desired 1, EC2 health check) completely decoupled from the ALB.
  - Automated AL2023 instance bootstrap scripts (`common.sh`, `api.sh`, `worker.sh`) and hardened systemd service units (`lectify-api.service`, `lectify-web.service`, `lectify-worker.service`) with memory caps, user isolation (`lectify:lectify`), and 120s SIGTERM graceful drain timeouts.
  - Vendored static ffmpeg script (`scripts/vendor-ffmpeg.sh`) with SHA-256 hash pinning (`bootstrap/ffmpeg.sha256`) and unattended bootstrap verification.
  - App.py fail-fast synthesis validation preventing deployment of unbuilt artifacts, with `LECTIFY_SKIP_COMPUTE_ARTIFACT_CHECK=1` escape hatch for destroy/placeholder flows.
- **Backend Infrastructure Seams** (`backend/server.py`, `backend/core/config.py`, `backend/core/db_secret.py`, `backend/workers/__main__.py`):
  - Unauthenticated shallow `/healthz` endpoint returning `{"status": "ok"}` without database queries.
  - `DB_AUTO_CREATE` setting gating automatic table creation during app lifespan.
  - AWS Secrets Manager database credentials overlay composing asyncpg connection URLs.
  - `python -m workers all` supervisor loop running all three pipeline workers concurrently with graceful signal propagation.
- **RDS Schema Bootstrap & Deterministic Demo Seeder** (`backend/scripts/bootstrap_db.py`, `backend/scripts/seed_demo.py`):
  - Out-of-band PostgreSQL schema bootstrap under 64-bit advisory lock `5504283845945100081`.
  - Deterministic idempotent demo seeder creating complete academic hierarchy and demo accounts (admin, teacher, student) using `uuid5` stable identifiers and mandatory interactive/env password prompts.
- **Frontend Relative API Client & Web Healthz** (`frontend/src/lib/api.js`, `frontend/next.config.mjs`, `frontend/app/healthz/route.ts`, `frontend/middleware.ts`, `infra/cdk/scripts/build-web.sh`):
  - Same-origin relative `/api` base URL eliminating CORS preflights in production with Next.js dev rewrites to localhost:8000.
  - Unauthenticated `/healthz` Next.js route handler returning `{"status": "ok"}` with middleware bypass.
  - Off-instance Next.js standalone bundle builder packaging standalone output to `infra/cdk/build/web/`.
- **Test suite counts:**
  - CDK: 49 passed (12 new unit & integration tests across `test_app.py`, `test_compute.py`, `test_compute_iam.py`, `test_secrets_hygiene.py`).
  - Backend: 193 passed, 3 skipped (8 new tests across `test_healthz.py`, `test_db_secret.py`, `test_worker_all.py`, `test_bootstrap_db.py`, `test_seed_demo.py`).
  - Frontend: 6 passed (isolated unit tests in `src/lib/__tests__/`).
- **Next card in queue:** Phase 15 complete; ready for Phase verification and milestone advance to Phase 16.

### What was added (Phase 13.1 — Class-Scoped Access & Timetable)

- **Plan 13.1-01 (Database Schema & Model Foundations)** — Added `class_id` and `timetable_slot_id` foreign keys with indexes to `LectureORM` (`backend/models/orm.py`) and Prisma `model Lecture` (`prisma/schema.prisma`); defined `TimetableSlotORM` and `model TimetableSlot`; created `backend/models/timetable.py` Pydantic models; updated `test_schema_parity.py` with 4/4 passing tests.
- **Plan 13.1-02 (Lecture Upload & Teacher Assignment Verification)** — Enforced mandatory `class_id` on `POST /api/lectures` upload, validated active teacher assignments with HTTP 403 rejection (and admin bypass), hydrated and persisted `class_id` in `LectureRepository`, and added `backend/tests/test_lectures.py` (4/4 tests green).
- **Plan 13.1-05 (Timetable Slot CRUD, Overlap Detection & Access Control)** — Built `TimetableRepository` with `find_overlap` interval disjunction, implemented `/api/timetable` endpoints rejecting conflicts with HTTP 409, mounted in `backend/server.py`, and added `backend/tests/test_timetable.py` (4/4 tests green).
- **Plan 13.1-03 (Student Fail-Closed Direct Item Retrieval)** — Implemented `verify_lecture_access(lecture_id, user)` in `backend/core/deps.py` raising fail-closed HTTP 404 for un-enrolled students and unassigned teachers to prevent resource enumeration. Refactored lecture detail, audio streaming, PDF export, bookmarking, reviews, chat/doubts, and quiz submission endpoints. Added `backend/tests/test_lecture_access.py` (6/6 tests green).
- **Plan 13.1-04 (Scoped List & Search Filtering)** — Extended `list_published` and `list_published_embeddings` in `LectureRepository` to accept `class_ids`, added `get_user_accessible_class_ids` in `backend/core/deps.py`, scoped `GET /api/lectures/published` and `GET /api/search` with zero cross-class leakage, and added `backend/tests/test_scoped_search.py` (3/3 tests green).
- **Plan 13.1-06 (Frontend Integration: Class Picker & Timetable View)** — Added `timetableApi` and `academicApi` in `frontend/src/lib/api.js`, added `/teacher-assignments/mine` route alias, added assigned class picker with empty-state warning and slot selector in `UploadLecturePage.jsx`, and integrated Weekly Timetable widgets into `StudentDashboard.jsx` and `TeacherDashboard.jsx`.
- **Plan 13.1-07 (Realistic College Seed Fixture & Cross-Class Isolation Suite)** — Created realistic college seed fixture (`backend/fixtures/college_seed.py`) modeling 4 years × 4 engineering branches, divisions, subjects, classes, users, slots, and lectures. Built 9 comprehensive cross-class isolation tests (`backend/tests/test_cross_class_isolation.py`) proving zero information leakage across lecture details, streaming, notes, PDF, bookmarks, flashcards, quiz attempts, chat/doubts, search, timetable, and teacher upload. All 9 tests green (30/30 total Phase 13.1 tests green).
- **Next card in queue:** Phase 13.1 complete; ready for Phase verification and milestone advance to Phase 14 (`Admin Academic Hierarchy & Dashboard`).

### What was added (Phase 13 — Code Seams, Plans 01-13)

- **SQL Queue Backend (Plans 13-01 to 13-05)** — Created `core/queue_backend.py`, `repositories/job_repository.py`, `job_chunk_repository.py`, `workers/base.py`, `services/notification_service.py`, `core/ssm_overlay.py` to completely replace Redis and ARQ. Workers now run as pure Python processes on `asyncio` loops polling SQS/SQLite.
- **Security & Infrastructure** — Implemented SSM overlay for secure runtime config, instance profile S3 auth (removing static keys), and added robust HTTP rate limiting for AI API calls.
- **Cleanup (Plan 13-09)** — Purged `redis` and `arq` dependencies from the codebase.
- **Gap closure (Plans 13-10 to 13-13)**:
  - Retry-After-carrying `ProviderRateLimited` (`ai_service` + Groq transcription).
  - Crash-safe enqueue-before-complete ordering with `enqueue_job(..., resend_if_queued=...)`.
  - Bounded SIGTERM drain (`DRAIN_TIMEOUT_SECONDS`, default 90) with visibility-0 release.
  - `backend/workers/__main__.py` entrypoint (created in 13-13; mapping CLI stage args to worker classes and exit 2 on invalid stages).
  - Workers poll stage-keyed queues (`transcribe`, `generate_materials`, `embed`) matching what `enqueue_job` sends to.
  - `ENV` now defaults to `production` (set `ENV=dev` for local runs; `DEV_ENVS = dev/test/local`).
  - Live-HTTP test files ignored at collection unless `REACT_APP_BACKEND_URL` is set.
- **Test counts:** 142 passed, 3 skipped in backend offline suite (all tests green on memory backend).
- **New graph nodes:** (Graph update skipped; graphify not installed)
- **Next card in queue:** Phase 13.1 — Class-Scoped Access & Timetable

### What was added (Phase 12 — Account Gate, Budget, CDK Skeleton & Network)

- **CDK Infrastructure Foundation** — Self-contained AWS CDK app in `infra/cdk/` (`app.py`, `budget_stack.py`, `network_stack.py`) with zero-NAT VPC, 4 subnets, S3 gateway endpoint, 4 security groups, and cost budget alarms ($50 default with 4 threshold alerts excluding credits).
- **Automation & Operator Tooling** — `infra/cdk/Makefile` with one-command deploy/destroy/preflight/orphans targets, `scripts/preflight.sh` with automated account/region/CDK/bootstrap verification.
- **Live AWS Verification** — Preflight passed, CDK bootstrap created `CDKToolkit` in `ap-southeast-2`, `BudgetStack` deployed before `NetworkStack`, teardown verified with zero orphaned resources.
- **Test counts:** 19/19 new CDK tests green (`test_budget.py`, `test_network.py`, `test_app.py`).
- **New graph nodes:** `infra/cdk/app.py`, `infra/cdk/lectify_cdk/budget_stack.py`, `infra/cdk/lectify_cdk/network_stack.py`.
- **Next card in queue:** Phase 13 — Code Seams & Phase 14 — Data & Messaging Infrastructure

### What was added (Phase 11 — Microservices Migration)

- **API Gateway Routing Proxy** — `gateway/nginx.conf` routing `/api/auth`, `/api/admin`, `/api/enrollment`, `/api/qr`, `/api/study`, `/api/chat`, `/api/lectures`, and `/api/search` to their respective microservices.
- **Microservice Routing Switches** — Configured dynamic router mounting based on the `SERVICE_NAME` setting inside `backend/server.py` and `backend/core/config.py` to run the same backend codebase as independent services.
- **Standalone Worker Pools** — Docker Compose configured with standalone worker processes (`worker-transcription`, `worker-ai`, `worker-embedding`) to run decoupled processing pools.
- **Inter-service Auth Client** — Refactored token validation in `backend/core/deps.py` to make internal API calls to `auth-service` when running the interaction service.
- **Integration Tests** — Added `backend/tests/test_gateway_auth.py` to verify API Gateway routing, token exchange, and validation across the proxy.
- **Test environment fix** — Modified `backend/core/config.py` to detect `pytest` and prevent dotenv overriding test DB connection.
- **Test counts:** 98 passed, 19/19 passing in `test_academic.py`, 6/6 passing in `test_audit.py`.
- **New graph nodes:** `test_gateway_auth.py`.
- **Next card in queue:** Phase 9 — AI Study Expansion (G)

### What was added (Phase 8 — Auth Polish)

- **RBAC Enforcement** — `backend/core/deps.py`: `require_student()`, `require_role()` factory, `can_access_lecture()`, `get_admin_user()`, blacklist check in `get_current_user()`, `extract_token_data()` with expired-token fallback
- **Token Session Management** — JTI (UUID) in all JWT payloads, `models/orm.py` (`TokenBlacklistORM`), `models/user.py` (`TokenBlacklistDB`), `repositories/token_repository.py` (`blacklist_token`, `is_blacklisted`, `clean_expired`)
- **Logout & Refresh** — `routes/auth.py`: `POST /auth/logout` (204, blacklists token), `POST /auth/refresh` (blacklists old, issues new)
- **Token Cleanup** — `server.py` lifespan: periodic background task (every 6h) removing expired blacklist entries
- **Frontend Session** — `frontend/src/lib/auth.jsx`: backend logout call; `frontend/src/lib/api.js`: queued 401→refresh interceptor with queued retry
- **Audit Logging** — `core/deps.py`: `log_audit()` function + 8 action constants; `models/academic.py`: expanded `AuditLogCreate` regex
- **Admin CRUD Audited** — `routes/admin.py`: all 7 hierarchy entity create/update/delete endpoints wired, old `_log_action()` removed
- **Lecture Audited** — `routes/lectures.py`: publish/unpublish/delete now log AUDIT_PUBLISH, AUDIT_UNPUBLISH, AUDIT_DELETE
- **QR Audited** — `routes/qr.py`: QR generation logs AUDIT_GENERATE_QR
- **Audit Tests** — `tests/test_audit.py`: 6 unit tests for model validation + action types
- **Test counts:** 28 pass (6 new audit + 22 existing), 4 pre-existing Redis-dependent worker tests

### What was added (Phase 7 — Monitoring + Reliability)

- **Prometheus Metrics** — 12 custom metrics exposed at /metrics via prometheus-fastapi-instrumentator
  - `backend/services/metrics_service.py` — Counter/Gauge/Histogram for lectures, queue, AI pipeline, processing
  - `backend/core/config.py` — `PROMETHEUS_ENABLED`, `PROMETHEUS_METRICS_PATH`, `SLA_TARGET_PERCENT`, `SLACK_WEBHOOK_URL`, alert thresholds, `DAILY_SUMMARY_TIME`
  - `backend/server.py` — Instrumentator in lifespan with `should_group_status_codes=True`, enhanced /health with DB/Storage/Redis probes
  - `docker-compose.yml` — Prometheus service (port 9090) + Grafana service (port 3000) with provisioning volumes
- **SLA Tracking** — `backend/services/monitoring_service.py` — `compute_daily_sla()`, `compute_rolling_sla()`, `generate_daily_summary()`, Slack Block Kit formatting
- **Alert Manager** — `backend/services/alert_service.py` — `AlertManager` with 5-min dedup cooldown, `check_queue_depth()`, `check_dlq_growth()`, `check_sla_breach()`, Slack webhook integration
- **Background Monitoring Loop** — `backend/server.py` lifespan — periodic loop (every 5 min) for SLA, alerts, daily summary dispatch
- **Metric Instrumentation** — All workers (`ai.py`, `embedding.py`, `transcription.py`): `queue_retry_count` on exceptions; `queue_client.py`: queue depth/failures tracking; `lecture_service.py`: `ai_generation_duration` timing, `record_lecture_processed`
- **Grafana Dashboard** — `infra/grafana/dashboards/lectify-overview.json` — 12 panels across API (Request Rate, Latency p95, Error 5xx), Pipeline (Queue Depth, Processing Duration, Failure Rate, DLQ Size), SLA (Same-day %, Processed/24h, Time Trend), and System (AI Gen Latency, Token Consumption)
- **Infrastructure Config** — `infra/prometheus/prometheus.yml` — scrape target `backend:8001`; `infra/grafana/datasources/prometheus.yml` — uid-based datasource; `infra/grafana/dashboards/dashboard.yml` — provisioning config
- **Test counts:** 16/20 pass (same baseline — 4 worker tests need Redis)

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
| **8 — Auth Polish (I)** | Full RBAC enforcement, session refresh, audit logging | **DONE** | require_student, require_role, can_access_lecture, token blacklist, logout/refresh, audit logging wired to 25+ endpoints |
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
| 7 | Monitoring + reliability (F) | **DONE** (12 custom metrics, 12-panel Grafana dashboard, SLA tracking, Slack alerts, background monitoring loop) |
| 8 | Auth polish (I) | **DONE** (3 plans: RBAC, session management, audit logging — 28 tests pass) |

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
- **IaC:** AWS CDK (Python 3.12 venv) in infra/cdk: BudgetStack + NetworkStack (Phase 12); see infra/cdk/README.md
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

<!-- BEGIN AWS Agent Toolkit rules -->
# AWS Guidance for the new AWS experience

This user has signed up for the new AWS experience. This experience lets you sign into AWS using a social provider and requires the following additional context.

Where this guidance conflicts with the project's own instructions, the project's instructions take precedence.

## Context

### Terminology:

- Say "project" instead of "account" — a project contains an AWS account and settings for sharing with other collaborators
- Say "team member" instead of "IAM user" — users are invited by email, not created or federated in IAM
- Say "AWS Settings" when referring to management tasks at [settings.aws.com](https://settings.aws.com/) (project management, billing, team members, spend limits). Users view their actual AWS resources in the AWS Management Console.
- Say "selected Region" when referring to the user's Region — not "home Region"
- The user has a managed IAM experience. This includes a managed service control policies (SCP) and resource control policies (RCP) that govern the use of AWS. They will still need to use IAM to create policies to let services work with each other. If there are questions about the SCPs or RCPs, go to the documentation at https://docs.aws.amazon.com/accounts/latest/reference/scps-and-rcps-for-projects.html

### Constraints:

- All projects share a single AWS Region determined by the user's contact address. Resources cannot be created in other Regions
- When developing:
  - MUST create all Regional resources in the project's assigned Region
  - You CAN create AWS WAF and Cloudwatch Logs resources in us-east-1 when there are global resources (like a global WAF instance) that require a connection to dependencies in us-east-1. You should not use these for any other reason, because resources in the selected Region will provide lower cost (due to no cross-Region traffic), increased availability (due to no cross-Region traffic), and easier manageability (due to not needing to look in another Region). When you need to do an inventory of resources, you need to look in both the selected Region and us-east-1 for Cloudwatch Logs or WAF resources.
  - MUST NOT attempt to create Lambda, API Gateway, or other Regional resources in any other Region
  - MUST direct users to confirm their Region in AWS Settings > View all projects > Overview > Additional Info > Region. If the user cannot confirm their Region, check in ~/.aws/config
  - MUST NOT use Lambda@Edge — excluded from both Lambda and CloudFront
  - MUST NOT use CloudFormation StackSets — no multi-account or multi-Region deployments
  - MUST NOT attempt cross-Region actions — no cross-Region replication for DynamoDB/S3/RDS, no multi-Region KMS keys
  - MUST NOT use Route 53 cross-Region routing — geolocation, latency-based, and failover routing policies are not available
  - CloudFront is a global service and its actions ARE allowed in `us-east-1`. A user can create a CloudFront distribution pointing to their project-region Lambda function URL or API Gateway. However, Lambda and API Gateway themselves MUST NOT be created in `us-east-1` — they must be in the project Region.
  - Reduced availability in `eu-north-1` specifically: Amazon Rekognition, Amazon Textract, Amazon Personalize, AWS App Runner are not available in that Region.
- IAM permissions for human access are managed by AWS. Don't assign roles to team members unless absolutely necessary
- The user may have a spend limit if they are on the paid plan. The limit that pauses their project if it's exceeded. If resources suddenly become inaccessible, ask if they have a spend limit configured. Only project owners can modify a spend limit.
- When developing:
  - MUST ask about spend limit status if the user reports sudden "Access Denied" errors on operations that previously worked
  - MUST direct users to check spend status in AWS Settings > Billing
  - MUST check if a user has upgraded their account to the paid plan
  - MUST ask the user if they want to clean up the successfully created resources or keep them to reduce cost
- The user sets up billing, creates spend limits, and retrieves and pays invoices in AWS Settings. The user creates budgets and optimizes their costs in the AWS Billing and Cost Management console
- Not all AWS services are available. If a service isn't working, do the following:
  1. Run the command `aws freetier get-account-plan-state`
  2. If accountPlanType": "FREE", check the [Free Tier supported services list](https://docs.aws.amazon.com/accounts/latest/reference/supported-services-sign-up-new.html#supported-services-free-tier) next,
  3. If accountPlanType": "PAID", check the [Paid Tier supported services list](https://docs.aws.amazon.com/accounts/latest/reference/supported-services-sign-up-new.html#supported-services-paid-plan).
  4. If neither list shows the service, check the [Not supported for this experience list](https://docs.aws.amazon.com/accounts/latest/reference/supported-services-sign-up-new.html#unsupported-services). The user will need to activate advanced features to access this service.
- Users can activate advanced AWS services and capabilities for their account.
- Before starting a task, check whether a relevant AWS skill is available. Load the skill with retrieve_skill and prefer its guidance over general knowledge.

### Help level

- help_level (required): LOW, MEDIUM, or HIGH. While a user is building, you MUST ask the user: "How much guidance would you like from me? Low (I only flag security risks), medium (I ask a couple of clarifying questions if something seems off), or high (I explain what I'm doing, suggest alternatives, and flag best practices)."

You CAN update this rule file to save a user's help_level.

Constraints for each level:

**LOW:**

- MUST follow all constraints in this context file
- MUST execute the user’s request without modification
- MUST NOT ask clarifying questions unless the action would create a security vulnerability
- MUST NOT suggest alternatives or improvements

**MEDIUM:**

- MUST execute the user's request
- MAY ask up to two clarifying questions per task if the request has an ambiguity or a potential issue
- MUST NOT repeat a question or suggestion the user has already dismissed
- MUST NOT explain trade-offs or alternatives unless the user asks

**HIGH:**

- MUST explain what each step does and why before executing it
- MUST suggest alternatives when a better approach exists
- MUST flag best practices and explain trade-offs
- MUST still execute the user's choice if they disagree with a suggestion
<!-- END AWS Agent Toolkit rules -->
