#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# LectureMind AI — Single-Command Launcher
# ═══════════════════════════════════════════════════════════════════════════════
# Usage:
#   ./run.sh                  Start backend + frontend for local dev
#   ./run.sh --docker         Start full stack via docker compose
#   ./run.sh --help           Show this help
#
# Default mode (no flags): SQLite + local storage, backend on :8001, frontend
# on :3000. Zero external services required.
#
# Requirements: python3, node/npm (or yarn), ffmpeg (for audio chunking).
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

BACKEND_PORT="${PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
BACKEND_LOG="${SCRIPT_DIR}/.logs/backend.log"
FRONTEND_LOG="${SCRIPT_DIR}/.logs/frontend.log"
BACKEND_PID=""
FRONTEND_PID=""
_CLEANED=false

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; NC='\033[0m' # No Colour

info()  { echo -e "${CYAN}[lectify]${NC} $*"; }
ok()    { echo -e "${GREEN}[✔]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
err()   { echo -e "${RED}[✘]${NC} $*" >&2; }

# ── Help ──────────────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
    sed -n '3,12p' "$0"
    echo
    echo "Flags:"
    echo "  --docker    Start full stack via docker compose (Postgres + MinIO + app)"
    echo "  --help      Show this message"
    echo
    exit 0
fi

# ── Docker Mode ───────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--docker" ]]; then
    if ! command -v docker &>/dev/null; then
        err "Docker is not installed."
        exit 1
    fi
    if [[ ! -f .env ]]; then
        cp .env.example .env
        warn ".env file created from .env.example — edit it with your GEMINI_API_KEY and JWT_SECRET."
    fi
    info "Starting full stack with Docker Compose..."
    exec docker compose up --build
fi

# ── Prerequisites ─────────────────────────────────────────────────────────────
info "Checking prerequisites..."

command -v python3 &>/dev/null || { err "python3 is required."; exit 1; }
PYTHON="$(command -v python3)"

# Check for node + npm (or yarn)
NPM=""
YARN=""
if command -v yarn &>/dev/null; then
    YARN="$(command -v yarn)"
    ok "yarn found"
elif command -v npm &>/dev/null; then
    NPM="$(command -v npm)"
    ok "npm found"
else
    err "npm or yarn is required for the frontend."
    exit 1
fi

# FFmpeg (optional — only needed for long audio chunking)
if command -v ffmpeg &>/dev/null; then
    ok "ffmpeg found"
else
    warn "ffmpeg not found — long lecture chunking will be unavailable (install with: apt install ffmpeg / brew install ffmpeg)"
fi

ok "Prerequisites satisfied"

# ── Environment ───────────────────────────────────────────────────────────────
if [[ ! -f .env ]]; then
    cp .env.example .env
    warn ".env file created from .env.example — edit it to set GEMINI_API_KEY for AI features."
fi

# Export vars from .env (no clobber if already set)
set -a; source .env; set +a

# Defaults that let the app boot with zero external services
export DATABASE_BACKEND="${DATABASE_BACKEND:-postgres}"
export DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///./lecturemind.db}"
export STORAGE_BACKEND="${STORAGE_BACKEND:-local}"
# SQLite queue so the API and worker processes share one queue file locally
# (the memory backend is per-process; SQS is for deployed environments).
export QUEUE_BACKEND="${QUEUE_BACKEND:-sqlite}"
export STORAGE_LOCAL_DIR="${STORAGE_LOCAL_DIR:-./storage_data}"
export JWT_SECRET="${JWT_SECRET:-change-me-dev-local}"
export CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:3000}"

# ── Backend Setup ─────────────────────────────────────────────────────────────
info "Setting up backend..."

cd backend

# Create venv if needed
if [[ ! -d .venv ]]; then
    info "Creating Python virtual environment..."
    "$PYTHON" -m venv .venv
    ok "Virtual environment created"
fi

source .venv/bin/activate

# Install deps — use a marker file to skip if unchanged
REQS_HASH="$(md5sum requirements.txt 2>/dev/null | cut -d' ' -f1 || true)"
CACHED_HASH=""
[[ -f .requirements_hash ]] && CACHED_HASH="$(cat .requirements_hash)"

if [[ "$REQS_HASH" != "$CACHED_HASH" ]]; then
    info "Installing/updating Python dependencies..."
    # Install core deps needed to run the server (not the full requirements.txt
    # which has many pinned extras). Add more as needed for AI features.
    pip install -q \
        fastapi uvicorn sqlalchemy aiosqlite aiofiles bcrypt pyjwt \
        pydantic pydantic-settings python-dotenv python-multipart \
        passlib email-validator httpx python-jose \
        neo4j reportlab tiktoken google-genai google-generativeai stripe \
        2>&1 | tail -3
    echo "$REQS_HASH" > .requirements_hash
    ok "Dependencies installed"
else
    ok "Python dependencies up to date"
fi

cd "$SCRIPT_DIR"

# ── Frontend Setup ────────────────────────────────────────────────────────────
info "Setting up frontend..."

# Write frontend .env so CRA picks up REACT_APP_BACKEND_URL at dev build time
echo "REACT_APP_BACKEND_URL=http://localhost:${BACKEND_PORT}" > frontend/.env

cd frontend

# Check if node_modules exists (quick heuristic for installed deps)
if [[ ! -d node_modules ]]; then
    info "Installing frontend dependencies..."
    if [[ -n "$YARN" ]]; then
        $YARN install --frozen-lockfile 2>/dev/null || $YARN install
    else
        $NPM install --legacy-peer-deps --no-audit --no-fund
    fi
    ok "Frontend dependencies installed"
else
    ok "Frontend dependencies up to date"
fi

cd "$SCRIPT_DIR"

# ── Start Backend ─────────────────────────────────────────────────────────────
info "Starting backend on port ${BACKEND_PORT}..."
mkdir -p .logs

cd backend
source .venv/bin/activate

# Start uvicorn in background
uvicorn server:app \
    --host 0.0.0.0 \
    --port "$BACKEND_PORT" \
    --reload \
    --log-level info \
    > "${BACKEND_LOG}" 2>&1 &
BACKEND_PID=$!
cd "$SCRIPT_DIR"

# Wait for backend to be healthy (up to 30 seconds)
info "Waiting for backend to become healthy..."
for i in $(seq 1 30); do
    if curl -sf "http://localhost:${BACKEND_PORT}/api/health" >/dev/null 2>&1; then
        ok "Backend is healthy (http://localhost:${BACKEND_PORT}/api/health)"
        break
    fi
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        err "Backend died during startup. Check ${BACKEND_LOG}"
        exit 1
    fi
    sleep 1
done

# ── Start Frontend ────────────────────────────────────────────────────────────
info "Starting frontend on port ${FRONTEND_PORT}..."

cd frontend
if [[ -n "$YARN" ]]; then
    BROWSER=none PORT="$FRONTEND_PORT" $YARN start \
        > "${FRONTEND_LOG}" 2>&1 &
else
    BROWSER=none PORT="$FRONTEND_PORT" $NPM start \
        > "${FRONTEND_LOG}" 2>&1 &
fi
FRONTEND_PID=$!
cd "$SCRIPT_DIR"

# ── Wait for Frontend ─────────────────────────────────────────────────────────
info "Waiting for frontend to start..."
for i in $(seq 1 30); do
    if curl -sf "http://localhost:${FRONTEND_PORT}" >/dev/null 2>&1; then
        ok "Frontend is ready (http://localhost:${FRONTEND_PORT})"
        break
    fi
    if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
        err "Frontend died during startup. Check ${FRONTEND_LOG}"
        break
    fi
    sleep 2
done

# ── Cleanup Handler ───────────────────────────────────────────────────────────
cleanup() {
    $_CLEANED && return
    _CLEANED=true
    echo
    info "Shutting down..."
    if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null
        wait "$BACKEND_PID" 2>/dev/null
        ok "Backend stopped"
    fi
    if [[ -n "$FRONTEND_PID" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
        kill "$FRONTEND_PID" 2>/dev/null
        wait "$FRONTEND_PID" 2>/dev/null
        ok "Frontend stopped"
    fi
    info "Goodbye!"
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# ── Show URLs & Follow Logs ───────────────────────────────────────────────────
echo ""
echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  LectureMind AI is running${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
echo -e "  Frontend:  ${CYAN}http://localhost:${FRONTEND_PORT}${NC}"
echo -e "  Backend:   ${CYAN}http://localhost:${BACKEND_PORT}${NC}"
echo -e "  API Docs:  ${CYAN}http://localhost:${BACKEND_PORT}/docs${NC}"
echo -e "  Health:    ${CYAN}http://localhost:${BACKEND_PORT}/api/health${NC}"
echo ""
echo -e "  ${YELLOW}Press Ctrl+C to stop everything${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
echo ""

# Tail both logs interleaved with labels — follow until Ctrl+C
# Use named pipes for clean interleaving
tail -qf \
    --retry \
    -n 0 \
    --pid="$BACKEND_PID" \
    "$BACKEND_LOG" 2>/dev/null | sed "s/^/[backend]  /" &
TAIL_BE=$!

tail -qf \
    --retry \
    -n 0 \
    --pid="$FRONTEND_PID" \
    "$FRONTEND_LOG" 2>/dev/null | sed "s/^/[frontend] /" &
TAIL_FE=$!

# Wait for either process to exit
while true; do
    if ! kill -0 "$BACKEND_PID" 2>/dev/null && ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
        info "Both processes have exited."
        break
    fi
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        warn "Backend exited unexpectedly. Check ${BACKEND_LOG}"
    fi
    if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
        warn "Frontend exited unexpectedly. Check ${FRONTEND_LOG}"
    fi
    sleep 2
done

# Clean up tail processes
kill "$TAIL_BE" "$TAIL_FE" 2>/dev/null || true
wait 2>/dev/null
