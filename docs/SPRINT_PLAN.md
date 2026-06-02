# Production MVP Sprint Plan

Assumption: 10–12 weeks total, 2-week sprints. Adjust based on team size.

## Sprint 0 (Week 1–2): Foundations + Architecture
Goals:
- Lock MVP scope and system boundaries
- Prepare infra baseline for production-grade MVP

Deliverables:
- Finalized PRODUCTION_MVP_PLAN.md (already created)
- Data model draft (ERD in docs or diagram later)
- Env config plan (.env.example to be added in next sprint)
- Queue selection decision (RabbitMQ or Redis Queue)


## Sprint 1 (Week 3–4): Admin Hierarchy Core (Phase A)
Goals:
- Academic structure setup

Features:
- Models: Institution, Year, Branch, Semester, Subject, Division, Class
- Admin CRUD APIs for all levels
- Teacher assignment to Class
- Student enrollment model

Deliverables:
- Backend CRUD endpoints
- DB migrations (Postgres)
- Admin basic UI (list/create/update)


## Sprint 2 (Week 5–6): QR Enrollment + Access Control (Phase A)
Goals:
- Student onboarding via QR

Features:
- QR generation per Class
- QR scan → enrollment endpoint
- RBAC enforcement for class/lecture access

Deliverables:
- QR code generation service
- Enrollment endpoints
- Student “My Classes” view


## Sprint 3 (Week 7–8): Recording + Upload Flow (Phase B)
Goals:
- Teacher recording workflow

Features:
- Start/Stop recording UX (client-side)
- Chunked upload on stop
- Lecture status tracking

Deliverables:
- Teacher recording flow UI
- Upload pipeline (S3/MinIO)
- Processing status screen


## Sprint 4 (Week 9–10): Queue + Worker Pipeline (Phase C)
Goals:
- Production-grade async processing

Features:
- Queue infrastructure
- Worker pools for transcription + AI
- Retry + dead letter queue
- Priority queues (today’s lectures first)

Deliverables:
- Queue services in docker
- Worker services deployed
- Processing metrics (queue depth, SLA)


## Sprint 5 (Week 11–12): AI Pipeline Enhancements (Phase D)
Goals:
- Clean transcript + importance tagging

Features:
- Transcript cleaning step
- Exam importance extraction
- Summarization + notes + quiz + flashcards
- Embeddings for search

Deliverables:
- Updated AI prompts + pipeline code
- Importance tags in data model
- Search updated with tagged highlights


## Sprint 6 (Week 13–14): Student Delivery (Phase E)
Goals:
- Complete student experience

Features:
- Student dashboard by class
- Notes view + quiz + flashcards
- Search + bookmarks

Deliverables:
- Polished student UI
- End-to-end demo (upload → notes by EOD)


## Sprint 7 (Week 15–16): Monitoring + Reliability (Phase F)
Goals:
- Make MVP production-grade

Features:
- Prometheus + Grafana
- SLA alerts
- Failure reporting
- Daily processing summary

Deliverables:
- Monitoring dashboards
- Ops checklist


## Final Demo Checklist
- Admin can create Year/Branch/Semester/Subject/Division
- Teacher assigned to class
- QR enrollment works
- Recording → upload → queue processing
- Notes available by end of day
- Student can search + quiz + flashcards
- Monitoring dashboards active
