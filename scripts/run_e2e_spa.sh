#!/usr/bin/env bash
set -euo pipefail

# Hermetic Playwright E2E runner for the shadow SPA (web/) served at /next.
#
# Builds web/ (Vite) so it can be mounted, then runs the specs in tests/e2e_spa
# against a real single-worker gunicorn instance. The SPA's /api calls are
# mocked at the browser route layer, so no live Bedrock/Redis is needed.
#
# Usage:
#   scripts/run_e2e_spa.sh
#
# Env:
#   E2E_HOST/E2E_PORT   where the local backend listens (default 127.0.0.1:8000)
#   E2E_WORKERS         gunicorn --workers count (default 1)

cd "$(dirname "$0")/.."
ROOT="$(pwd)"

HOST="${E2E_HOST:-127.0.0.1}"
PORT="${E2E_PORT:-8000}"
WORKERS="${E2E_WORKERS:-1}"
BASE="http://${HOST}:${PORT}"

echo "== PreConsult SPA Playwright E2E (backend=${BASE}, workers=${WORKERS}) =="

echo "--- building web/ (Vite) ---"
(
  cd web
  npm ci --no-audit --no-fund
  npm run build
)

echo "--- ensure Playwright browsers + system deps ---"
"${ROOT}/.venv/bin/python" -m playwright install chromium >/dev/null 2>&1 || true

echo "--- building Reflex shell (so / and its static mount are present) ---"
# The SPA app imports the Reflex module; the backend also serves /. Building the
# Reflex frontend keeps the full stack realistic (and applies the socket patch).
TPL="${ROOT}/.venv/lib/python3.11/site-packages/reflex_base/.templates/web/utils/state.js"
if [ -f "$TPL" ]; then
  cp "${ROOT}/reflex_app/web_utils/state.js" "$TPL"
fi
(
  cd reflex_app
  REFLEX_API_URL="${BASE}" REFLEX_TRANSPORT="${REFLEX_TRANSPORT:-websocket}" \
    BUILD_MODE=true "${ROOT}/.venv/bin/python" -m reflex export --frontend-only --no-zip
)

echo "--- running specs ---"
E2E_HOST="${HOST}" E2E_PORT="${PORT}" E2E_WORKERS="${WORKERS}" \
  "${ROOT}/.venv/bin/python" -m pytest tests/e2e_spa \
    -v \
    --strict-markers \
    -m e2e \
    "$@"

echo "== SPA E2E passed (workers=${WORKERS}) =="
