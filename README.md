# LectureMind AI

**AI-powered lecture intelligence platform.** Upload lecture recordings, get automatic transcripts, AI-generated summaries, study notes, flashcards, and quizzes — plus a RAG chatbot that answers questions grounded in your lecture content.

---

## Architecture

```
lectify/
├── backend/          # FastAPI application (Python 3.11 on AWS instances; local dev tested on 3.14)
│   ├── core/          # Config, DB connections, auth, security
│   ├── models/        # Pydantic + SQLAlchemy ORM models
│   ├── repositories/  # Data-access layer (thin dispatchers)
│   │   └── _sql/      # SQLAlchemy async implementations
│   ├── routes/        # API endpoints (auth, lectures, chat, search, study, analytics)
│   ├── services/      # Business logic (AI, storage, PDF export, spaced repetition)
│   └── tests/         # pytest suite
├── frontend/          # React 19 app (CRA + CRACO + Tailwind + Radix UI)
│   └── src/           # Components, pages, API client
├── docker-compose.yml # Local-only stack (Postgres + MinIO + backend + frontend)
├── run.sh             # Single-command launcher for local dev
└── .env.example       # Environment variable template
```

### Tech Stack

| Layer       | Technology                                                           |
|-------------|----------------------------------------------------------------------|
| Backend     | Python 3.11 on AWS instances (3.14 local dev), FastAPI, SQLAlchemy 2.0 (async) |
| AI          | Google Gemini 3.7 Flash (transcription, summarisation, quiz gen)     |
| Database    | PostgreSQL 16 (prod) / SQLite (dev)                                  |
| Storage     | S3 (AWS) / local filesystem or MinIO via docker-compose (local)      |
| Queue       | SQS stage queues + DLQ (AWS) / SQL-table backend (local); job idempotency in Postgres |
| Frontend    | React 19, CRACO, Tailwind CSS, Radix UI, TanStack Query, Recharts   |
| Auth        | JWT (bcrypt + PyJWT)                                                 |

---

## Deploying to AWS

See [docs/AWS_RUNBOOK.md](docs/AWS_RUNBOOK.md) (deploy, operate, teardown) and [docs/CAPACITY_REPORT.md](docs/CAPACITY_REPORT.md) (load-test results).

---

## Quick Start (Local Dev — No Docker Required)

### Prerequisites

- **Python 3.11+** with `venv`
- **Node.js 20+** with `npm` or `yarn`
- **FFmpeg** (for audio chunking — `apt install ffmpeg` / `brew install ffmpeg`)

### 1. Clone & Configure

```bash
git clone <repo-url> && cd lectify
cp .env.example .env
# Edit .env — at minimum set GEMINI_API_KEY for AI features
```

### 2. Run Everything

```bash
./run.sh
```

This single command:
1. Creates a Python venv & installs backend dependencies
2. Auto-detects if `npm` or `yarn` is available & installs frontend dependencies
3. Starts the **backend** (uvicorn on port 8001)
4. Starts the **frontend** dev server (port 3000)
5. Cleans up both processes on Ctrl+C

After startup, visit:
- **Frontend:** http://localhost:3000
- **API docs:** http://localhost:8001/docs
- **Health check:** http://localhost:8001/api/health

### Manual Start (for debugging)

```bash
# Terminal 1 — Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# Terminal 2 — Frontend
cd frontend
npm install && npm start
```

---

## Docker (Local-only Stack)

For a full local stack with PostgreSQL, MinIO, Neo4j:

```bash
docker compose up --build -d
```

| Service    | URL                        |
|------------|----------------------------|
| Frontend   | http://localhost:3000      |
| Backend    | http://localhost:8001      |
| API docs   | http://localhost:8001/docs |
| MinIO UI   | http://localhost:9001      |
| Neo4j      | http://localhost:7474      |

Before running, copy `.env.example` to `.env` and fill in the required values (`JWT_SECRET`, `GEMINI_API_KEY`).

---

## Environment Variables

| Variable                 | Default                  | Description                            |
|--------------------------|--------------------------|----------------------------------------|
| `DATABASE_BACKEND`       | `postgres`               | `postgres` or `sqlite` (SQL only)      |
| `DATABASE_URL`           | —                        | SQL connection string                  |
| `JWT_SECRET`             | `change-me`              | HMAC secret for JWT tokens             |
| `JWT_ALGORITHM`          | `HS256`                  | JWT signing algorithm                  |
| `JWT_EXPIRE_MINUTES`     | `10080` (7 days)         | Token expiry                           |
| `GEMINI_API_KEY`         | —                        | Google AI Studio API key               |
| `GEMINI_MODEL`           | `gemini-3.7-flash`       | Gemini model name                      |
| `STORAGE_BACKEND`        | `local`                  | `local` or `s3`                        |
| `STORAGE_LOCAL_DIR`      | `./storage_data`         | Directory for local file storage       |
| `CORS_ORIGINS`           | `*`                      | Comma-separated allowed origins        |

---

## Features

### Core Pipeline
1. **Upload & Chunk** — Upload lecture audio; auto-chunked for long recordings
2. **Transcription** — Gemini-powered speech-to-text with language detection
3. **Transcript Cleaning** — AI cleans filler words, speaker disfluencies
4. **Exam Importance Tagging** — Key exam-relevant passages highlighted
5. **Study Pack Generation** — Notes, quiz questions, flashcards per lecture

### Student Features
- **Dashboard** — Recent lectures, study progress, due flashcards
- **RAG Chat** — Ask questions grounded in your lecture transcripts
- **Search** — Full-text search across all lectures and transcripts
- **Bookmarks** — Save and organise important sections
- **Spaced Repetition** — Flashcard review with SM-2 algorithm
- **PDF Export** — Download study packs as formatted PDFs

### Admin Hierarchy
- Institution → Year → Branch → Semester → Subject → Division → Class
- QR-based student enrollment
- Role-based access (student / teacher / admin)

---

## Development

### Running Tests

```bash
cd backend

# All tests (in-memory SQLite backend):
python -m pytest tests/ -v

# Specific test files:
python -m pytest tests/test_academic.py -v
python -m pytest tests/test_lecturemind_api.py -v
python -m pytest tests/test_sql_repositories.py -v
```

The test suite uses an in-memory SQLite database with AIOSQLite — no external services needed.

### Project Structure (Graph)

This project ships with a knowledge graph generated by [Graphify](https://github.com/safishamsi/graphifyy). For architectural questions:

```bash
# Explore the graph interactively:
open graphify-out/graph.html
# Read the full audit report:
cat graphify-out/GRAPH_REPORT.md
```

### Code Conventions
- **AGENTS.md** and **CLAUDE.md** are the source of truth for AI agents
- Repository pattern with thin dispatchers over SQL implementations (SQL only)
- All async where possible
- Tests use monkeypatched env vars for backend selection

---

## License

Private / internal use. See LICENSE file (if any).
