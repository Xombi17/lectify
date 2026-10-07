#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# LectureMind AI — Single-Command Launcher
# ═══════════════════════════════════════════════════════════════════════════════
# Usage:
#   ./run.sh                  Start backend + workers + frontend for local dev
#   ./run.sh --docker         Start full stack via docker compose
#   ./run.sh --help           Show this help
#
# Default mode (no flags): SQLite + local storage + SQLite queue,
# backend on :8001, frontend on :3000. Zero external services required.
# AI features need keys in backend/.env (GEMINI_API_KEY).
#
# Requirements: python3 (with backend/.venv), node/npm, ffmpeg (for chunking).
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

BACKEND_PORT="${PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
BACKEND_LOG="${SCRIPT_DIR}/.logs/backend.log"
WORKERS_LOG="${SCRIPT_DIR}/.logs/workers.log"
FRONTEND_LOG="${SCRIPT_DIR}/.logs/frontend.log"
BACKEND_PID=""
WORKERS_PID=""
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
    sed -n '3,13p' "$0"
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
        if [[ -f .env.example ]]; then
            cp .env.example .env
            warn ".env created from .env.example — edit it with GEMINI_API_KEY and JWT_SECRET."
        else
            err "No .env file. Create one with JWT_SECRET and GEMINI_API_KEY first."
            exit 1
        fi
    fi
    info "Starting full stack with Docker Compose..."
    exec docker compose up --build
fi

# ── Prerequisites ─────────────────────────────────────────────────────────────
info "Checking prerequisites..."

command -v python3 &>/dev/null || { err "python3 is required."; exit 1; }
[[ -x backend/.venv/bin/python ]] || {
    err "backend/.venv not found. Create it first:"
    err "  cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
}
command -v npm &>/dev/null || { err "npm is required for the frontend."; exit 1; }
[[ -d frontend/node_modules ]] || {
    err "frontend/node_modules missing. Install first: cd frontend && npm install"
    exit 1
}
command -v ffmpeg &>/dev/null \
    && ok "ffmpeg found" \
    || warn "ffmpeg not found — long lecture chunking will be unavailable"

for port in "$BACKEND_PORT" "$FRONTEND_PORT"; do
    if (echo >/dev/tcp/localhost/$port) &>/dev/null; then
        err "Port $port is already in use. Stop that process first."
        exit 1
    fi
done
ok "Prerequisites satisfied"

# ── Environment (local dev: zero external services) ───────────────────────────
# NOTE: there is no root .env.example on purpose — AI keys live in
# backend/.env (loaded by the backend itself). Everything below just works.
export ENV=dev
export DATABASE_BACKEND=postgres
export DATABASE_URL="sqlite+aiosqlite:///${SCRIPT_DIR}/backend/lecturemind.db"
export STORAGE_BACKEND=local
export STORAGE_LOCAL_DIR="${SCRIPT_DIR}/backend/storage_data"
export JWT_SECRET="${JWT_SECRET:-change-me-dev-local}"
export CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:3000}"
export DB_AUTO_CREATE=true
# SQLite queue so the API and worker processes share one queue file.
# ("memory" is per-process; "sqs" is for deployed environments.)
export QUEUE_BACKEND="${QUEUE_BACKEND:-sqlite}"
export DEV_BACKEND_URL="http://localhost:${BACKEND_PORT}"

mkdir -p .logs

# ── Cleanup Handler ───────────────────────────────────────────────────────────
cleanup() {
    $_CLEANED && return
    _CLEANED=true
    echo
    info "Shutting down..."
    for pid in "$BACKEND_PID" "$WORKERS_PID" "$FRONTEND_PID"; do
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
        fi
    done
    wait 2>/dev/null || true
    ok "All processes stopped. Goodbye!"
    exit 0
}
trap cleanup SIGINT SIGTERM
trap 'cleanup' EXIT

# ── Start Backend ─────────────────────────────────────────────────────────────
info "[1/3] Starting backend on port ${BACKEND_PORT}..."
cd backend
./.venv/bin/python -m uvicorn server:app \
    --host 0.0.0.0 \
    --port "$BACKEND_PORT" \
    --log-level info \
    > "${BACKEND_LOG}" 2>&1 &
BACKEND_PID=$!
cd "$SCRIPT_DIR"

info "Waiting for backend to become healthy..."
healthy=false
for _ in $(seq 1 45); do
    if curl -sf "http://localhost:${BACKEND_PORT}/api/health" >/dev/null 2>&1; then
        healthy=true
        break
    fi
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
        err "Backend died during startup. Tail of ${BACKEND_LOG}:"
        tail -20 "${BACKEND_LOG}" >&2
        exit 1
    fi
    sleep 2
done
$healthy || { err "Backend never became healthy. Check ${BACKEND_LOG}"; exit 1; }
ok "Backend is healthy (http://localhost:${BACKEND_PORT}/api/health)"

# ── Start Workers ─────────────────────────────────────────────────────────────
info "[2/3] Starting workers (transcribe + AI materials + embed)..."
cd backend
./.venv/bin/python -m workers all \
    > "${WORKERS_LOG}" 2>&1 &
WORKERS_PID=$!
cd "$SCRIPT_DIR"
sleep 5
kill -0 "$WORKERS_PID" 2>/dev/null || {
    err "Workers exited immediately. Tail of ${WORKERS_LOG}:"
    tail -20 "${WORKERS_LOG}" >&2
    exit 1
}
ok "Workers running."

# ── Start Frontend ────────────────────────────────────────────────────────────
# NOTE: webpack, not Turbopack — Turbopack dev panics on this repo's
# dual lockfile layout ("inferred workspace root" crash loop).
info "[3/3] Starting frontend on port ${FRONTEND_PORT} (first compile is slow)..."
cd frontend
PORT="$FRONTEND_PORT" DEV_BACKEND_URL="$DEV_BACKEND_URL" npx next dev --webpack \
    > "${FRONTEND_LOG}" 2>&1 &
FRONTEND_PID=$!
cd "$SCRIPT_DIR"

info "Waiting for frontend to start..."
for _ in $(seq 1 45); do
    if curl -sf "http://localhost:${FRONTEND_PORT}/" >/dev/null 2>&1; then
        ok "Frontend is ready (http://localhost:${FRONTEND_PORT})"
        break
    fi
    if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
        err "Frontend died during startup. Check ${FRONTEND_LOG}"
        break
    fi
    sleep 2
done

# ── Show URLs & Follow Logs ───────────────────────────────────────────────────
echo ""
echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  LectureMind AI is running${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
echo -e "  Frontend:  ${CYAN}http://localhost:${FRONTEND_PORT}${NC}"
echo -e "  Backend:   ${CYAN}http://localhost:${BACKEND_PORT}${NC}"
echo -e "  API Docs:  ${CYAN}http://localhost:${BACKEND_PORT}/docs${NC}"
echo -e "  Health:    ${CYAN}http://localhost:${BACKEND_PORT}/api/health${NC}"
echo -e "  Logs:      ${CYAN}.logs/backend.log .logs/workers.log .logs/frontend.log${NC}"
echo ""
echo -e "  ${YELLOW}Press Ctrl+C to stop everything${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
echo ""

trap - EXIT
trap cleanup SIGINT SIGTERM
tail -F -n 0 "$BACKEND_LOG" "$WORKERS_LOG" "$FRONTEND_LOG" 2>/dev/null &
wait
