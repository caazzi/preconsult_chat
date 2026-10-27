#!/usr/bin/env bash
set -euo pipefail

# Hermetic Playwright E2E runner for the React SPA (web/), which is the canonical
# document served at / by the Python host (`preconsult.host:app`).
#
# Builds web/ (Vite) so the host can mount the bundle at /, then runs the specs
# in tests/e2e_spa. The spec's `backend` fixture boots a real single-worker
# gunicorn instance of `preconsult.host:app` from the repo root, and the SPA's
# /api calls are mocked at the browser route layer, so no live Vertex AI or
# serverless Redis is needed.
#
# Usage:
#   scripts/run_e2e_spa.sh
#
# Env:
#   E2E_HOST/E2E_PORT   where the local backend listens (default 127.0.0.1:8000)
#   E2E_WORKERS         gunicorn --workers count (default 1)
#   E2E_GUNICORN        gunicorn executable (default: .venv/bin/gunicorn)

cd "$(dirname "$0")/.."
ROOT="$(pwd)"

HOST="${E2E_HOST:-127.0.0.1}"
PORT="${E2E_PORT:-8000}"
WORKERS="${E2E_WORKERS:-1}"
BASE="http://${HOST}:${PORT}"

echo "== PreConsult SPA Playwright E2E (backend=${BASE}, workers=${WORKERS}) =="

# 1. Build the SPA bundle. The host serves web/dist at / and its documents
#    (legal pages) from the repo, so the sources must be present before pytest
#    starts the backend fixture.
echo "--- building web/ (Vite) ---"
(
  cd web
  npm ci --no-audit --no-fund
  npm run build
)

# 2. Ensure Playwright browsers are present (no-op if already installed).
echo "--- ensure Playwright browsers + system deps ---"
"${ROOT}/.venv/bin/python" -m playwright install chromium >/dev/null 2>&1 || true

# 3. Run the specs from the repo root. The backend fixture boots
#    `preconsult.host:app` itself (cwd = repo root), so pytest is all that needs
#    to run here.
echo "--- running specs ---"
E2E_HOST="${HOST}" E2E_PORT="${PORT}" E2E_WORKERS="${WORKERS}" \
  "${ROOT}/.venv/bin/python" -m pytest tests/e2e_spa \
    -v \
    --strict-markers \
    -m e2e \
    "$@"

echo "== SPA E2E passed (workers=${WORKERS}) =="
