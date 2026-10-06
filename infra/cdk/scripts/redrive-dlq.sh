#!/usr/bin/env bash
# Redrive the shared DLQ back to a stage queue (Phase 16 D-11).
# Operator-run only: needs sqs Receive/Delete/Send on the DLQ ARN plus
# Send on the destination stage queue (the worker role lacks this by design).
# Usage:
#   redrive-dlq.sh [--source lectify-dlq|ARN] [--dest lectify-transcribe|ARN]
#                  [--max 10] [--force] [--region ap-southeast-2]
# After the move completes, reset ONLY lectures with nothing restored:
# do NOT call /retry for a lecture the move already restored (it would
# enqueue a SECOND transcribe job alongside the restored message).
# Call /retry ONLY for lectures with nothing restored — verify DLQ/stage
# depth zero for that lecture and no new transcribe job version first:
#   curl -X POST $API/api/lectures/{id}/retry -H "Authorization: Bearer $ADMIN_JWT"
set -euo pipefail

SOURCE="lectify-dlq"
DEST="lectify-transcribe"
MAX=10
FORCE=""
REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-ap-southeast-2}}"

while [ $# -gt 0 ]; do
  case "$1" in
    --source) SOURCE="${2:?}"; shift 2 ;;
    --dest) DEST="${2:?}"; shift 2 ;;
    --max) MAX="${2:?}"; shift 2 ;;
    --force) FORCE="1"; shift ;;
    --region) REGION="${2:?}"; shift 2 ;;
    --help|-h) sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 1 ;;
  esac
done

queue_name_of() {
  local name="$1"
  case "$name" in
    arn:aws:sqs:*) printf '%s' "${name##*:}" ;;
    *) printf '%s' "$name" ;;
  esac
}

resolve_arn() {
  local name="$1"
  case "$name" in
    arn:aws:sqs:*) printf '%s' "$name" ;;
    *)
      local url
      url="$(aws sqs get-queue-url --queue-name "$name" --region "$REGION" --query 'QueueUrl' --output text)"
      # URL form: https://sqs.<region>.amazonaws.com/<acct>/<queue>
      local acct queue
      acct="$(printf '%s' "$url" | awk -F/ '{print $(NF-1)}')"
      queue="$(printf '%s' "$url" | awk -F/ '{print $NF}')"
      printf 'arn:aws:sqs:%s:%s:%s' "$REGION" "$acct" "$queue"
      ;;
  esac
}

queue_depth() {
  local url="$1"
  aws sqs get-queue-attributes --queue-url "$url" --region "$REGION" \
    --attribute-names ApproximateNumberOfMessages \
    --query 'Attributes.ApproximateNumberOfMessages' --output text 2>/dev/null || echo "0"
}

SOURCE_ARN="$(resolve_arn "$SOURCE")"
DEST_ARN="$(resolve_arn "$DEST")"
[ -n "$SOURCE_ARN" ] || { echo "could not resolve source: $SOURCE" >&2; exit 1; }
[ -n "$DEST_ARN" ] || { echo "could not resolve dest: $DEST" >&2; exit 1; }

case "$DEST_ARN" in
  *:lectify-transcribe|*:lectify-materials|*:lectify-embed) ;;
  *) echo "dest must be one of lectify-transcribe/materials/embed (got $DEST)" >&2; exit 1 ;;
esac

SOURCE_URL="$(aws sqs get-queue-url --queue-name "$(queue_name_of "$SOURCE")" --region "$REGION" --query QueueUrl --output text 2>/dev/null || true)"
if [ -n "$SOURCE_URL" ]; then
  DEPTH="$(queue_depth "$SOURCE_URL")"
  if [ "$DEPTH" != "None" ] && [ "$DEPTH" -gt "$MAX" ] 2>/dev/null && [ -z "$FORCE" ]; then
    echo "DLQ depth $DEPTH exceeds --max $MAX; re-run with --force to proceed" >&2
    exit 1
  fi
  echo "DLQ depth: $DEPTH (max $MAX)"
fi

echo "Starting message move: $SOURCE_ARN -> $DEST_ARN"
TASK_HANDLE="$(aws sqs start-message-move-task --source-arn "$SOURCE_ARN" \
  --destination-arn "$DEST_ARN" --region "$REGION" \
  --query 'MessageMoveTaskHandle' --output text)"
echo "Move task: $TASK_HANDLE"

for _ in $(seq 1 60); do
  STATUS="$(aws sqs describe-message-move-task --message-move-task-handle "$TASK_HANDLE" \
    --region "$REGION" --query 'Status' --output text 2>/dev/null || echo UNKNOWN)"
  echo "status: $STATUS"
  case "$STATUS" in
    COMPLETED)
      echo "Redrive complete. Next, per lecture use ONE mechanism only:"
      echo "If the move restored processing for a lecture (queue depth shows the message back, lecture left dead_letter), do NOT call /retry."
      echo 'Call /retry ONLY for lectures with nothing restored (verify DLQ/stage depth and no new transcribe job version first):'
      echo '  curl -X POST "$API/api/lectures/{lecture_id}/retry" -H "Authorization: Bearer $ADMIN_JWT"'
      echo "Then confirm queue depth zero and the lecture left dead_letter."
      exit 0
      ;;
    FAILED|CANCELLED) echo "Message move $STATUS" >&2; exit 1 ;;
  esac
  sleep 10
done
echo "Timed out waiting for message move; check status manually:" >&2
echo "  aws sqs describe-message-move-task --message-move-task-handle $TASK_HANDLE" >&2
exit 1
