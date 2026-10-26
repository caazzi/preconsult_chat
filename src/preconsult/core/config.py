"""
Centralized configuration management for the PreConsult application.
"""
import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file (if it exists)
load_dotenv()

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "securemed-chat-494521")
REGION = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")

BUILD_MODE = os.environ.get("BUILD_MODE") == "true"

PRECONSULT_API_KEY = os.environ.get("PRECONSULT_API_KEY")
if not PRECONSULT_API_KEY:
    if BUILD_MODE:
        logging.warning("BUILD_MODE=true: PRECONSULT_API_KEY nao verificada. NAO use em producao.")
    else:
        raise ValueError("FATAL: PRECONSULT_API_KEY nao definida. Abortando startup.")

SENTRY_DSN = os.environ.get("SENTRY_DSN", "")

# When True, honor proxy-forwarded client-IP headers (cf-connecting-ip,
# x-forwarded-for). Only enable when requests actually reach Cloud Run through
# a trusted fronting proxy (e.g. Cloudflare). When False, client IP is taken
# from the transport layer, so spoofed headers can't bypass rate limits/quotas.
TRUST_PROXY_HEADERS = os.environ.get("TRUST_PROXY_HEADERS") == "true"

LLM_MODEL = os.environ.get("LLM_MODEL", "us.anthropic.claude-haiku-4-5-20251001-v1:0")

# AWS Bedrock region for the Claude Haiku inference calls. Bedrock is a regional
# service and Claude is NOT available in every region; a single fixed region is
# used (env-overridable). Data-residency routing (e.g. LGPD) must key on where
# the session actually is, not on UI language — a later phase concern.
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))

# Deploy revision identity. GIT_SHA is injected by CI; K_REVISION is Cloud Run's
# own revision id at runtime. Kept PHI-free and included in every structured log
# event so "which deployed build produced this outcome" is answerable in logs,
# not just in Sentry. Mirrors the Sentry `release` in main.py.
REPOSITORY_REVISION = os.environ.get("GIT_SHA") or os.environ.get("K_REVISION") or "dev"

# --- Session cookie (per-session auth) -------------------------------------
# A signed, HttpOnly session cookie authenticates a browser's ephemeral session.
# The cookie stores only an opaque, signed *session id* — never health data — so
# it does not alter the zero-persistence posture. It is a session cookie (no
# Max-Age), so the browser discards it on close; the server-side 30-minute TTL is
# the real lifetime bound.
SESSION_SECRET = os.environ.get("SESSION_SECRET")
if not SESSION_SECRET:
    if BUILD_MODE:
        logging.warning("BUILD_MODE=true: SESSION_SECRET nao verificada. NAO use em producao.")
        SESSION_SECRET = "build-mode-insecure-session-secret"
    else:
        raise ValueError("FATAL: SESSION_SECRET nao definida. Abortando startup.")

SESSION_COOKIE_NAME = "preconsult_session"
# Secure must be enabled in production (HTTPS). Default to True; local dev over
# plain HTTP can opt out with SESSION_COOKIE_SECURE=false.
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "true").lower() != "false"

# Public session bootstrap. When true, POST /api/session/init may be called
# without a credential and mints the session cookie that authenticates every
# other route. Default false: the bootstrap stays behind auth until per-IP
# bucketing is verified in production -- if every request resolved to one IP,
# the 20/day session quota would become a single global cap.
ALLOW_PUBLIC_INIT = os.environ.get("ALLOW_PUBLIC_INIT", "false").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)


# AWS credentials for Bedrock are resolved by boto3's default provider chain
# (env vars, shared config, or the instance/task role). No path validation is
# required here; log only whether an explicit key pair is present (PHI-free).
if os.environ.get("AWS_ACCESS_KEY_ID"):
    logging.info("AWS credentials present via environment; Bedrock will use them.")
else:
    logging.info("No AWS_ACCESS_KEY_ID in env; Bedrock falls back to the default boto3 credential chain.")
