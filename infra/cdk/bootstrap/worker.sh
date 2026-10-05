#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

echo "==> Starting Lectify Worker tier bootstrap..."

ensure_swap 2G
create_service_user
install_python311

fetch_asset "${BACKEND_ASSET_BUCKET}" "${BACKEND_ASSET_KEY}" /opt/lectify/backend true

echo "Fetching vendored ffmpeg archive..."
FFMPEG_ARCHIVE="/tmp/ffmpeg-release-amd64-static.tar.xz"
fetch_asset "${FFMPEG_ASSET_BUCKET}" "${FFMPEG_ASSET_KEY}" "${FFMPEG_ARCHIVE}" false

echo "Verifying ffmpeg archive checksum..."
cd /tmp
sha256sum -c "${SCRIPT_DIR}/ffmpeg.sha256"

echo "Extracting ffmpeg..."
mkdir -p /opt/lectify/ffmpeg
tar -xf "${FFMPEG_ARCHIVE}" --strip-components=1 -C /opt/lectify/ffmpeg
ln -sf /opt/lectify/ffmpeg/ffmpeg /usr/local/bin/ffmpeg
ln -sf /opt/lectify/ffmpeg/ffprobe /usr/local/bin/ffprobe
rm -f "${FFMPEG_ARCHIVE}"

echo "Running ffmpeg smoke test..."
ffmpeg -version
ffmpeg -hide_banner -loglevel error -f lavfi -i sine=frequency=440:duration=1 -ac 1 -y /tmp/smoke.wav
rm -f /tmp/smoke.wav
echo "ffmpeg smoke test passed!"

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
TRANSCRIPTION_CONCURRENCY=1
AI_CONCURRENCY=2
EMBEDDING_CONCURRENCY=2
DRAIN_TIMEOUT_SECONDS=90
PROMETHEUS_ENABLED=false
SLACK_SUMMARY_ENABLED=false
DAILY_SUMMARY_ENABLED=false
EOF

install_units "${SCRIPT_DIR}/systemd"

echo "Starting lectify-worker service..."
systemctl enable --now lectify-worker

sleep 10
if systemctl is-active --quiet lectify-worker; then
  echo "lectify-worker started successfully and is active!"
  exit 0
else
  echo "ERROR: lectify-worker failed to start." >&2
  systemctl status lectify-worker --no-pager || true
  journalctl -u lectify-worker --no-pager -n 50 || true
  exit 1
fi
