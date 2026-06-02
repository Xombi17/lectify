# Production MVP Plan (Lecture Intelligence Platform)

## 0) Non-Negotiables
- Production-grade from MVP (no throwaway architecture).
- Optimized code by default (avoid rework later).
- Queue-driven processing for parallel lectures.
- Same-day delivery target; next-day max.

## 1) Goals (MVP)
Deliver a stable system that can:
- Capture long lectures (mic/upload)
- Transcribe at scale
- Clean transcript (remove non-academic content)
- Generate study assets
- Publish to students by end of day
- Support admin hierarchy (year/branch/semester/subject/division)
- Enroll students via QR

## 2) Architecture (MVP Production-Ready)
- API: FastAPI
- Queue: RabbitMQ or Redis Queue
- Workers: Python workers (AI pipeline)
- Storage: S3/MinIO
- DB: Postgres (primary)
- Monitoring: Prometheus + Grafana (basic)

## 3) Pipeline (Queue-Driven)
Upload → Enqueue Transcribe → Enqueue Clean → Enqueue Generate → Enqueue Index → Publish

Each stage:
- idempotent
- retryable
- stores partial output

## 4) Phase Plan (Feature-by-Feature)

Phase A: Core Admin + Academic Structure
- Data models: Institution, Year, Branch, Semester, Subject, Division, Class
- Admin CRUD APIs for all
- Teacher assignment to Class
- Student enrollment by QR
- Admin dashboard UI

Phase B: Recording + Upload Flow
- Teacher Start/Stop button
- Upload after stop
- Audio chunking (long sessions)
- Store in S3/MinIO immediately
- Status tracking for lecture processing

Phase C: Queue + Worker System
- Add queue infra
- Worker pools for transcription and AI
- Concurrency limits
- Priority queue (today’s lectures first)
- Retry + dead-letter for failures

Phase D: AI Pipeline (Production Grade)
- Transcription (Whisper API or self-hosted)
- Transcript cleaning (remove scolding/off-topic)
- Exam importance extraction
- Summarization + notes + quiz + flashcards
- Embedding for search

Phase E: Student Delivery
- Student dashboard
- Search
- Lecture notes view
- Quiz + flashcards
- Bookmarking

Phase F: Monitoring + Reliability
- Job SLA tracking
- Queue metrics
- Failure alerts
- Daily processing summary

## 5) Success Criteria
- 95% lectures processed same day
- 99% job reliability (retryable)
- Students see notes by end of day
- Admin can configure academic hierarchy

## 6) Optimization Rules
- Chunk large audio
- Use parallel transcription
- Cache AI outputs
- Avoid reprocessing unchanged content

## 7) Risks + Mitigation
- Load spikes → queue + worker scaling
- Bad audio → confidence thresholds + alerts
- Cost spikes → chunking + caching + priority

