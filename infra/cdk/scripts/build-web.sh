#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
FRONTEND_DIR="${ROOT_DIR}/frontend"
OUTPUT_DIR="${ROOT_DIR}/infra/cdk/build/web"

cd "${FRONTEND_DIR}"

echo "==> Installing frontend dependencies (npm ci)..."
npm ci

echo "==> Building Next.js standalone application..."
npm run build

echo "==> Detecting standalone server.js..."
SERVER_JS=$(find .next/standalone -name server.js -not -path "*/node_modules/*" | head -n 1 || true)
if [ -z "${SERVER_JS}" ] || [ ! -f "${SERVER_JS}" ]; then
  echo "ERROR: Standalone server.js not found under .next/standalone. Ensure output: 'standalone' is set in next.config.mjs." >&2
  exit 1
fi

echo "Found standalone entrypoint: ${SERVER_JS}"
APP_SUBDIR="$(dirname "${SERVER_JS}")"
REL_APP_SUBDIR="${APP_SUBDIR#.next/standalone/}"
if [ "${REL_APP_SUBDIR}" = ".next/standalone" ]; then
  REL_APP_SUBDIR=""
fi

echo "==> Assembling build bundle in ${OUTPUT_DIR}..."
rm -rf "${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}"

cp -R .next/standalone/* "${OUTPUT_DIR}/"

if [ -n "${REL_APP_SUBDIR}" ] && [ -d "${OUTPUT_DIR}/${REL_APP_SUBDIR}" ]; then
  TARGET_APP_DIR="${OUTPUT_DIR}/${REL_APP_SUBDIR}"
else
  TARGET_APP_DIR="${OUTPUT_DIR}"
fi

mkdir -p "${TARGET_APP_DIR}/.next"
cp -R .next/static "${TARGET_APP_DIR}/.next/static"

if [ -d "public" ]; then
  cp -R public "${TARGET_APP_DIR}/public"
fi

FINAL_SERVER_JS="${TARGET_APP_DIR}/server.js"
if [ ! -f "${FINAL_SERVER_JS}" ]; then
  echo "ERROR: Assembled bundle is missing server.js at ${FINAL_SERVER_JS}" >&2
  exit 1
fi

echo "==> Web bundle successfully assembled!"
echo "Final server.js: ${FINAL_SERVER_JS}"
BUNDLE_SIZE=$(du -sh "${OUTPUT_DIR}" | cut -f1)
echo "Total bundle size: ${BUNDLE_SIZE}"
