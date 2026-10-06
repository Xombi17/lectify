#!/usr/bin/env bash
# Lectify local dev — backend + workers + frontend in one terminal.
#
# Usage:
#   ./dev.sh            Start everything (SQLite + local storage, no Docker/AWS)
#   ./dev.sh --help     Show this help
#
# What it starts:
#   backend   FastAPI on :8001  (SQLite file DB, local file storage, SQLite queue)
#   workers   Transcribe + AI materials + embedding pipeline (same DB + queue)
#   frontend  Next.js (webpack) on :3000, proxies /api to the backend
#
# Logs: .logs/backend.log, .logs/workers.log, .logs/frontend.log
# Stop everything: Ctrl+C
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    sed -n '2,14p' "$0"
    exit 0
fi

# ── Shared environment (local dev: zero external services) ──────────────────
export ENV=dev
export DATABASE_BACKEND=postgres
export DATABASE_URL="sqlite+aiosqlite:///${ROOT}/backend/lecturemind.db"
export STORAGE_BACKEND=local
export STORAGE_LOCAL_DIR="${ROOT}/backend/storage_data"
export JWT_SECRET="${JWT_SECRET:-change-me-dev-local}"
export CORS_ORIGINS="${CORS_ORIGINS:-http://localhost:3000}"
export DB_AUTO_CREATE=true
# SQLite queue so the API and worker processes share one queue file.
# ("memory" is per-process; "sqs" is for deployed environments.)
export QUEUE_BACKEND="${QUEUE_BACKEND:-sqlite}"

BACKEND_PORT="${PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
export DEV_BACKEND_URL="http://localhost:${BACKEND_PORT}"

mkdir -p .logs
BACKEND_LOG="$ROOT/.logs/backend.log"
WORKERS_LOG="$ROOT/.logs/workers.log"
FRONTEND_LOG="$ROOT/.logs/frontend.log"

# ── Preconditions ─────────────────────────────────────────────────────────────
command -v python3 &>/dev/null || { echo "python3 is required." >&2; exit 1; }
[[ -x backend/.venv/bin/python ]] || {
    echo "backend/.venv not found. Create it first:" >&2
    echo "  cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
    exit 1
}
command -v node &>/dev/null || { echo "node is required for the frontend." >&2; exit 1; }
[[ -d frontend/node_modules ]] || {
    echo "frontend/node_modules missing. Install first: cd frontend && npm install" >&2
    exit 1
}
for port in "$BACKEND_PORT" "$FRONTEND_PORT"; do
    if (echo >/dev/tcp/localhost/$port) &>/dev/null; then
        echo "Port $port is already in use. Stop that process first." >&2
        exit 1
    fi
done

# ── Cleanup ───────────────────────────────────────────────────────────────────
PIDS=""
cleanup() {
    echo; echo "Stopping..."
    # shellcheck disable=SC2086
    for pid in $PIDS; do kill "$pid" 2>/dev/null || true; done
    wait 2>/dev/null || true
    echo "Stopped."
}
trap cleanup INT TERM EXIT

# ── Backend ───────────────────────────────────────────────────────────────────
echo "[1/3] Starting backend on :$BACKEND_PORT ..."
cd backend
ENV="$ENV" DATABASE_BACKEND="$DATABASE_BACKEND" DATABASE_URL="$DATABASE_URL" \
STORAGE_BACKEND="$STORAGE_BACKEND" STORAGE_LOCAL_DIR="$STORAGE_LOCAL_DIR" \
JWT_SECRET="$JWT_SECRET" CORS_ORIGINS="$CORS_ORIGINS" DB_AUTO_CREATE="$DB_AUTO_CREATE" \
QUEUE_BACKEND="$QUEUE_BACKEND" \
    .venv/bin/python -m uvicorn server:app --host 0.0.0.0 --port "$BACKEND_PORT" \
    > "$BACKEND_LOG" 2>&1 &
PIDS="$PIDS $!"
cd "$ROOT"

echo "      Waiting for backend health..."
for _ in $(seq 1 60); do
    if curl -sf -m 3 "http://localhost:${BACKEND_PORT}/api/health" >/dev/null 2>&1; then
        echo "      Backend healthy."
        break
    fi
    sleep 2
done
curl -sf -m 3 "http://localhost:${BACKEND_PORT}/api/health" >/dev/null 2>&1 || {
    echo "Backend failed to start. Tail of $BACKEND_LOG:" >&2
    tail -20 "$BACKEND_LOG" >&2
    exit 1
}

# ── Workers ───────────────────────────────────────────────────────────────────
echo "[2/3] Starting workers (transcribe + AI + embed) ..."
cd backend
ENV="$ENV" DATABASE_BACKEND="$DATABASE_BACKEND" DATABASE_URL="$DATABASE_URL" \
STORAGE_BACKEND="$STORAGE_BACKEND" STORAGE_LOCAL_DIR="$STORAGE_LOCAL_DIR" \
JWT_SECRET="$JWT_SECRET" QUEUE_BACKEND="$QUEUE_BACKEND" \
    .venv/bin/python -m workers all \
    > "$WORKERS_LOG" 2>&1 &
PIDS="$PIDS $!"
cd "$ROOT"
sleep 5
kill -0 $(echo $PIDS | awk '{print $2}') 2>/dev/null || {
    echo "Workers exited immediately. Tail of $WORKERS_LOG:" >&2
    tail -20 "$WORKERS_LOG" >&2
    exit 1
}
echo "      Workers running."

# ── Frontend ──────────────────────────────────────────────────────────────────
echo "[3/3] Starting frontend on :$FRONTEND_PORT (webpack; first compile is slow) ..."
cd frontend
PORT="$FRONTEND_PORT" DEV_BACKEND_URL="$DEV_BACKEND_URL" npx next dev --webpack \
    > "$FRONTEND_LOG" 2>&1 &
PIDS="$PIDS $!"
cd "$ROOT"

echo "      Waiting for frontend..."
for _ in $(seq 1 60); do
    if curl -sf -m 3 "http://localhost:${FRONTEND_PORT}/" >/dev/null 2>&1; then
        echo "      Frontend ready."
        break
    fi
    sleep 2
done

# ── Done ──────────────────────────────────────────────────────────────────────
echo
echo "Lectify is running:"
echo "  Frontend:  http://localhost:${FRONTEND_PORT}"
echo "  Backend:   http://localhost:${BACKEND_PORT}  (docs: /docs)"
echo "  Logs:      .logs/backend.log .logs/workers.log .logs/frontend.log"
echo "  Press Ctrl+C to stop everything."
echo
trap 'cleanup; trap - EXIT; exit 0' INT TERM
trap '' EXIT
tail -F -n 0 "$BACKEND_LOG" "$WORKERS_LOG" "$FRONTEND_LOG" 2>/dev/null &
TAIL_PID=$!
PIDS="$PIDS $TAIL_PID"
wait
