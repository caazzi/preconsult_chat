#!/usr/bin/env bash
set -euo pipefail

# Hermetic Playwright E2E runner.
#
# Builds the Reflex frontend pointed at a local backend, then runs the browser
# specs in tests/e2e against a real single-worker gunicorn instance. The LLM/
# Redis API endpoints are mocked at the browser (route) layer by the specs, so
# this needs NO live Vertex AI or serverless Redis.
#
# Usage:
#   scripts/run_e2e.sh                 # default (--workers 1, the fixed config)
#   E2E_WORKERS=2 scripts/run_e2e.sh   # reproduce the "Invalid session" bug
#
# Env:
#   E2E_HOST/E2E_PORT   where the local backend listens (default 127.0.0.1:8000)
#   E2E_WORKERS         gunicorn --workers count (default 1)
#   UV                 path to uv (default resolves on PATH)
#
# cd to repo root so the venv + reflex_app are found.
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
UV="${UV:-uv}"

HOST="${E2E_HOST:-127.0.0.1}"
PORT="${E2E_PORT:-8000}"
WORKERS="${E2E_WORKERS:-1}"
BASE="http://${HOST}:${PORT}"

echo "== PreConsult Playwright E2E (backend=${BASE}, workers=${WORKERS}) =="

# 1. Apply the tracked reflex-client socket-replay patch onto the installed
#    reflex-base template (the live .web may otherwise be a re-materialized,
#    unpatched copy). Must mirror the Dockerfile hook.
TPL="${ROOT}/.venv/lib/python3.11/site-packages/reflex_base/.templates/web/utils/state.js"
if [ -f "$TPL" ]; then
  cp "${ROOT}/reflex_app/web_utils/state.js" "$TPL"
  echo "--- applied reflex-client socket-replay patch ---"
else
  echo "!! reflex-base template not found at $TPL; export below will use the unpatched client"
fi

# 2. Build the frontend for the local backend origin so the baked client's
#    EVENT/PING/API URLs point here (not at pre-consult.org).
echo "--- building frontend for ${BASE} ---"
(
  cd reflex_app
  REFLEX_API_URL="${BASE}" REFLEX_TRANSPORT="${REFLEX_TRANSPORT:-polling}" \
    BUILD_MODE=true "${ROOT}/.venv/bin/python" -m reflex export --frontend-only --no-zip
)

# 3. Ensure Playwright browsers are present (no-op if already installed).
echo "--- ensure Playwright system deps + browser ---"
"${ROOT}/.venv/bin/python" -m playwright install chromium >/dev/null 2>&1 || true

# 3. Run the specs. The backend fixture inside tests/e2e/conftest.py boots the
#    gunicorn server itself, so pytest is all that needs to run here.
echo "--- running specs ---"
E2E_HOST="${HOST}" E2E_PORT="${PORT}" E2E_WORKERS="${WORKERS}" \
  "${ROOT}/.venv/bin/python" -m pytest tests/e2e \
    -v \
    --strict-markers \
    -m e2e \
    "$@"

echo "== E2E passed (workers=${WORKERS}) =="
