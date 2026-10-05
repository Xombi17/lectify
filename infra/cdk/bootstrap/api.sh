#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

echo "==> Starting Lectify API/Web tier bootstrap..."

ensure_swap 2G
create_service_user
install_python311
install_node20

fetch_asset "${BACKEND_ASSET_BUCKET}" "${BACKEND_ASSET_KEY}" /opt/lectify/backend true
fetch_asset "${WEB_ASSET_BUCKET}" "${WEB_ASSET_KEY}" /opt/lectify/web true

make_venv /opt/lectify/venv /opt/lectify/backend/requirements.txt

write_env_file /etc/lectify/app.env <<EOF
ENV=aws
SERVICE_NAME=monolith
DATABASE_BACKEND=postgres
DB_SECRET_ARN=${DB_SECRET_ARN}
DB_HOST=${DB_HOST}
DB_PORT=${DB_PORT:-5432}
DATABASE_NAME=${DATABASE_NAME:-postgres}
DB_AUTO_CREATE=false
QUEUE_BACKEND=sqs
QUEUE_URL_TRANSCRIBE=${QUEUE_URL_TRANSCRIBE}
QUEUE_URL_MATERIALS=${QUEUE_URL_MATERIALS}
QUEUE_URL_EMBED=${QUEUE_URL_EMBED}
QUEUE_URL_DLQ=${QUEUE_URL_DLQ}
LECTURE_READY_TOPIC_ARN=${LECTURE_READY_TOPIC_ARN}
STORAGE_BACKEND=s3
OBJECT_STORAGE_BUCKET=${OBJECT_STORAGE_BUCKET}
S3_BUCKET=${OBJECT_STORAGE_BUCKET}
AWS_REGION=${AWS_REGION}
SSM_PREFIX=${SSM_PREFIX:-/lectify/}
CORS_ORIGINS=${ALB_ORIGIN}
APP_URL=${ALB_ORIGIN}
PROMETHEUS_ENABLED=false
SLACK_SUMMARY_ENABLED=false
DAILY_SUMMARY_ENABLED=false
EOF

install_units "${SCRIPT_DIR}/systemd"

echo "Starting lectify-api and lectify-web services..."
systemctl enable --now lectify-api lectify-web

echo "Verifying local service health on ports 8000 and 3000..."
for i in $(seq 1 40); do
  if curl -fsS http://localhost:8000/healthz >/dev/null 2>&1 && curl -fsS http://localhost:3000/healthz >/dev/null 2>&1; then
    echo "API and Web tiers healthy!"
    exit 0
  fi
  sleep 3
done

echo "ERROR: Timed out waiting for API and Web services to become healthy." >&2
systemctl status lectify-api --no-pager || true
systemctl status lectify-web --no-pager || true
journalctl -u lectify-api -u lectify-web --no-pager -n 50 || true
exit 1
