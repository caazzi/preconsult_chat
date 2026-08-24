# --- Stage 1: Build Frontend ---
FROM python:3.11-slim-bookworm AS builder

# Install Node.js for Reflex frontend compilation
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs unzip && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/
ENV PATH="/uv/bin:$PATH"

# Copy the entire project for build (needed so `uv sync` can install the app
# wheel from source).
COPY . .

# Install dependencies and bake the app wheel into the venv.
# Installing the project here (NOT --no-install-project) means the runtime
# `uv run` never rebuilds/re-syncs the wheel, eliminating the ~40s of
# `Building preconsult @ file:///app` CPU work that happened on every cold start.
RUN uv sync --frozen

# Apply the tracked reflex-client socket-replay patch onto the reflex-base web
# template so `reflex export` compiles it into the frontend bundle. Without
# this, a fresh .web (re-materialized from the installed reflex package on each
# clean build) would drop the dead-session event-replay fix. Keep state.js in
# sync with the reflex-base template for the pinned reflex version (0.9.8.post1).
RUN cp /app/reflex_app/web_utils/state.js \
       /app/.venv/lib/python3.11/site-packages/reflex_base/.templates/web/utils/state.js

# Build Reflex frontend
WORKDIR /app/reflex_app
ARG API_URL="https://pre-consult.org"
ENV API_URL=$API_URL
# Baked into the client's env.json (TRANSPORT) during export. Must match the
# server-side config.transport at runtime (see final stage). Defaults to
# `polling` for Cloud Run (see rxconfig.py), overridable via REFLEX_TRANSPORT.
ARG REFLEX_TRANSPORT="polling"
ENV REFLEX_TRANSPORT=$REFLEX_TRANSPORT
RUN npm install -g bun && \
    BUILD_MODE=true uv run reflex export --frontend-only --no-zip

# --- Stage 2: Final Production Image ---
FROM python:3.11-slim-bookworm

WORKDIR /app

# Install uv for the final runtime too (cleaner for running scripts)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uv/bin/
ENV PATH="/uv/bin:$PATH"

# Copy the built project and venv from builder
COPY --from=builder /app /app

# Set up environment.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app/src" \
    REFLEX_TRANSPORT="websocket"

# Expose ports (Reflex default is 8000 for backend, 3000 for frontend, 
# but in prod it's consolidated or served differently)
# We will run reflex in prod mode which binds to 8080 (Cloud Run default)
EXPOSE 8080
# Set up non-root user for security
RUN groupadd -r preconsult && useradd -r -g preconsult -m preconsult && \
    chown -R preconsult:preconsult /app

USER preconsult
WORKDIR /app/reflex_app

# Run production backend using Gunicorn with a SINGLE Uvicorn worker per
# instance. Reflex's Socket.IO/Engine.IO session store is in-memory per worker
# (no `redis_url` — see rxconfig.py, which keeps the free-tier serverless Redis
# quota for real-user sessions). With >1 workers, long-polling requests for one
# browser round-robin across workers, each with its own in-memory session, so a
# poll hitting the "wrong" worker is rejected with `400 "Invalid session <sid>"`
# and the UI fails to advance ("Cannot connect to server: xhr post error").
# Cloud Run `--session-affinity` pins a client to one instance, so a single
# worker per instance reliably owns the whole socket session; horizontal
# scaling happens at the instance level (uvicorn's asyncio loop serves many
# concurrent connections).
#
# IMPORTANT: invoke gunicorn DIRECTLY from the baked venv (/app/.venv/bin) —
# NOT via `uv run`. Running `uv run gunicorn` (with or without UV_NO_SYNC) makes
# the worker drop Cloud Run proxy connections with "Invalid HTTP request
# received" / 502 protocol errors, while the identical command serves 200 on
# localhost and the direct venv invocation serves cleanly behind the proxy.
# `uv sync --frozen` in the builder bakes the project + venv, so startup stays
# fast (seconds) with no runtime rebuild. 'exec' ensures signals (like SIGTERM
# for scale-down) correctly reach gunicorn.
CMD ["sh", "-c", "exec /app/.venv/bin/gunicorn preconsult.preconsult:api --bind 0.0.0.0:${PORT:-8080} --worker-class uvicorn.workers.UvicornWorker --workers 1 --threads 4"]
