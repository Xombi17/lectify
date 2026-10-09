# Application Status — Lectify

**Last updated:** 2026-10-09

CLAUDE.md Status is the source of truth; this table is a summary.

## Build State vs PRODUCTION_MVP_PLAN

| Phase | Scope | Status | Notes |
|-------|-------|--------|-------|
| **A — Academic hierarchy** | Institution/Year/Branch/Semester/Subject/Division/Class + admin CRUD + RBAC + QR enrollment | **DONE** | Admin APIs + UI, assignments, QR enrollment (Phases 1-4). |
| **B — Recording + upload** | Upload, store, transcribe | **DONE** | `routes/lectures.py` + `services/storage_service.py` |
| **C — Queue + worker** | SQS queues, retry, DLQ, idempotency | **DONE** | SQS workers, Phases 13/14; DLQ redrive in Phase 16 |
| **D — AI pipeline** | Hierarchical chunking, embeddings, summary, notes, quiz, flashcards, exam-tag | **DONE** | `services/ai_service.py` (Gemini 3.7 Flash) |
| **E — Student features** | Dashboard, search, study, bookmarks, chat | **DONE** | `routes/study.py`, `routes/search.py`, `routes/dashboard.py` |
| **F — Monitoring** | Prometheus, CloudWatch alarms, dashboard | **DONE** | Prometheus Phase 7; CloudWatch alarms + dashboard Phase 17 |
| **H — QR enrollment** | QR per class, scan-to-enroll | **DONE** | Phase 3 |
| **I — Auth polish** | Admin role enforcement, RBAC across all routes | **PARTIAL** | `core/deps.py` has admin/teacher/student guards |

## Card Status

| # | Card | State | Tests |
|---|------|-------|-------|
| 1 | Phase A.1 — Academic hierarchy data layer | **DONE** | 27 total |
| 2 | Phase A.2 — Admin role + hierarchy CRUD + RBAC | Brief on disk; needs fix | — |
| 3 | Phase A.3 — TeacherAssignment + StudentEnrollment endpoints | Brief NOT written | — |
| 4 | Phase A.4 — QR generation per class + scan-to-enroll | Brief NOT written | — |
| 5 | Phase A.5 — Admin UI (React) | Brief NOT written | — |
| 6 | Phase C — Queue + worker | Brief NOT written | — |
| 7 | Phase F — Monitoring | Brief NOT written | — |

## Key Architectural Notes

- **God nodes**: `LectureRepository` (119 edges), `StudyMaterials` (75), `LectureDB` (74) — core abstractions
- **Cross-cutting concerns**: `session_maker()` connects 5 communities; `get_storage()` connects 4
- **Top communities**: Academic hierarchy (C0, 139 nodes), Lecture business logic (C1, 136), FastAPI routes (C2, 103)

## Immediate Blockers

None blocking. Phase 18 live runs (scale-out demo, load test) are pending; see CLAUDE.md Status.

Queue, admin features and observability are in place; remaining work is live verification.