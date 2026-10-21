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
**Last updated:** 2026-10-21 (Phase 20 Field Notebook redesign; human UAT pending; VER-01 live run still open)

### SESSION HANDOFF 2026-10-22 (read this first in a new session)

**Live stack (ap-southeast-2, profile `lectify`, URL `http://comput-alb16-wndvevxfg69z-1334501939.ap-southeast-2.elb.amazonaws.com`):** all stacks deployed; web+worker ASGs running; RDS up. CLI default region is us-east-1 (SCP-denied): always `export AWS_PROFILE=lectify AWS_REGION=ap-southeast-2 AWS_DEFAULT_REGION=ap-southeast-2`. Deploy needs `-c budget_email=varadaj47@gmail.com -c ready_emails=varadaj47@gmail.com -c app_origin=<ALB URL in LOWERCASE>` (S3 CORS matches case-sensitively; mixed-case broke uploads once). Pause/resume: `make aws-pause|aws-resume|aws-status` in infra/cdk. Ship = `make build-web` + `npx --no-install cdk deploy --all ...` + `aws autoscaling start-instance-refresh` on both ASGs (`ComputeStack-WebAsgASGEE4061A2-2CcStOQTw3tx`, `ComputeStack-WorkerAsgASGC59A845D-QR910JqZwEER`, MinHealthy 100 / MaxHealthy 200, warmup 300). Instances only pick up new code/SSM keys after a refresh. RDS is private: run scripts via `aws ssm send-command` (AWS-RunShellScript) on an instance as user `lectify` with `source /etc/lectify/app.env`, `PYTHONPATH=/opt/lectify/backend`, `/opt/lectify/venv/bin/python`. Never print secrets; read keys from `backend/.env`.

**In flight when this session ended:** a backend-only deploy that DID complete its CDK step (ComputeStack updated 18:46 UTC, OpenRouter key in SSM); the instance refresh on both ASGs had just started (0%) and needs about 10-15 min. VERIFY it finished: `aws autoscaling describe-instance-refreshes`, then worker log (`aws logs filter-log-events --log-group-name /lectify/worker`) should show `AI provider chain: ['groq','openrouter','naga','gemini','nim']`. The lecture `crypto_intro_short` (id starts `e774d7ae`) was stuck at "Generating study materials" because Naga 503 / NIM 404 / Gemini 503; after the refresh press Retry processing (owner teacher or admin) and confirm it reaches Ready.

**AI providers (backend/services/ai_service.py, core/config.py):** STT chain deepgram -> naga -> gemini (Deepgram verified live: 2-7 s). LLM chain `LLM_PROVIDERS` default `groq,openrouter,naga,radox,gemini,nim` with **round robin** (`LLM_ROUND_ROBIN=1`, `FailoverAIProvider(rotate=True)`): each call starts at the next provider then fails over. Providers without keys are skipped. Verified live with the real `generate_study_materials`: Groq `openai/gpt-oss-120b` (5.8 s; the old llama-3.3 id no longer exists), OpenRouter `minimax/minimax-m3.1-flash:free` (19 s). **NIM is broken** (NVIDIA function id 404; also hits `nvidia/nemotron-3-super-120b-a12b:free` on OpenRouter): kept last. **Radox** (`https://radoxai.com/v1`, only `/v1` works) accepts the key but every model returns 402 insufficient_quota: needs credit, then set `RADOX_CHAT_MODEL` (ids from `GET /v1/models`). Naga free tier is flaky (503s). SSM now holds JWT_SECRET, GROQ, GEMINI, DEEPGRAM, NAGA_AI, NIM, OPENROUTER keys (RADOX key is only in local .env).

**Uncommitted work in the tree (nothing committed; user commits):** (1) my UX-audit fixes, see the "UX audit fixes" section below (backend 338 tests, plus frontend tests); (2) a second Claude session `cdk-7a` is doing the Phase 20 frontend redesign in the same tree (custom icon set `src/components/icons.jsx`, editorial warm palette, full page audit). Coordinate through ListAgents/SendMessage; do not edit `frontend/` or redeploy while it is working unless the user says so. The deployed web bundle is from the 18:00 UTC build (pre-icons), not the latest redesign; shipping the redesign needs `make build-web` after cdk-7a finishes and the user has looked at it in a browser (nobody has yet).

**Open items:** Phase 20 visual UAT; VER-01 live run with SNS email (subscription is confirmed); NIM model fix or removal; Radox credit; legacy lectures with `class_id IS NULL` visible to all students; capacity (DB pool, login storm); no emailed password reset (admin reset links instead); react-query not adopted. Gotchas: frontend vitest needs `--pool=threads` on Node 24; a GateGuard hook demands "importers / affected API / data / user instruction" facts before the first edit of each file (state them, then retry the edit).

### What was added (Phase 20 - Field Notebook frontend redesign)

- **Tokens and themes** (`frontend/src/index.css`, `tailwind.config.js`, `app/providers.tsx`, `ThemeToggle.jsx`): Day desk / Night desk via `data-theme`, next-themes with a pre-paint script (`lectify-theme`, `suppressHydrationWarning` in `app/layout.tsx`); lime removed; tokens and AA contrast checked in `tokens.test.js`.
- **Fonts** (`app/layout.tsx`): `next/font/google` Bricolage Grotesque, Newsreader, Caveat (400/700) and Geist Mono, self-hosted at build; no third-party CDN references.
- **Primitives**: Button variants paper/pen/quiet with legacy aliases, restyled ui fields and read-tabs, `StatusStamp` ("Ready / Writing up / Retry processing"), `ConfirmDialog`, `PenPlayer`.
- **Surfaces restyled**: landing, auth, student dashboard/review/bookmarks, lecture detail, teacher dashboard/upload, admin on a plain page (no holes or tape). `lectureApi.retry` client added for the admin retry action.
- **Guards**: `tokens`, `designGuards` (banned fonts/CDNs plus a surface-wide gate: weights 400/700 only, 4 sizes, no palette classes, no duotone, no standalone `text-accent`, no `dark:`, framer-motion requires `useReducedMotion`), `testids` baseline, `modules`.
- **Concurrent UX-audit changes** (separate session, noted as facts): new ForgotPassword, ResetPassword, Enroll, Account, AdminUsers pages, `AuthCard`, `PasswordInput`, `not-found`/`error`/`global-error`, Account link and Users nav in `AppShell`, filters and load-more in `StudentDashboard`. Their old Tailwind sizes and weights were swept into the Field Notebook tokens (logic and testids unchanged).
- **Test counts:** frontend vitest 18 files, 283 passed; `next build` passes. Backend untouched.
- **Still open:** human visual UAT (375px and 1280px, day and night, reduced motion, admin without holes or tape); VER-01 live run.
- **Next card in queue:** Phase 20 UAT sign-off, then redeploy ComputeStack and run VER-01.

### What was added (UX audit fixes: accounts, enrollment, QR, paging)

- **Accounts** (`routes/auth.py`, `routes/admin.py`, `core/security.py`): public signup creates **students only** (teacher/admin accounts come from `POST /admin/users`); `PATCH /auth/me`, `POST /auth/change-password` (revokes the old token, returns a new one), `POST /auth/reset-password`; admin-issued one-time reset link `POST /admin/users/{id}/reset-link` (30 min, dies when the password changes, no storage). Reset/enrollment tokens carry a `type` claim and `decode_access_token` rejects any typed token, so they can never authenticate a session. Password minimum is 8. No email service exists for end users, so there is no emailed forgot-password and no email verification.
- **QR + enrollment** (`routes/qr.py`): the QR SVG key moved to `classes/{class_id}/qr/{id}.svg` (the old `qr-codes/` prefix was outside the API role's `classes/*` write scope, so generation failed on AWS); the enrollment URL uses `APP_URL` if set, else the browser's `Origin` (default is now empty, never localhost); only students can enroll; the preview call returns the class name; regenerate now checks the class exists and the teacher is assigned. Frontend `/enroll?token=` page handles signed-out, wrong role, already enrolled and expired QR.
- **Retry:** `POST /lectures/{id}/retry` allows the owning teacher or an admin (UI shows the button to both).
- **Paging:** `/lectures/published` and `/lectures/mine` accept `limit` (default 100, max 200) and `offset`; repositories default to unbounded so existing callers are unchanged.
- **Frontend:** `/forgot-password`, `/reset-password`, `/account`, `/admin/users`, 404 + error boundaries, session-expired banner with return-to path, show/hide password, student filters/sort/New marker/resume/Load more, teacher search/Load more, audio resume position (`src/lib/recentLectures.js`, per-user localStorage), hierarchy list search (>8 items) and a root Classes list, per-page tab titles.
- **Test counts:** backend 332 passed, 3 skipped; frontend 283 passed.
- **Not deployed yet:** visual UAT pending. To ship: `make build-web`, `cdk deploy --all` with the **lowercase** ALB origin, instance refresh on both ASGs, then `make put-secrets` (Deepgram/Naga/NIM keys are missing from SSM).
- **Not done:** react-query adoption, email verification / emailed password reset, DB-pool and login-throughput tuning (Phase 18 capacity gap).

### What was added (v1.0 milestone closure)

- **Verification:** `13.1`, `15`, `19` now have `*-VERIFICATION.md` (all `passed`); Phase 19 `19-SECURITY.md` has `threats_open: 0` (24/24). `v1.0-MILESTONE-AUDIT.md` records the audit; `REQUIREMENTS.md` ticked except **VER-01** (live real-provider upload-to-ready + SNS email on the deployed stack).
- **IAM fix** (`infra/cdk/lectify_cdk/compute_iam.py`): API role gains `s3:DeleteObject` (classes/*) and `s3:ListBucket` (classes/* prefix) so missing-object `upload-complete` returns 409 (not 500) and failed/deleted uploads stop orphaning S3 objects. **Takes effect only after a ComputeStack redeploy.**
- **Class scoping:** `/flashcards/due`, `/bookmarks/me`, `/analytics/me` filter by the student's enrolled classes (`core/deps.py` `student_class_scope`/`lecture_in_scope`); both upload paths reject a `timetable_slot_id` that is missing or belongs to another class (400).
- **Re-embed:** `python -m scripts.reembed_lectures [--dry-run] [--limit N]` re-embeds existing lectures after the `gemini-embedding-001` switch.
- **Test hygiene:** CDK fail-fast tests use `LECTIFY_ARTIFACT_ROOT` + temp dirs (they used to mutate real build/vendor dirs); `test_queue` priority test no longer depends on time of day. Frontend vitest needs `--pool=threads` on Node 24.
- **Test counts:** backend 309 passed, 3 skipped; CDK 65 passed; frontend 16 passed.
- **Still open:** VER-01 + Phase 16 human checks; capacity goal (20 vs ~2,000 users, DB pool first); published lectures with `class_id IS NULL` are visible to all students (backfill/unpublish before prod); per-process provider cooldowns.
- **Next card in queue:** redeploy ComputeStack, run one live lecture (VER-01), then `/gsd-complete-milestone 1.0`.

### What was added (Phase 19 UAT gap fixes)

- **Embedding 404:** `GeminiProvider.embed` now uses `GEMINI_EMBED_MODEL` (default `gemini-embedding-001`) with `output_dimensionality=768` (live call verified, 768-dim). Old `text-embedding-004` vectors are in a different space; existing lectures may need re-embedding (no script exists).
- **Processing time:** `LectureDB.processing_seconds` (computed, not persisted) from `JobRepository.span_seconds`; lecture detail shows "Processed in 12.4 s / 1m 05s" next to Ready.
- **Neo4j log noise:** `get_neo4j_service` raises `Neo4jUnavailable` with a 60 s cooldown and one WARNING; callers skip quietly.
- **Test counts:** backend 306 passed, 3 skipped; frontend 16 passed.

### What was added (Phase 19 - Fast transcription providers)

- **STT providers** (`backend/services/transcription_service.py`): `DeepgramProvider` (Nova-3, whole file), `NagaWhisperProvider` (<= 20 MiB), `build_transcription_chain` + `transcribe_with_failover` (cooldown-aware).
- **Worker** (`backend/workers/transcription.py`): Deepgram-first whole-file path with no ffmpeg split; failover to chunked Naga/Gemini.
- **LLM failover** (`backend/services/ai_service.py`): `FailoverAIProvider` (naga, nim, gemini), `EmptyCompletion`, NIM default model fix, shared per-provider cooldown.
- **Config/secrets**: `DEEPGRAM_*`, `NAGA_*`, `TRANSCRIPTION_PROVIDERS`, `LLM_PROVIDERS`, `PROVIDER_COOLDOWN_SECONDS`, `LLM_TIMEOUT_S`; `put-secrets.sh` now writes DEEPGRAM_API_KEY, NAGA_AI_API_KEY, NIM_API_KEY.
- **Smoke**: `backend/scripts/smoke_providers.py` (opt-in `LIVE_PROVIDER_TESTS=1`). Docs: `docs/SPEC_AI.md`, `docs/AWS_RUNBOOK.md`, `infra/cdk/README.md`.
- **Spike**: `DEEPGRAM_LANGUAGE=multi` won on a Hinglish lecture (`19-LANGUAGE-SPIKE.md`).
- **Test counts:** 24 provider tests, LLM failover tests, 5 new worker tests; 303 passed, 3 skipped.
- **Next card in queue:** verify-work for Phase 19 (live upload-to-ready timing vs Gemini baseline).

### What was added (Phase 18 - Load Test, Capacity Report, Runbook & Docs)

- **StubProvider gate (18-01)** (`backend/services/ai_service.py`): `STUB_PROVIDERS=1` honoured only in aws/demo/staging; only transcription sleeps `STUB_DELAY_S`.
- **`infra/cdk/scripts/scale-demo.sh`**: stub-on / run / stub-off for the VER-03 scale-out demo, logs to `cdk.out/`.
- **Load tooling (18-02)**: `backend/scripts/load_users.py` (seed/mint), `loadtest/browse.js`, `loadtest/login_storm.js`, `docs/CAPACITY_REPORT.md` template.
- **Docs (18-03)**: `docs/AWS_RUNBOOK.md`, stale-doc sweep (Mongo, Rabbit queue, Redis and MinIO no longer described as production architecture; Python versions stated).
- **Test counts:** 38 passed (stub providers + presign), 8 passed (load_users + seed_demo).
- **Scale-out demo (18-04, live):** stubbed 31-job backlog took the worker ASG 1 -> 3 in about 2 min and back to 1 about 19 min after the backlog drained (scale-in confirmed from ASG activities and alarm history; the script's 40 min timeout was too short). Live run found and fixed two defects: wrong assignments URL in `scale-demo.sh`, and the API role lacked `sqs:GetQueueAttributes` (`upload-complete` returned 500).
- **Load test (18-05):** Load test: 20 concurrent users sustained at p95 < 1 s vs ~2,000 target (not met, ~100x short; 25 users already p95 2.3 s). First bottleneck: API DB connection pool (RDS connections peaked at 7 = pool 5 + overflow 2) while web CPU max 11% and RDS CPU max 8%. Login storm (5/s for 2 min) separately: p95 31.7 s, 10.6% errors. Details in `docs/CAPACITY_REPORT.md`.
- **Next card in queue:** verify-work for Phase 18.

### What was added (ChatGPT-adjudicated schema fixes: progression + teaching instances)

- **`batch_semesters` progression table** (`BatchSemesterORM`, triple, `BatchSemesterRepository`, routes `POST /admin/batch-semesters`, `GET /batches/{id}/semesters`, `DELETE /batch-semesters/{id}`): joins the cohort axis to the curriculum axis. A division's current semester is derived from term dates, never stored — one source of truth. Seeded 16 rows (2028/2029 × sems 1-8, Mumbai Univ Jul-Dec/Jan-Jun windows); live check: 2028 → Sem 5, 2029 → Sem 3.
- **Classes as teaching instances** (`ClassORM.batch_semester_id` nullable, unique now on the triple): retakes/repeat teaching no longer collide. Class creation pins the period.
- **Admin UI**: batch detail shows a cohort progression timeline (past/current/future terms); department view shows a "Currently in Semester N" badge per batch; class dialog pre-fills the teaching period from the division's batch current term.
- **Convention documented:** `Branch` (DB) = Department (institution/UI); rename deferred to a cleanup migration.
- **Deferred per advice:** subject M:N catalog, curriculum versioning (not needed until a second curriculum revision ships).
- **Test counts:** `test_batches.py` 6 passed (added progression derivation + triple-uniqueness rejection); frontend 15 passed.
- **Next card in queue:** verify-work on the admin batch flows (create batch/division via UI, rename-rename persistence), then Phase 18.

### What was added (Fr. CRCE A.Y. 2026-27 curriculum subjects)

- **Subject department + category columns** (`SubjectORM.branch_id/category`, Pydantic triple, repo `list_by_branch`/`list_by_semester_branch`, routes `POST /subjects` passthrough + `GET /branches/{id}/subjects`): subjects belong to a department within a semester, typed as mandatory/elective/lab/project/internship/broadening.
- **Curriculum seed** (`backend/scripts/seed_curriculum.py`, idempotent uuid5, rebuild-if-empty DDL guard, honest NULL credits): 324 subjects across FE/SE/TE/BE × CE(CSE)/CSE/ECS/MECH transcribed from the college curriculum docs — verified 83/78/82/81 per branch, 96 mandatory / 134 elective / 40 lab / 12 project / 4 internship / 38 broadening. BE VII/VIII pool split documented in-script (electives+research in VII; project+internship in VIII).
- **Admin UI**: subject dialog gains department + category dropdowns; class-dialog subject picker filters to the division's department when known.
- **Prisma** (`schema.prisma`): `Subject.branchId/category` + back-relations.
- **Branch code note:** official docs abbreviate Computer Engineering as CE, but the DB (and division names COMPS A/B/C) uses COMPS per the earlier spec — curriculum keyed to COMPS.
- **Test counts:** `test_batches.py` now 4 passed (added branch-subject scoping); `test_academic.py` + batch file 23 passed together; frontend 15 passed.
- **Next card in queue:** verify-work on the admin batch flows (create batch/division via UI, rename-rename persistence), then Phase 18.

### What was added (Batch-aware academic structure — Fr. CRCE cohorts)

- **Backend Batch entity** (`backend/models/orm.py` `BatchORM`, `backend/models/academic.py` triple + placement validator, `repositories/_sql/academic_repository.py` `BatchRepository`, `repositories/batch_repository.py` dispatcher, `backend/routes/admin.py`): `POST/GET/PUT/DELETE /admin/batches`, `GET /institutions/{id}/batches`, `GET /branches/{id}/divisions`, `GET /batches/{id}/divisions`; `DivisionCreate` requires `semester_id` OR (`branch_id` + `batch_id`).
- **Division cohort placement** (`DivisionORM.branch_id/batch_id` nullable FKs, `semester_id` now nullable): divisions attach to department × graduating batch, so CSE-2028 → single `CSE` while CSE-2029+ → `CSE A/B/C`. Legacy semester divisions keep working.
- **Fr. CRCE seed** (`backend/scripts/seed_crce.py`, idempotent uuid5, adopts the single existing institution instead of duplicating): 4 branches (COMPS/CSE/ECS/MECH), batches 2028 (adm 2024) + 2029 (adm 2025), years 1-4, semesters 1-8, 14 divisions per the spec matrix. Live sqlite verified: 1 institution, 4 branches, 2 batches, 14 divisions.
- **Admin UI batch support** (`HierarchyTree.jsx`, `CreateEntityDialog.jsx`, `lib/api.js`): Batches group under the college, batch detail with its divisions, department detail showing divisions grouped by batch with per-batch Add, division dialog with department/batch/semester dropdowns (no pasted IDs), batch-first setup checklist step, Batches stat.
- **Prisma** (`prisma/schema.prisma`): `Batch` model + `Division` cohort fields with back-relations (CLI validate skipped — engine download timed out offline; edits mirror existing patterns).
- **Test counts:** backend `test_batches.py` 3 passed (repo CRUD, branch×batch listing, placement validator); existing `test_academic.py` + `test_lectures.py` + `test_schema_parity.py` 27 passed; frontend 15 passed.
- **Next card in queue:** verify-work on the admin batch flows (create batch/division via UI, rename-rename persistence), then Phase 18.

### What was added (Phase 17 — Observability & Scaling, Plans 01-04)

- **Ops topic + dead-letter log (17-01)** (`infra/cdk/lectify_cdk/budget_stack.py`, `backend/workers/base.py`): CMK-encrypted `lectify-ops` SNS topic (email subscribed, account-scoped publish policy), Budget alerts fan out to EMAIL + SNS, `JOB_DEAD_LETTER` ERROR line in the worker dead-letter branch.
- **Compute logging (17-02)** (`compute_iam.py`, `compute_stack.py`, `infra/cdk/bootstrap/`): scoped log-write IAM, CloudWatch agent shipping `/var/log/lectify/*.log`, logrotate, worker ASG without template desired capacity plus group metrics.
- **ObservabilityStack (17-03)** (`infra/cdk/lectify_cdk/observability_stack.py`): `/lectify/{api,web,worker}` log groups (7d), dead-letter metric filter, 7 ops alarms + 2 scaling alarms, `WorkerScaleOut`/`WorkerScaleIn` step policies (max 3), `lectify-overview` dashboard.
- **Docs (17-04)**: `infra/cdk/README.md` section 11 (topic confirmation, test alarm, alarms, logs, dashboard, scaling); `make destroy` removes ObservabilityStack, BudgetStack persists.
- **Test counts:** CDK 65 passed (53 -> 57 -> 65); backend 36 passed in the touched worker/presign suites.
- **Live verification:** Phase 17 UAT passed all 8 checks, including confirmed ops alarm delivery, dashboard rendering, logs, and worker scaling; `17-SECURITY.md` records `threats_open: 0`.
- **Next card in queue:** Phase 16 live UAT (`/gsd-verify-work 16`) for upload-to-ready, DLQ recovery, and playback; Phase 17 is verified.

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
  - Gap closure: upload-complete now rejects non-upload re-entry (including `dead_letter`/`error`) before storage inspection, and all redrive docs enforce one recovery mechanism per lecture.
- **Test counts (new green / total green):**
  - Backend: 24 upload tests; 250 passed, 3 skipped full suite after Phase 16 gap closure and Phase 13 test-isolation refresh.
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
- **Test counts:** 250 passed, 3 skipped in the backend offline suite after the gap-closure refresh.
- **Verification:** `13-VERIFICATION.md` now passes 7/7 roadmap criteria; Phase 13 requirements QUEUE-04/06/07/08 remain Complete.
- **New graph nodes:** no source graph changes in this refresh; graphify metadata is unchanged.
- **Next card in queue:** Phase 16 human UAT (`/gsd-verify-work 16`) for live upload, ready notification, DLQ recovery, and playback.

### What was added (Phase 12 — Account Gate, Budget, CDK Skeleton & Network)

- **CDK Infrastructure Foundation** — Self-contained AWS CDK app in `infra/cdk/` (`app.py`, `budget_stack.py`, `network_stack.py`) with zero-NAT VPC, 4 subnets, S3 gateway endpoint, 4 security groups, and cost budget alarms ($50 default with 4 threshold alerts excluding credits).
- **Automation & Operator Tooling** — `infra/cdk/Makefile` with one-command deploy/destroy/preflight/orphans targets, `scripts/preflight.sh` with automated account/region/CDK/bootstrap verification.
- **Live AWS Verification** — Preflight passed, CDK bootstrap created `CDKToolkit` in `ap-southeast-2`, `BudgetStack` deployed before `NetworkStack`, teardown verified with zero orphaned resources.
- **Test counts:** 19/19 original CDK tests green (`test_budget.py`, `test_network.py`, `test_app.py`); 22 focused Phase 12 checks green in the current tree.
- **Verification:** `12-VERIFICATION.md` and `12-SECURITY.md` added; roadmap goal passed. Code review recorded 0 critical, 5 warning, and 1 informational follow-up.
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
| **D — AI pipeline** | Hierarchical chunking, embeddings, summary, notes, quiz, flashcards, exam-tag | **DONE** | `services/ai_service.py` (Gemini 3.7 Flash) |
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

- **Backend:** Python 3.11 on AWS instances (3.14 local dev), FastAPI, SQLAlchemy (async), Pydantic
- **Frontend:** Next 16 app router + React 19 (JS pages), Tailwind 3.4 + shadcn tokens (Field Notebook design system)
- **Database:** PostgreSQL (Neon), SQLite for tests
- **Storage:** S3 (AWS) / local filesystem or MinIO (local dev)
- **Queue:** SQS (AWS) / SQL-table backend (local), Postgres jobs-table idempotency (Phase 13/14)
- **AI:** STT Deepgram Nova-3 (fallback Naga whisper, Gemini); generation Naga/NIM Nemotron free with Gemini fallback; embeddings Gemini
- **Auth:** Custom JWT with role-based access (admin, teacher, student)
- **Search:** Lexical + cosine similarity
- **IaC:** AWS CDK (Python 3.12 venv) in infra/cdk: BudgetStack + NetworkStack (Phase 12) + DataStack/ComputeStack + ObservabilityStack (Phase 17); see infra/cdk/README.md
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
- **S3** (AWS) / MinIO (local) for lecture audio file storage
- **Neon (Postgres)** via SQLAlchemy async engine
- **Gemini 3.7 Flash** for all AI tasks
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
