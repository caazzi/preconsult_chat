# --- Stage 1: Build Frontend ---
FROM python:3.11-slim-bookworm AS builder

# Node.js builds the SPA in web/ (see the frontend stage below)
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

# --- Stage 1b: Build the shadow SPA (web/) ---------------------------------
# The React rewrite is served at /next from the SAME image (see preconsult.py).
# Vite's base is /next/, so emitted asset URLs need no extra config. The web/
# sources (incl. web/scripts and web/package-lock.json) are kept by
# .dockerignore negations; node_modules/ is installed fresh here.
WORKDIR /app/web
RUN npm ci --no-audit --no-fund
# Sync the generated contracts from the Python source of truth, then build.
RUN node scripts/sync-contracts.mjs && npm run build
# Drop the (large) node_modules + web sources from the build context copy: only
# web/dist is needed at runtime, and COPY --from=builder copies all of /app.
RUN rm -rf /app/web/node_modules /app/web/src /app/web/scripts

# The only frontend build is web/ (above); there is no second frontend host.
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
    PYTHONPATH="/app/src"

# Cloud Run routes to $PORT (8080 by default).
EXPOSE 8080
# Set up non-root user for security
RUN groupadd -r preconsult && useradd -r -g preconsult -m preconsult && \
    chown -R preconsult:preconsult /app

USER preconsult
WORKDIR /app

# A SINGLE Uvicorn worker per instance, deliberately, for now. Sessions live in
# Redis; the only per-worker state is the best-effort Redis-outage fallback and
# the rate-limit fallback, so this is a resilience/latency choice rather than a
# correctness requirement. Raising the worker count is a separate, measured
# change (see AGENTS.md) — do not bump it here.
#
# IMPORTANT: invoke gunicorn DIRECTLY from the baked venv (/app/.venv/bin) —
# NOT via `uv run`. Running `uv run gunicorn` (with or without UV_NO_SYNC) makes
# the worker drop Cloud Run proxy connections with "Invalid HTTP request
# received" / 502 protocol errors, while the identical command serves 200 on
# localhost and the direct venv invocation serves cleanly behind the proxy.
# `uv sync --frozen` in the builder bakes the project + venv, so startup stays
# fast (seconds) with no runtime rebuild. 'exec' ensures signals (like SIGTERM
# for scale-down) correctly reach gunicorn.
CMD ["sh", "-c", "exec /app/.venv/bin/gunicorn preconsult.main:app --bind 0.0.0.0:${PORT:-8080} --worker-class uvicorn.workers.UvicornWorker --workers 1 --threads 4"]
