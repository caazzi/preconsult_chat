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

# When True, honor the hop our own proxy appended to X-Forwarded-For. Required
# on Cloud Run: the container's transport peer is the local proxy
# (169.254.169.126, identical for every client), so with this False every
# visitor shares one rate-limit and session-quota bucket.
TRUST_PROXY_HEADERS = os.environ.get("TRUST_PROXY_HEADERS") == "true"

# cf-connecting-ip is NOT trustworthy on this deployment: pre-consult.org is
# DNS-only (no Cloudflare proxy), so the header passes through untouched from
# the client. Cloud Run appends the real client address to X-Forwarded-For as
# the last entry instead. Only enable this if the domain is moved behind
# Cloudflare's proxy, where Cloudflare becomes the trusted hop that sets it.
TRUST_CF_CONNECTING_IP = os.environ.get("TRUST_CF_CONNECTING_IP") == "true"

# Which model provider processes the intake answers. "vertex" (Google Vertex AI
# / Gemini) is the deployed default because it is the provider the running
# service has credentials for; "bedrock" (Anthropic Claude on AWS) is the opt-in
# path kept for the later AWS migration. This is a PHI data-flow decision, not a
# tuning knob: switching it changes which third party receives clinical text, so
# the privacy copy in reflex_app/preconsult/preconsult.py (and web/legal/ once
# the SPA serves those pages) must be updated in the same change.
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "vertex").strip().lower()

VERTEX_REGION = os.environ.get("VERTEX_AI_REGION", "us-central1")

# AWS Bedrock region for the Claude Haiku inference calls. Bedrock is a regional
# service and Claude is NOT available in every region; a single fixed region is
# used (env-overridable). Data-residency routing (e.g. LGPD) must key on where
# the session actually is, not on UI language — a later phase concern.
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))

# Provider-specific model ids. An explicit LLM_MODEL still wins, so the deployed
# environment can pin a model without touching code.
_DEFAULT_LLM_MODEL = {
    "vertex": "gemini-2.5-flash",
    "bedrock": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
}
LLM_MODEL = os.environ.get("LLM_MODEL") or _DEFAULT_LLM_MODEL.get(
    LLM_PROVIDER, _DEFAULT_LLM_MODEL["vertex"]
)

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


# Credential sanity logging for the selected provider. PHI-free: never logs a
# credential, only which resolution path is in play.
if LLM_PROVIDER == "bedrock":
    if os.environ.get("AWS_ACCESS_KEY_ID"):
        logging.info("AWS credentials present via environment; Bedrock will use them.")
    else:
        logging.info("No AWS_ACCESS_KEY_ID in env; Bedrock falls back to the default boto3 credential chain.")
else:
    gcp_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if gcp_creds and not os.path.exists(gcp_creds):
        logging.warning(f"GOOGLE_APPLICATION_CREDENTIALS is set but file not found at: {gcp_creds}")
    elif gcp_creds:
        logging.info(f"Using Google Cloud Credentials from: {gcp_creds}")
    else:
        logging.info("GOOGLE_APPLICATION_CREDENTIALS not set; using ambient/WIF credentials for Vertex AI.")
