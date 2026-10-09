# Technical Spec (Production MVP)

## 1) Architecture
- API: FastAPI
- DB: Postgres
- Storage: S3 (AWS; presigned browser upload)
- Queue: SQS Standard, 3 stage queues + shared DLQ, idempotency in Postgres jobs table
- Workers: Python AI workers

## 2) Core Services
- Auth
- Admin hierarchy management
- Lecture upload + processing
- AI pipeline (transcribe → clean → generate)
- Search (semantic + lexical)

## 3) Data Entities
- Institution, Year, Branch, Semester, Subject, Division, Class
- TeacherAssignment
- StudentEnrollment
- Lecture
- StudyMaterials
- Quiz, Flashcard

## 4) Processing Pipeline
- Chunking → parallel transcription → cleaning → summarization → publish

## 5) Reliability
- Idempotent jobs
- Retry + dead-letter queue
- Monitoring + SLA metrics

### Connection budget & rate limiting
- DB Budget = (5+2) per process × API/worker count must stay < ≈60.
- Rate limiter is in-memory per instance (SEC-05 limitation).

