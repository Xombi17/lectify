# LectureMind AI — PRD

## Problem statement (original)
Build an AI-first educational platform that turns classroom lecture audio into
structured, multilingual, student-friendly learning systems: transcripts, smart
notes, quizzes, flashcards, search, analytics — for institutions.

## User personas
- Teacher: uploads lectures, reviews AI output, publishes to students.
- Student: browses published lectures, studies notes, takes quizzes, practices
  flashcards.

## Architecture (preview env vs self-host)
- **Preview**: MongoDB (Motor) + Local filesystem storage. `DATABASE_BACKEND=mongo`, `STORAGE_BACKEND=local`.
- **Self-host (docker compose)**: PostgreSQL (SQLAlchemy 2.0 async) + MinIO/S3 (aioboto3). `DATABASE_BACKEND=postgres`, `STORAGE_BACKEND=s3`. Same code, env-var flip only.
- Backend: FastAPI + repository pattern + AI service abstraction + storage abstraction
- AI: Google Gemini 2.5 Flash via `google-genai` SDK (text + audio + embeddings)
- Auth: JWT (HS256) with teacher/student roles
- Frontend: React + Tailwind + shadcn/ui + Phosphor icons + framer-motion

## What's been implemented (2026-02)
- ✅ Repository pattern data layer (User, Lecture, Chat, Attempt, **Bookmark**, **FlashcardReview**) — dispatched by `DATABASE_BACKEND` (mongo / postgres)
- ✅ Storage abstraction (LocalStorage + S3Storage via aioboto3) — dispatched by `STORAGE_BACKEND` (local / s3)
- ✅ AIProvider abstraction → GeminiProvider (transcribe / digest_chunk / merge_chunk_digests / generate_study_materials / chat / translate_pack / embed)
- ✅ JWT auth (teacher / student roles)
- ✅ Lecture upload + long-lecture chunking + hierarchical merge + real-time progress
- ✅ Smart notes / Quiz / Flashcards (now editable by teacher) / Doubt Chat (RAG) / Translation (9 langs)
- ✅ Semantic + lexical search, student analytics with streak + weak topics
- ✅ Audio streaming (works on Local + S3 via StreamingResponse)
- ✅ **Phase 1 P1 study tools** — teacher inline editing of summary/notes/concepts, **PDF export** (reportlab, branded), **bookmarks** (concept / note / flashcard) with dedicated page, **spaced-repetition flashcards** (SM-2 lite with Again/Hard/Good/Easy ratings + global daily review queue)
- ✅ Docker Compose (Postgres + MinIO + backend with ffmpeg + nginx frontend), MIGRATION.md
- ✅ Per-loop client caching, path-traversal guards
- ✅ 126/126 backend tests passing

## P0 backlog
- *(all complete)*

## P1 / P2 backlog (no paid API needed)
- Smart timestamping + audio jump-to topics (uses existing chunk data; needs Gemini timestamp extraction pass)
- Mind maps / knowledge graph (Gemini extracts hierarchy → render with d3 or simple tree)
- Adaptive learning recommendations (weak topics → easier explanation pass via Gemini)
- In-browser live recording (MediaRecorder API)
- Multi-tenancy: Super Admin + Institution + Department + Subject + per-tenant data scoping
- Teacher cohort analytics (most-confused topics, engagement heatmap)
- Assignments
- Audit logs, consent capture, data retention/deletion
- Alembic migrations on top of SQLAlchemy schema
- Manual highlights on AI notes (related to bookmarks)
- Translation of quiz questions with answer-key re-mapping

## P1 / P2 backlog (paid API or hardware)
- Podcast / TTS revision audio (ElevenLabs / OpenAI TTS)
- AI whiteboard / diagram detection (camera + vision API)
- AI exam prediction (needs corpus of past papers)
- Mobile app (Flutter / React Native)
- Real-time AI teaching assistant (confusion / attention detection)
- Classroom hardware integration (smart mic / edge AI device)
- Zoom / Meet integration
- ✅ Repository-pattern data layer (UserRepository, LectureRepository, ChatRepository, AttemptRepository)
- ✅ Storage abstraction (LocalStorage; S3 ready)
- ✅ AIProvider abstraction → GeminiProvider (gemini-2.5-flash) with `chat`, `translate_pack`, `embed`, `digest_chunk`, `merge_chunk_digests` methods
- ✅ JWT auth: signup / login / me (teacher & student roles)
- ✅ Lecture upload + background AI pipeline (now also computes embeddings)
- ✅ **Long-lecture handling**: ffmpeg-driven chunking (>30 min → ~10-min chunks), hierarchical merge into one study pack; live progress (step/total/label/chunk_count) persisted on the lecture doc and shown in the UI
- ✅ Smart notes, quiz, flashcards generation (structured JSON output)
- ✅ Teacher dashboard with auto-refreshing status
- ✅ Lecture detail page (tabs: Notes / Quiz / Flashcards / Doubt Chat / Transcript) with progress bar for long lectures
- ✅ Quiz runner with grading + explanations (persists attempts for analytics, RBAC-protected)
- ✅ Flashcard deck with 3D flip animation (framer-motion)
- ✅ Student dashboard with semantic + lexical search across published lectures
- ✅ Doubt Chat (RAG over lecture transcript)
- ✅ Multilingual translation (9 languages, cached on lecture doc)
- ✅ Semantic search (Gemini text-embedding-004 + cosine similarity + lexical fallback)
- ✅ Student analytics (attempts, avg score, streak, weak/strong topics)
- ✅ Audio streaming endpoint with auth
- ✅ Landing page + auth split-screen
- ✅ Publish / unpublish lecture
- ✅ Docker Compose for self-host (Postgres + MinIO + backend + frontend) — backend image bakes in ffmpeg
- ✅ MIGRATION.md (Mongo → Postgres step-by-step)
- ✅ Per-loop Mongo client (safe across multiple asyncio loops; production hardening)

## P0 backlog
- *(all complete)*

## P1 backlog
- Translation of quiz questions (currently kept in original language for grading integrity)
- Teacher analytics: most-confusing topics, engagement
- Alembic migrations on top of the SQLAlchemy schema (currently `Base.metadata.create_all` idempotent bootstrap)

## P2 backlog
- Podcast / TTS revision audio
- Real-time live transcription
- Knowledge graph
- Mobile app

## Next tasks
1. Set `GEMINI_API_KEY` in `/app/backend/.env` to enable AI processing.
2. Implement S3 storage backend (boto3) so self-host works out of the box.
3. Build AI doubt chat over each lecture's transcript.
