# LectureMind AI — PRD

## Problem statement (original)
Build an AI-first educational platform that turns classroom lecture audio into
structured, multilingual, student-friendly learning systems: transcripts, smart
notes, quizzes, flashcards, search, analytics — for institutions.

## User personas
- Teacher: uploads lectures, reviews AI output, publishes to students.
- Student: browses published lectures, studies notes, takes quizzes, practices
  flashcards.

## Architecture (preview env)
- Backend: FastAPI + Motor (Mongo, repo-pattern abstracted)
- AI: Google Gemini 2.5 Flash via `google-genai` SDK (single AI service layer)
- Storage: pluggable `StorageService` (LocalStorage now, S3/MinIO in self-host)
- Auth: JWT (HS256) with teacher/student roles
- Frontend: React + Tailwind + shadcn/ui + Phosphor icons + framer-motion

## What's been implemented (2026-02)
- ✅ Repository-pattern data layer (UserRepository, LectureRepository, ChatRepository, AttemptRepository)
- ✅ Storage abstraction (LocalStorage; S3 ready)
- ✅ AIProvider abstraction → GeminiProvider (gemini-2.5-flash) with `chat`, `translate_pack`, `embed` methods
- ✅ JWT auth: signup / login / me (teacher & student roles)
- ✅ Lecture upload + background AI pipeline (now also computes embeddings)
- ✅ Smart notes, quiz, flashcards generation (structured JSON output)
- ✅ Teacher dashboard with auto-refreshing status
- ✅ Lecture detail page (tabs: Notes / Quiz / Flashcards / **Doubt Chat** / Transcript)
- ✅ Quiz runner with grading + explanations (now persists attempts for analytics)
- ✅ Flashcard deck with 3D flip animation (framer-motion)
- ✅ Student dashboard with **semantic + lexical search** across published lectures
- ✅ **P1: Doubt Chat (RAG over lecture transcript)** — per-(lecture,user) history, suggestion chips
- ✅ **P1: Multilingual translation** — 9 languages, cached on lecture doc
- ✅ **P1: Semantic search** — Gemini text-embedding-004 + cosine similarity + lexical fallback
- ✅ **P1: Student analytics** — attempts, avg score, streak, weak topics, strong topics
- ✅ Audio streaming endpoint with auth
- ✅ Landing page + auth split-screen
- ✅ Publish / unpublish lecture
- ✅ Docker Compose for self-host (Postgres + MinIO + backend + frontend)
- ✅ MIGRATION.md (Mongo → Postgres step-by-step)

## P0 backlog
- Real S3/MinIO storage implementation (currently local only)
- Postgres repository implementations (scaffold already in MIGRATION.md)

## P1 backlog
- Lecture audio chunking for >30 min recordings
- Translation of quiz questions (currently kept in original language for grading integrity)
- Teacher analytics: most-confusing topics, engagement

## P2 backlog
- Podcast / TTS revision audio
- Real-time live transcription
- Knowledge graph
- Mobile app

## Next tasks
1. Set `GEMINI_API_KEY` in `/app/backend/.env` to enable AI processing.
2. Implement S3 storage backend (boto3) so self-host works out of the box.
3. Build AI doubt chat over each lecture's transcript.
