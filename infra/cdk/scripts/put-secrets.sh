#!/usr/bin/env bash
# Create SSM SecureString params /lectify/{JWT_SECRET,GROQ_API_KEY,GEMINI_API_KEY,DEEPGRAM_API_KEY,NAGA_AI_API_KEY,NIM_API_KEY,CLOUDFLARE_*}.
# Values come from env vars of the same name, else a silent prompt. Never printed.
# Usage: put-secrets.sh [--overwrite] [--help]
#   --overwrite  replace parameters that already exist (default: skip existing)
set -euo pipefail
OW=""
for a in "$@"; do
  case "$a" in
    --help|-h) sed -n '2,6p' "$0"; exit 0 ;;
    --overwrite) OW="--overwrite" ;;
    *) echo "unknown option: $a" >&2; exit 1 ;;
  esac
done
for KEY in JWT_SECRET GROQ_API_KEY GEMINI_API_KEY DEEPGRAM_API_KEY NAGA_AI_API_KEY NIM_API_KEY CLOUDFLARE_ACCOUNT_ID CLOUDFLARE_API_TOKEN; do
  NAME="/lectify/$KEY"
  if [ -z "$OW" ] && aws ssm get-parameter --name "$NAME" >/dev/null 2>&1; then
    echo "SKIP $NAME (exists; use --overwrite)"; continue
  fi
  VAL="${!KEY:-}"
  if [ -z "$VAL" ]; then read -r -s -p "Enter value for $KEY: " VAL; echo >&2; fi
  [ -n "$VAL" ] || { echo "empty value for $KEY" >&2; exit 1; }
  aws ssm put-parameter --name "$NAME" --value "$VAL" --type SecureString $OW >/dev/null
  echo "OK   $NAME (SecureString)"
done
