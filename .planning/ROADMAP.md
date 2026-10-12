# Roadmap: Lectify — AWS Cloud-Native Deployment

## Overview

This milestone moves Lectify from its local Docker stack (Redis/ARQ, MinIO, Neon, Prometheus/Grafana, nginx gateway) to AWS: SQS queues with EC2 Auto Scaling worker fleets, S3 presigned browser uploads, private RDS PostgreSQL, SNS notifications, CloudWatch observability, all defined in CDK (Python). It is a free-tier-first, one-week-deadline migration, so the work ends with a deployed, end-to-end verified stack and an honest capacity report.

Phase numbering continues from the 11 legacy phases already complete (pre-milestone), so this milestone starts at Phase 12.

**Dependency order:** 12 -> (13 ∥ 13.1 ∥ 14) -> 15 -> 16 -> 17 -> 18
Phase 13 (offline queue/storage seams), Phase 13.1 (offline class-scoped access + timetable) and Phase 14 (data/messaging infra) run in parallel after Phase 12. Phase 15 needs 13 and 14. Phase 16 needs Phase 15 and Phase 13.1, so the end-to-end demo runs on class-isolated data.

**Never cut:** DLQ, DB idempotency, presigned upload, Budget alarm, security gate.
**Cut first if time slips:** scaling tuning, presigned GET (STOR-05), SNS filter UX, SetInstanceProtection.
**Deploy cadence:** run the full stack only for demo/load windows; `cdk destroy` between sessions.

## Phases

- [x] **Phase 12: Account Gate, Budget, CDK Skeleton & Network** - Verify the AWS account, set cost alarms first, and stand up a clean-deploying CDK app with the VPC and security groups
- [x] **Phase 13: Code Seams (Queue, Jobs, Storage, Config, Security Gate)** - Offline app changes: QueueBackend (SQS/memory), Postgres job state, SQS worker loops, S3 presign, SSM overlay, flag gates, security fixes
- [x] **Phase 13.1: Class-Scoped Access & Timetable** - Lectures belong to a class; students see only their own class's lectures, AI content and timetable; per-class timetable CRUD; cross-class isolation tests (completed 2026-10-05)
- [x] **Phase 14: Data & Messaging Infrastructure** - RDS, S3 bucket policy/CORS/lifecycle, SQS queues + DLQ, SNS lecture-ready topic, secrets (completed 2026-10-05)
- [x] **Phase 15: Compute Tier & Delivery** - ALB, API/web ASG, worker ASG, per-tier IAM, unattended bootstrap, schema bootstrap on RDS (completed 2026-10-05)
- [ ] **Phase 16: Presigned Upload & End-to-End Pipeline** - Browser-direct S3 upload and one real lecture through every stage, plus the forced-failure DLQ proof
- [x] **Phase 17: Observability & Scaling** - CloudWatch logs, alarms, dashboard, ops SNS topic, and queue-backlog step scaling (completed 2026-10-09)
- [x] **Phase 18: Load Test, Capacity Report, Runbook & Docs** - Scale-out demo, load test with honest capacity numbers, runbook and doc updates (completed 2026-10-09)

## Phase Details

### Phase 12: Account Gate, Budget, CDK Skeleton & Network

**Goal**: The operator knows what the AWS account allows, spending is guarded before anything costs money, and a CDK app can create and destroy a network foundation cleanly.
**Depends on**: Nothing (first phase of this milestone)
**Requirements**: ACCT-01, ACCT-02, ACCT-03, ACCT-04, ACCT-05
**Success Criteria** (what must be TRUE):

  1. Operator can follow a documented preflight and see account identity, region, and a successful `cdk bootstrap` smoke test
  2. A Budget with email alerts at 50/80/100% exists in the account before any other stack resource is deployed
  3. `cdk deploy` and `cdk destroy` each complete with one command and leave no orphaned resources
  4. The synthesized template has public subnets, private isolated subnets, an S3 gateway endpoint, and zero NAT gateways
  5. Security groups exist so RDS accepts only app/worker SGs, the API accepts only the ALB SG, workers have no inbound rules, and no SSH rule exists

**Plans**: 4 plans
Plans:
**Wave 1**

- [x] 12-01-PLAN.md — Scaffold infra/cdk (pins, Python 3.12 venv, npm CLI), BudgetStack, validating app.py + tests (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 12-02-PLAN.md — NetworkStack: VPC, S3 gateway endpoint, 4 SGs, cost/SG guard tests, Budget-first dependency (wave 2)
- [x] 12-03-PLAN.md — Makefile deploy/destroy/destroy-all/orphans, preflight.sh, README (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 12-04-PLAN.md — Offline gate + live preflight/deploy/destroy checkpoints (wave 3, non-autonomous)

### Phase 13: Code Seams (Queue, Jobs, Storage, Config, Security Gate)

**Goal**: The backend runs the full lecture pipeline on SQS-shaped semantics, Postgres job state, S3 presign and SSM config, with all existing tests green offline and the public-deploy security gate closed.
**Depends on**: Phase 12 (can start in parallel with Phase 14; needs no AWS resources)
**Requirements**: QUEUE-01, QUEUE-03, QUEUE-04, QUEUE-05, QUEUE-06, QUEUE-07, QUEUE-08, QUEUE-09, STOR-01, DATA-02, DATA-04, SEC-04, SEC-05, COMP-06, NOTIF-01
**Success Criteria** (what must be TRUE):

  1. All 98 existing tests pass on the `memory` QueueBackend with `redis`/`arq` removed from runtime, and `enqueue_job`/`update_job_status` call sites are unchanged
  2. A duplicate delivery of the same `(lecture_id, stage, version)` is processed once; a worker deletes a message only after DB commit and next-stage enqueue
  3. A failing job retries with 60/300/900/900s backoff and ends with the lecture marked `dead_letter`; a provider 429 honors `Retry-After` without consuming a receive; SIGTERM drains in-flight work
  4. Signup with `role=admin` is rejected, the default `JWT_SECRET` aborts startup, CORS is restricted, and regression tests prove all three
  5. `S3Storage` works with instance-profile credentials and supports presigned POST/GET and `head_object`; Neo4j sync and Prometheus/Slack loops are off by flag, `/health` no longer probes Redis, and pools are sized to the documented connection budget
  6. After the AI worker sets `status=ready`, a lecture-ready publish is attempted and a publish failure never fails the stage; `prisma/schema.prisma` matches `orm.py` for the `jobs` table
  7. A long recording is split into chunks tracked individually; killing a worker mid-recording and redelivering retries only the unfinished chunks, and the merged transcript is in order

**Plans**: 13 plans
Plans:
**Wave 1**
- [x] 13-01-PLAN.md — Test baseline, security gate (SEC-04), config flags/pools/SSM overlay

**Wave 2** *(blocked on Wave 1)*
- [x] 13-02-PLAN.md — S3Storage instance-profile creds, presign POST/GET, head_object
- [x] 13-03-PLAN.md — jobs table (ORM + Prisma parity), JobRepository idempotency + atomic claim

**Wave 3** *(blocked on Wave 2)*
- [x] 13-04-PLAN.md — QueueBackend seam (memory/SQS) + queue_client facade rewrite

**Wave 4** *(blocked on Wave 3)*
- [x] 13-05-PLAN.md — Worker loop: claim/commit/enqueue/delete, backoff, dead_letter

**Wave 5** *(blocked on Wave 4)*
- [x] 13-06-PLAN.md — Provider 429 handling, SIGTERM drain, worker entrypoint

**Wave 6** *(blocked on Wave 5)*
- [x] 13-07-PLAN.md — Chunk-level transcription state (job_chunks)
- [x] 13-08-PLAN.md — Lecture-ready SNS publish hook

**Wave 7** *(blocked on Wave 6)*
- [x] 13-09-PLAN.md — Remove redis/arq, drop Redis health probe, docs/status close-out

**Gap closure** *(from 13-VERIFICATION.md)*
- [ ] 13-10-PLAN.md — (wave 1) ProviderRateLimited carries Retry-After from Gemini/NIM/Groq 429s; REQUIREMENTS rows reset to Pending
- [ ] 13-11-PLAN.md — (wave 1) Clean offline test collection + dispatcher isolation; ENV fail-closed security gate; drop dead SNS helper
- [ ] 13-12-PLAN.md — (wave 2) Crash-safe enqueue-before-complete ordering; worker honors Retry-After
- [ ] 13-13-PLAN.md — (wave 3) workers/__main__.py entrypoint, bounded SIGTERM drain + release, stage-keyed queues, docs close-out

### Phase 13.1: Class-Scoped Access & Timetable

**Goal**: Each class (e.g. Comps A, year 2) is its own isolated space: its students see only its lectures, AI content and timetable, and its assigned professor manages them.
**Depends on**: Phase 12 (offline code; runs in parallel with Phases 13 and 14; coordinate `orm.py`/`schema.prisma` edits with Phase 13)
**Requirements**: SCOPE-01, SCOPE-02, SCOPE-03, SCOPE-04, SCOPE-05, SCOPE-06
**Success Criteria** (what must be TRUE):

  1. Every lecture carries a `class_id` taken from the uploading teacher's assignment, and a teacher cannot create, publish or view lectures for a class they are not assigned to
  2. A student enrolled in Comps A sees only Comps A lectures, notes, quizzes, flashcards, search results, study data and chat context; requesting any Comps B/CSE A resource by ID returns 403/404 on every route (list, get, search, study, chat, audio)
  3. Admin or teacher can create a weekly timetable for a class, overlapping slots for the same class or teacher are rejected, and a student sees only their own class's timetable
  4. A seed mirroring the college (4 years × Comps A/B/C, CSE A/B/C, Electronics & Computer, Mechanical) exists, and an automated cross-class isolation suite passes against it

**Plans**: 7/7 plans executed
  - [x] 13.1-01: Data Model, Schema Parity, and Migrations / Models (D-02, D-05)
  - [x] 13.1-02: Lecture Upload & Teacher Assignment Verification (D-01, SCOPE-01, SCOPE-03)
  - [x] 13.1-03: Student Fail-Closed Access & Direct Item Retrieval Protection (D-03, SCOPE-02)
  - [x] 13.1-04: Scoped List & Search Filtering (D-04, SCOPE-02, SCOPE-03)
  - [x] 13.1-05: Timetable Slot CRUD, Overlap Detection & Access Control (D-05, D-06, D-07, SCOPE-04, SCOPE-05)
  - [x] 13.1-06: Frontend Integration for Class Upload & Timetable (SCOPE-01, SCOPE-05, UI hint)
  - [x] 13.1-07: College Structure Seed Fixture & Cross-Class Isolation Test Suite (D-08, D-09, SCOPE-06)

**UI hint**: yes

### Phase 14: Data & Messaging Infrastructure

**Goal**: The stateful AWS resources exist and are locked down: database, bucket, queues, topics, and secrets.
**Depends on**: Phase 12 (can run in parallel with Phase 13)
**Requirements**: QUEUE-02, DATA-01, STOR-04, STOR-06, SEC-01, SEC-02, NOTIF-02
**Success Criteria** (what must be TRUE):

  1. RDS PostgreSQL 16 `db.t4g.micro` is running single-AZ in the private subnets with TLS enforced and automated backups, and is unreachable from the internet
  2. The S3 bucket has Block Public Access, SSE encryption at rest, class/lecture-namespaced key layout, CORS for the app origin, and abort-incomplete-multipart plus expiry lifecycle rules
  3. Three SQS Standard queues (transcribe, materials, embed) and one shared DLQ with maxReceiveCount=5 exist
  4. JWT/Groq/Gemini values live in SSM SecureString (created by a put-script, not CDK or the repo) and the RDS password lives in one generated Secrets Manager secret; grep of the repo and user-data finds no secrets
  5. The `lecture-ready` SNS topic exists with operator/demo email subscriptions that can be confirmed, and the per-student limitation is documented

**Plans**: 3/3 plans complete

**Wave 1**
- [x] 14-01-PLAN.md — DataStack Core: S3 bucket, 3 SQS stage queues + shared DLQ, SNS lecture-ready topic + email subscriptions

**Wave 2** *(blocked on Wave 1)*
- [x] 14-02-PLAN.md — RDS PostgreSQL 16 on db.t4g.micro, ParameterGroup (force_ssl=1), Secrets Manager secret, CfnOutputs

**Wave 3** *(blocked on Wave 2)*
- [x] 14-03-PLAN.md — SSM put-secrets.sh, repo secrets scanner & cost trap tests, Makefile deploy/destroy updates, README documentation

### Phase 15: Compute Tier & Delivery

**Goal**: The app is reachable through the ALB, workers poll SQS, all instances bootstrap unattended, and the schema exists on RDS.
**Depends on**: Phase 13, Phase 14
**Requirements**: COMP-01, COMP-02, COMP-03, COMP-04, COMP-05, SEC-03, DATA-03
**Success Criteria** (what must be TRUE):

  1. Visiting the ALB URL serves the Next.js app, `/api/*` reaches FastAPI, and the target group stays healthy on the shallow `/healthz` check
  2. A fresh API/web ASG instance and a fresh worker ASG instance reach healthy with no manual steps (Python 3.11, Node, swap, venv, pinned ffmpeg smoke test all pass), with Next.js built off-instance
  3. The worker ASG runs one systemd process with three poll loops and a hard max-capacity cap
  4. Frontend requests go to same-origin `/api` (no `"undefined/api"`), and a user can log in on the deployed stack against the seeded demo institution and users
  5. API and worker roles are scoped to the specific S3 prefix, queues, SNS topic and SSM path with no wildcards, IMDSv2 is required, and instances are reachable only via Session Manager

**Plans**: 6/6 plans complete

**Wave 1**
- [x] 15-01-PLAN.md — Backend seams: shallow `/healthz`, DB URL from Secrets Manager, `workers all` (3 loops, 1 process), `DB_AUTO_CREATE` gate
- [x] 15-03-PLAN.md — Frontend same-origin `/api`, Next `/healthz`, off-instance `build-web.sh`
- [x] 15-04-PLAN.md — ComputeStack skeleton: ALB + target groups + `/api/*` rule, per-tier least-privilege IAM roles

**Wave 2** *(blocked on Wave 1)*
- [x] 15-02-PLAN.md — `bootstrap_db` (advisory lock) + idempotent `seed_demo`

**Wave 3** *(blocked on Waves 1-2)*
- [x] 15-05-PLAN.md — Launch templates (IMDSv2), web/worker ASGs (worker max 3), unattended bootstrap, systemd units, CFN signals, app.py wiring

**Wave 4** *(blocked on Wave 3)*
- [x] 15-06-PLAN.md — Makefile targets, ffmpeg vendoring, README runbook (two-step deploy), hygiene scan, CLAUDE.md status

**UI hint**: yes

### Phase 16: Presigned Upload & End-to-End Pipeline

**Goal**: A student uploads audio straight to S3 and the lecture flows through every stage to ready, with failure handling proven on the live stack.
**Depends on**: Phase 15, Phase 13.1
**Requirements**: STOR-02, STOR-03, STOR-05, NOTIF-03, VER-01, VER-02
**Success Criteria** (what must be TRUE):

  1. A student can pick a recording in the upload page, see upload progress, and have the file go browser-to-S3 via `upload-url` then `upload-complete`
  2. Upload completion rejects missing or oversized objects (verified by `head_object`, ≤200 MB cap), and presigned URLs expire within 15 minutes
  3. One real lecture runs upload -> transcript -> materials -> embed -> ready, the student sees the ready status in-app, and the operator receives the SNS ready email
  4. A forced failure lands in the DLQ with the lecture marked `dead_letter`, and the documented redrive procedure recovers it
  5. A student can play back lecture audio via a presigned GET (cut first if time slips)

**Plans**: 5 plans
Plans:
**Wave 1**

- 16-01-PLAN.md — Backend presigned trio tracer: upload-url + uploading status, upload-complete head_object idempotent enqueue, audio-url class-gated (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- 16-02-PLAN.md — Frontend browser-direct uploadToS3 with XHR progress + 501 fallback, ready/failed pills, presigned audio with blob fallback (wave 2)
- 16-03-PLAN.md — Forced-failure DLQ proof, redrive-dlq.sh + README runbook, SPEC docs + VER-01/VER-02 operator record (wave 2)

**Gap closure** *(from 16-VERIFICATION.md, wave 1, parallel)*

- 16-04-PLAN.md — G1 critical: gate complete_upload to uploading/uploaded-only before head_object, 409 otherwise, clear error_message on success
- 16-05-PLAN.md — G2 docs: redrive-dlq.sh + README either-or (message-move OR /retry, never both)

**UI hint**: yes

### Phase 17: Observability & Scaling

**Goal**: Operators can see the system's health in one place, get alerted on real problems, and the worker fleet scales on backlog within a hard cap.
**Depends on**: Phase 16
**Requirements**: OBS-01, OBS-02, OBS-03, OBS-04
**Success Criteria** (what must be TRUE):

  1. API and worker logs appear in CloudWatch with 7-day retention
  2. No more than 10 alarms cover queue backlog, DLQ depth, EC2 CPU and job failure rate, and a test alarm delivers to a confirmed ops SNS subscription along with Budget notifications
  3. One CloudWatch dashboard shows queue depth, worker count, CPU, DLQ and failures
  4. Queue backlog (visible + in-flight across transcribe and materials) drives the worker ASG to scale out and back in via step scaling, with a long scale-in cooldown and max capacity of 2-3

**Plans**: 4/4 plans complete
Plans:
**Wave 1**

- [x] 17-01-PLAN.md — Ops SNS topic (CMK) + Budget SNS subscriber in BudgetStack; JOB_DEAD_LETTER worker log line (wave 1)
- [x] 17-02-PLAN.md — Scoped log IAM, worker ASG scaling-ready (no desired, group metrics), CloudWatch agent + unit file logging (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 17-03-PLAN.md — ObservabilityStack: log groups, metric filter, 7 alarms, step scaling, lectify-overview dashboard, app.py wiring (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 17-04-PLAN.md — README section 11, CLAUDE.md status, live verification checkpoint (wave 3)

### Phase 18: Load Test, Capacity Report, Runbook & Docs

**Goal**: Capacity is measured and reported honestly, and anyone can redeploy, operate and tear down the stack from the docs.
**Depends on**: Phase 17
**Requirements**: VER-03, VER-04, VER-05
**Success Criteria** (what must be TRUE):

  1. A provider-stubbed demo shows the worker ASG scaling out on a backlog and back in
  2. A k6/Locust load test (pre-minted tokens, login storm reported separately) runs against the deployed stack and produces a capacity report stating measured concurrent users versus the ~2,000 target
  3. `docs/AWS_RUNBOOK.md` lets an operator deploy, run the secrets put-script, bootstrap the schema, redrive the DLQ, tear down, and understand cost notes
  4. CLAUDE.md Status/Stack and stale docs (Python 3.11, queue, storage) reflect the AWS architecture

**Plans**: 5 plans
Plans:
**Wave 1**

- [x] 18-01-PLAN.md — Env-gated StubProvider + scale-demo.sh (stub-on/stub-off/run) (VER-03)
- [x] 18-02-PLAN.md — load_users.py seed/mint, k6 browse + login storm scripts, CAPACITY_REPORT template (VER-04)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 18-03-PLAN.md — docs/AWS_RUNBOOK.md + stale-doc sweep + CLAUDE.md Stack/Status (VER-05)

**Wave 3** *(non-autonomous, live AWS)*

- [x] 18-04-PLAN.md — Live provider-stubbed scale-out/in demo, evidence into report (VER-03)

**Wave 4** *(non-autonomous, live AWS)*

- [x] 18-05-PLAN.md — k6 install gate, live load test + login storm, complete capacity report + CLAUDE.md (VER-04, VER-05)

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 12. Account Gate, Budget, CDK Skeleton & Network | 4/4 | Complete |  |
| 13. Code Seams | 9/9 | Complete | 2026-10-05 |
| 13.1. Class-Scoped Access & Timetable | 7/7 | In Progress | - |
| 14. Data & Messaging Infrastructure | 3/3 | Complete    | 2026-10-05 |
| 15. Compute Tier & Delivery | 0/TBD | Not started | - |
| 16. Presigned Upload & End-to-End Pipeline | 0/TBD | Not started | - |
| 17. Observability & Scaling | 4/4 | Complete    | 2026-10-09 |
| 18. Load Test, Capacity Report, Runbook & Docs | 5/5 | Complete    | 2026-10-09 |

### Phase 19: Fast transcription providers: Deepgram Nova-3 STT and NagaAI LLM provider

**Goal:** Cut lecture transcription and AI-generation latency by adding Deepgram Nova-3 (pre-recorded STT) and NagaAI (OpenAI-compatible LLM gateway) behind the existing provider seam in `backend/services/ai_service.py`, env-selected with failover to Gemini. Lectures are mixed Hindi+English (Nova-3 multi); generation uses free models only (Naga/NIM Nemotron). See 19-RESEARCH.md. Self-hosted Whisper/NVIDIA GPU on EC2 evaluated and rejected (no GPU on free tier / credit-account quota).
**Requirements**: P19-CONFIG, P19-SPIKE, P19-STT, P19-LLM, P19-WORKER, P19-TEST, P19-DOCS (phase-local)
**Depends on:** Phase 18
**Plans:** 6/6 plans complete

Plans:
- [x] 19-01-PLAN.md — Settings, shared provider cooldown, hermetic test keys, SSM put-secrets keys (wave 1)
- [x] 19-02-PLAN.md — Hinglish language spike: Nova-3 multi vs hi vs en-IN, user picks winner (wave 1, checkpoints)
- [x] 19-03-PLAN.md — DeepgramProvider + NagaWhisperProvider + ordered STT failover chain (wave 2)
- [x] 19-04-PLAN.md — Free LLM chain Naga -> NIM -> Gemini, content=None + 429 cooldown, NIM default fix (wave 2)
- [x] 19-05-PLAN.md — TranscriptionWorker: Deepgram whole-file first, chunked chain fallback, stub regression (wave 3)
- [x] 19-06-PLAN.md — Live smoke script, spike winner applied, docs + CLAUDE.md Status, graphify (wave 4)
