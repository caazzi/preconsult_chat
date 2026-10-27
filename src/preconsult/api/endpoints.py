"""
API Endpoints (Orchestrator).

This module defines the FastAPI routes. It leverages dependency injection
to trigger the lazy-loading of services in the agent_service module, ensuring
the application starts quickly. Includes Redis-backed ephemeral state.
"""
import asyncio
import html
import json
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from ipaddress import ip_address
from typing import Annotated, Literal
from fastapi import APIRouter, HTTPException, Security, Depends, Request
from fastapi.security import APIKeyHeader
from fastapi.responses import StreamingResponse, Response, JSONResponse
from pydantic import BaseModel, Field, StringConstraints
from langchain_core.runnables import Runnable

from preconsult.core.config import (
    ALLOW_PUBLIC_INIT,
    PRECONSULT_API_KEY,
    TRUST_CF_CONNECTING_IP,
    TRUST_PROXY_HEADERS,
    SESSION_COOKIE_NAME,
    SESSION_COOKIE_SECURE,
)
from preconsult.core.observability import (
    new_request_id,
    log_event,
    record_funnel_step,
    timed,
)
from preconsult.core.parsing import has_emergency_red_flag
from preconsult.core.session_auth import (
    secure_compare,
    sign_session_id,
    verify_session_cookie,
)
from preconsult.services.agent_service import (
    stream_interview_questions,
    get_interview_chain,
)
from preconsult.services.pdf_service import generate_pdf_report_in_memory
from preconsult.services.session_service import (
    create_session,
    get_session,
    update_session,
    check_rate_limit,
    check_session_quota,
    increment_session_quota,
    get_redis,
)
# --- Security & Helper Functions ---
API_KEY_HEADER = APIKeyHeader(name="X-API-KEY", auto_error=False)


class AuthContext:
    """How a request authenticated: a browser session cookie or the API key.

    ``session_id`` is set for cookie auth (and used for ownership checks);
    ``via`` is ``"cookie"`` or ``"header"`` (metadata only, never logged with a
    value).
    """

    def __init__(self, via: str, session_id: str | None = None):
        self.via = via
        self.session_id = session_id


def _has_valid_api_key(api_key_header: str | None) -> bool:
    # Constant-time comparison so a caller cannot infer the key byte-by-byte
    # from response timing. Guard against an unset key (config permits None under
    # BUILD_MODE) or a missing header.
    # ``secure_compare`` compares UTF-8 bytes, so a non-ASCII header
    # (Starlette decodes latin-1) is a plain mismatch -> 403, not
    # ``TypeError`` -> 500.
    expected = PRECONSULT_API_KEY
    return bool(
        expected
        and api_key_header
        and secure_compare(api_key_header, expected)
    )


async def authenticate(
    request: Request,
    api_key_header: str = Security(API_KEY_HEADER),
) -> AuthContext:
    """Accept EITHER a valid session cookie OR the API key.

    The cookie path is the browser's; the header path is kept for Reflex (which
    still sends ``X-API-KEY``) and programmatic clients. Neither present/valid
    → 403 ``auth_failed``.
    """
    cookie_session = verify_session_cookie(request.cookies.get(SESSION_COOKIE_NAME))
    if cookie_session:
        return AuthContext(via="cookie", session_id=cookie_session)
    if _has_valid_api_key(api_key_header):
        return AuthContext(via="header")
    raise HTTPException(status_code=403, detail="Could not validate credentials")


async def init_access(
    request: Request,
    api_key_header: str = Security(API_KEY_HEADER),
) -> None:
    """Access rule for the session bootstrap.

    The bootstrap mints the cookie that authenticates every other route, so
    it cannot require that cookie. With ALLOW_PUBLIC_INIT=true it is open to
    anonymous browsers and relies on the per-IP rate limit, the bot gate and
    the bounded payload instead. With the default false it behaves exactly
    like every other route (cookie or key).
    """
    if ALLOW_PUBLIC_INIT:
        return
    await authenticate(request, api_key_header)


# Back-compat alias: existing imports/tests may reference get_api_key.
get_api_key = authenticate


def _require_session_ownership(request: Request, session_id: str) -> None:
    """Reject a cookie-authenticated request for someone else's session.

    Header-auth (programmatic/Reflex) is trusted for now; cookie auth must match
    the requested session, closing the horizontal-access gap.
    """
    cookie_session = verify_session_cookie(request.cookies.get(SESSION_COOKIE_NAME))
    if cookie_session and cookie_session != session_id:
        log_event(
            logging.WARNING,
            "auth.session_ownership_denied",
            request_id=new_request_id(),
        )
        raise HTTPException(status_code=403, detail="Could not validate credentials")


def _set_session_cookie(response: Response, session_id: str) -> None:
    """Attach the signed, HttpOnly, session cookie to a response.

    No ``max_age``/``expires`` ⇒ a session cookie the browser drops on close.
    Server-side TTL (30 min) is the real bound.
    """
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=sign_session_id(session_id),
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="strict",
        path="/",
    )


def _sanitize_input(text: str) -> str:
    """Sanitizes user text: strips whitespace and escapes HTML entities."""
    if not isinstance(text, str):
        return ""
    return html.escape(text.strip())


_EMERGENCY_MESSAGES = {
    "en": (
        "[EMERGENCY ALERT] Your symptoms may require immediate medical attention. "
        "Please call your local emergency number (e.g. 911) or go to the nearest "
        "emergency room now. This tool cannot help with an emergency."
    ),
    "pt": (
        "[ALERTA DE EMERGÊNCIA] Seus sintomas podem exigir atenção médica imediata. "
        "Ligue para o serviço de emergência local (por exemplo, 192) ou vá ao pronto-socorro "
        "mais próximo agora. Esta ferramenta não pode ajudar em uma emergência."
    ),
}


def _emergency_message(lang: str) -> str:
    return _EMERGENCY_MESSAGES.get(lang, _EMERGENCY_MESSAGES["en"])


def _emergency_stream_response(lang: str, event: str, request_id: str) -> StreamingResponse:
    """Short-circuit an SSE stream with a deterministic emergency warning.

    The red-flag decision is made on the *input* (chief complaint) rather than
    the model's output, so a patient describing a critical symptom is warned
    immediately even if the LLM never utters a trigger token. Emits the same
    ``data: <json>`` wire contract as a normal stream (HTTP 200) so the existing
    client ``is_emergency_trigger`` path surfaces the dialog.
    """
    log_event(
        logging.WARNING,
        event,
        request_id=request_id,
        lang=lang,
        trigger_side="input",
    )
    message = _emergency_message(lang)

    async def event_generator():
        yield f"data: {json.dumps(message)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# Longest header value we will parse. X-Forwarded-For is attacker-influenced
# and its value ends up in rate-limit keys, so cap it instead of trusting it.
_MAX_IP_HEADER_CHARS = 128


def _parse_ip(value: str) -> str | None:
    """Return a normalized IP, or None when the value is not a single address."""
    value = value.strip()
    if not value or len(value) > _MAX_IP_HEADER_CHARS:
        return None
    try:
        return str(ip_address(value))
    except ValueError:
        return None


def get_client_ip(request: Request) -> str:
    """Extract the effective client IP for rate limiting / quotas.

    Measured on Cloud Run (2026-10-26, header-echo probe):
      * ``request.client.host`` is ``169.254.169.126`` - the local proxy, the
        same value for every visitor. Using it would put *all* users in one
        rate-limit / session-quota bucket.
      * Cloud Run **appends** the client address to ``X-Forwarded-For`` and does
        not strip what the client sent, so ``"1.2.3.4,187.15.85.23"`` arrives
        when a caller forges the header. Only the **last** entry is ours.
      * ``cf-connecting-ip`` passes through untouched (no Cloudflare proxy), so
        it is ignored unless ``TRUST_CF_CONNECTING_IP`` is explicitly enabled.

    Anything that does not parse as a single IP falls back to the transport
    address, so a malformed header can neither forge a bucket nor blow up a key.
    """
    transport_ip = request.client.host if request.client else "127.0.0.1"
    if not TRUST_PROXY_HEADERS:
        return transport_ip

    if TRUST_CF_CONNECTING_IP:
        forwarded = _parse_ip(request.headers.get("cf-connecting-ip", ""))
        if forwarded:
            return forwarded

    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        # The rightmost entry is the one our proxy appended; every earlier entry
        # may have been supplied by the caller.
        forwarded = _parse_ip(xff.rsplit(",", 1)[-1])
        if forwarded:
            return forwarded

    return transport_ip

# --- Data Models (Ephemeral State Design) ---
# One list entry (condition, medication, family-history item). Every bound
# here is a cost/abuse guard: the bootstrap is (or will be) public, and this
# payload goes into Redis, the Bedrock prompt and the PDF renderer.
_ListEntry = Annotated[str, StringConstraints(max_length=100)]


class SessionInitRequest(BaseModel):
    # Step 1 — Demographics
    age_bracket: str = Field(default="", max_length=10)
    sex: str = Field(default="", max_length=40)
    lang: str = Field(default="en", max_length=8)
    # Step 2 — Chief Complaint
    specialist: str = Field(default="", max_length=80)
    chief_complaint: str = Field(default="", max_length=2000)
    duration: str = Field(default="", max_length=80)
    complaint_detail: str = Field(default="", max_length=2000)
    # Step 3 — Medical History
    conditions: list[_ListEntry] = Field(default_factory=list, max_length=20)
    medications: list[_ListEntry] = Field(default_factory=list, max_length=20)
    allergies: str = Field(default="", max_length=500)
    # Step 4 — Lifestyle & Family
    family_history: list[_ListEntry] = Field(default_factory=list, max_length=20)
    smoking: str = Field(default="", max_length=40)
    alcohol: str = Field(default="", max_length=40)

class InitialRequest(BaseModel):
    session_id: str
    chief_complaint: str = Field(..., max_length=5000)

class InterviewRequest(BaseModel):
    session_id: str

class QAPair(BaseModel):
    question: str
    answer: str = Field(..., max_length=2000)

class GeneratePdfRequest(BaseModel):
    session_id: str
    qa_pairs: list[QAPair] = Field(..., min_length=1, max_length=5)

# --- OpenAPI Tags & Error Response Schemas ---
TAG_SESSION = "Session Lifecycle"
TAG_STREAM = "Clinical Question Streams"
TAG_PDF = "PDF Report"
TAG_ANALYTICS = "Analytics"

# Stable machine-readable error codes surfaced by core/errors.py. Documented
# here so the interactive OpenAPI contract reflects the real error contract.
_AUTH_FORBIDDEN = {
    403: {
        "description": "Missing/invalid X-API-KEY. machine-readable code `auth_failed`.",
    }
}
_RATE_LIMITED = {
    429: {
        "description": "Per-IP rate or daily-session quota exceeded. machine-readable "
        "codes `rate_limited` / `redis_quota_exceeded`.",
    }
}
_SESSION_EXPIRED = {
    404: {
        "description": "Session unknown/expired. machine-readable code `session_expired`.",
    }
}
_STRATEGIC_ERRORS = {
    **_AUTH_FORBIDDEN,
    **_RATE_LIMITED,
    **_SESSION_EXPIRED,
}

# --- API Router ---
# Authenticated surface: every route except the session bootstrap.
router = APIRouter(dependencies=[Depends(authenticate)])
# Bootstrap surface: POST /session/init, which issues the cookie used by the
# routes above. Access is decided by init_access (ALLOW_PUBLIC_INIT).
public_router = APIRouter()

@public_router.post(
    "/session/init",
    dependencies=[Depends(init_access)],
    tags=[TAG_SESSION],
    summary="Create an ephemeral patient session",
    description=(
        "Initializes a new ephemeral session (30-minute TTL) with the full intake form. "
        "Returns a `session_id` used by all subsequent endpoints. Per-IP rate limited "
        "(2/min, 20/day). No data is persisted beyond the session TTL and the in-memory fallback."
    ),
    responses=_STRATEGIC_ERRORS,
)
async def init_session(request: SessionInitRequest, fastapi_req: Request):
    """Initializes a new ephemeral Redis session with full form data.

    Also issues the signed session cookie that authenticates the browser for
    all subsequent calls (the API key remains accepted for Reflex/programmatic
    clients).
    """
    request_id = new_request_id()
    ip = get_client_ip(fastapi_req)

    async with timed(
        "session.init",
        request_id=request_id,
        lang=request.lang,
        conditions_n=len(request.conditions),
        medications_n=len(request.medications),
        complaint_len=len(request.chief_complaint),
    ):
        # 1. Check daily quota (max 20 sessions per IP)
        if not await check_session_quota(ip, limit=20):
            raise HTTPException(status_code=429, detail="Daily session limit reached for this IP.")

        # 2. Check rate limit for session creation (max 2 per minute)
        if not await check_rate_limit(f"init:{ip}", limit=2, window=60):
            raise HTTPException(status_code=429, detail="Too many session requests. Please wait.")

        session_id = await create_session({
            "age_bracket": request.age_bracket,
            "sex": request.sex,
            "lang": request.lang,
            "specialist": request.specialist,
            "chief_complaint": request.chief_complaint,
            "duration": request.duration,
            "complaint_detail": request.complaint_detail,
            "conditions": request.conditions,
            "medications": request.medications,
            "allergies": request.allergies,
            "family_history": request.family_history,
            "smoking": request.smoking,
            "alcohol": request.alcohol,
        })

        # Increment quota after successful creation
        await increment_session_quota(ip)

        log_event(
            logging.INFO,
            "session.init.ok",
            request_id=request_id,
            session_id_short=session_id[:8],
            lang=request.lang,
        )

    response = JSONResponse({"session_id": session_id})
    _set_session_cookie(response, session_id)
    return response

@dataclass(frozen=True)
class _StreamSession:
    """Everything both question streams need once auth/limit/session pass."""

    session_id: str
    session_data: dict
    lang: str
    err_msg: str
    request_id: str


async def _open_stream(session_id: str, fastapi_req: Request) -> _StreamSession:
    """Rate limit, load the session and enforce cookie ownership.

    Shared by both stream endpoints so the order (limit before storage) and the
    stable error codes cannot drift between them.
    """
    request_id = new_request_id()
    ip = get_client_ip(fastapi_req)
    if not await check_rate_limit(f"stream:{ip}", limit=5, window=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait a moment.")

    session_data = await get_session(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session expired or invalid")
    _require_session_ownership(fastapi_req, session_id)

    lang = session_data.get("lang", "en")
    err_msg = (
        "⚠️ ERROR: Service temporarily unavailable. Please try again."
        if lang == "en"
        else "⚠️ ERRO: Serviço temporariamente indisponível. Tente novamente."
    )
    return _StreamSession(session_id, session_data, lang, err_msg, request_id)


def _emergency_response_if_flagged(
    ctx: _StreamSession,
    complaint: str,
    detail: str,
    event: str,
) -> StreamingResponse | None:
    """Deterministic input-side red-flag gate.

    Never rely solely on the model to signal an emergency: if the patient's own
    words trip a red flag, warn immediately and never call the LLM. Kept in one
    place because a fix landing in one stream and not the other would be a
    clinical safety regression, not a style issue.
    """
    if has_emergency_red_flag(complaint, detail):
        return _emergency_stream_response(ctx.lang, event, ctx.request_id)
    return None


def _question_stream(
    ctx: _StreamSession, chain: Runnable, *, topic: str
) -> StreamingResponse:
    """SSE response streaming the interview questions for this session.

    ``topic`` is the log-event namespace (``stream.initial`` / ``stream.interview``);
    the event payload is identical for both endpoints.
    """

    async def event_generator():
        streamed = 0
        structured = False
        try:
            async for event in stream_interview_questions(ctx.session_data, ctx.lang, chain):
                if event.kind == "questions":
                    structured = True
                    payload = {"type": "questions", "questions": event.value}
                    yield f"data: {json.dumps(payload)}\n\n"
                else:
                    streamed += 1
                    yield f"data: {json.dumps(event.value)}\n\n"
            log_event(
                logging.INFO,
                f"{topic}.ok",
                request_id=ctx.request_id,
                session_id_short=ctx.session_id[:8],
                chunks=streamed,
                structured=structured,
            )
        except Exception as e:
            logging.error(f"Error during {topic} stream: {e}", exc_info=True)
            log_event(
                logging.ERROR,
                f"{topic}.error",
                request_id=ctx.request_id,
                error_type=type(e).__name__,
            )
            yield f"data: {json.dumps(' ' + ctx.err_msg)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post(
    "/initial-questions-stream",
    tags=[TAG_STREAM],
    summary="Stream initial clinical follow-up questions",
    description=(
        "Server-Sent Events (SSE) stream of LLM-generated follow-up questions based on the "
        "stored chief complaint. Emits `data: <json>` lines; mid-stream errors are served as "
        "a normal SSE event (never an HTTP error). 5/min per IP."
    ),
    responses=_STRATEGIC_ERRORS,
)
async def get_initial_questions_streamed(
    request: InitialRequest,
    fastapi_req: Request,
    chain: Runnable = Depends(get_interview_chain)
):
    """Streams interview questions based on chief complaint."""
    ctx = await _open_stream(request.session_id, fastapi_req)

    sanitized_complaint = _sanitize_input(request.chief_complaint)
    await update_session(request.session_id, {"chief_complaint": sanitized_complaint})
    ctx.session_data["chief_complaint"] = sanitized_complaint

    emergency = _emergency_response_if_flagged(
        ctx,
        sanitized_complaint,
        ctx.session_data.get("complaint_detail", ""),
        "stream.initial.emergency_input",
    )
    if emergency is not None:
        return emergency

    log_event(
        logging.INFO,
        "stream.initial.start",
        request_id=ctx.request_id,
        session_id_short=ctx.session_id[:8],
        lang=ctx.lang,
        complaint_len=len(sanitized_complaint),
    )
    return _question_stream(ctx, chain, topic="stream.initial")

@router.post(
    "/interview-questions-stream",
    tags=[TAG_STREAM],
    summary="Stream targeted clinical interview questions",
    description=(
        "Server-Sent Events (SSE) stream of targeted interview questions derived from the full "
        "session context using OPQRST/SAMPLE clinical frameworks. Single LLM call. Emits "
        "`data: <json>` lines; mid-stream errors are served as a normal SSE event. 5/min per IP."
    ),
    responses=_STRATEGIC_ERRORS,
)
async def get_interview_questions_streamed(
    request: InterviewRequest,
    fastapi_req: Request,
    chain: Runnable = Depends(get_interview_chain)
):
    """Streams targeted interview questions based on full form context. Single LLM call."""
    ctx = await _open_stream(request.session_id, fastapi_req)

    emergency = _emergency_response_if_flagged(
        ctx,
        ctx.session_data.get("chief_complaint", ""),
        ctx.session_data.get("complaint_detail", ""),
        "stream.interview.emergency_input",
    )
    if emergency is not None:
        return emergency

    log_event(
        logging.INFO,
        "stream.interview.start",
        request_id=ctx.request_id,
        session_id_short=ctx.session_id[:8],
        lang=ctx.lang,
    )
    return _question_stream(ctx, chain, topic="stream.interview")

@router.post(
    "/generate-pdf",
    tags=[TAG_PDF],
    summary="Generate a deterministic in-memory patient report PDF",
    description=(
        "Compiles the stored session form data plus the submitted Q&A pairs into a localized "
        "PDF report entirely in memory (no LLM call). Streamed directly to the client. "
        "Requires a valid session and 1-5 QA pairs."
    ),
    responses=_STRATEGIC_ERRORS,
)
async def generate_pdf_endpoint(request: GeneratePdfRequest, fastapi_req: Request):
    """Generates PDF deterministically from session form data + Q&A pairs. No LLM call."""
    request_id = new_request_id()
    session_data = await get_session(request.session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Session expired or invalid")
    _require_session_ownership(fastapi_req, request.session_id)

    qa_pairs = [{"question": pair.question, "answer": pair.answer} for pair in request.qa_pairs]
    loop = asyncio.get_running_loop()
    async with timed(
        "pdf.generate",
        request_id=request_id,
        lang=session_data.get("lang", "en"),
        qa_n=len(qa_pairs),
    ):
        pdf_bytes, filename = await loop.run_in_executor(
            None, generate_pdf_report_in_memory,
            session_data, qa_pairs, session_data.get("lang", "en")
        )
    log_event(
        logging.INFO,
        "pdf.generate.ok",
        request_id=request_id,
        session_id_short=request.session_id[:8],
        pdf_bytes=len(pdf_bytes),
    )
    headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
    return Response(content=pdf_bytes, media_type='application/pdf', headers=headers)


# Pre-session funnel steps happen before the session exists (it is created at
# the lifestyle step), so they can never be keyed by one. They are counted in
# memory and logged, never written to Redis: the free-tier quota is reserved for
# real patient sessions. The remaining keys keep the 7-day Redis funnel.
ANONYMOUS_FUNNEL_EVENTS = (
    "intake_started",
    "demographics_submitted",
    "complaint_submitted",
    "history_submitted",
)
SESSION_FUNNEL_EVENTS = (
    "lifestyle_submitted",
    "summary_generated",
    "pdf_downloaded",
)

# The whitelist is the contract in docs/analytics-contract.md. It also bounds
# the Redis hash fields: an unvalidated `str` let any client grow the free-tier
# hash with invented keys.
FunnelEvent = Literal[
    "intake_started",
    "demographics_submitted",
    "complaint_submitted",
    "history_submitted",
    "lifestyle_submitted",
    "summary_generated",
    "pdf_downloaded",
]


class AnalyticsEventRequest(BaseModel):
    event: FunnelEvent


@router.post(
    "/analytics/event",
    tags=[TAG_ANALYTICS],
    summary="Record an anonymous funnel analytics event",
    description=(
        "Counts one funnel event key. Pre-session keys are counted in memory and logged "
        "(no Redis, no session required); session keys increment the 7-day Redis funnel. "
        "Best-effort: never raises on Redis failure. Keys are documented in "
        "docs/analytics-contract.md."
    ),
    responses=_AUTH_FORBIDDEN,
)
async def log_analytics_event(request: AnalyticsEventRequest):
    if request.event in ANONYMOUS_FUNNEL_EVENTS:
        # No Redis access on purpose: no session exists yet, and every visit
        # would otherwise burn free-tier quota before the patient needs one.
        record_funnel_step(request.event)
        return {"status": "ok"}
    try:
        client = get_redis()
        today_str = date.today().isoformat()
        key = f"analytics:{today_str}"
        await client.hincrby(key, request.event, 1)
        await client.expire(key, 30 * 24 * 60 * 60)
    except Exception as e:
        logging.error(f"Falha ao registrar analytics: {e}")
    return {"status": "ok"}


@router.get(
    "/analytics/stats",
    tags=[TAG_ANALYTICS],
    summary="Fetch the 7-day analytics funnel",
    description=(
        "Returns per-day recorded funnel counters for the last 7 days (oldest first). "
        "Best-effort: returns empty buckets if Redis is unavailable."
    ),
    responses=_AUTH_FORBIDDEN,
)
async def get_analytics_stats():
    data = []
    try:
        client = get_redis()
        for i in range(7):
            day = date.today() - timedelta(days=i)
            day_str = day.isoformat()
            key = f"analytics:{day_str}"
            raw_stats = await client.hgetall(key)
            stats = {
                "date": day_str,
                "demographics": int(raw_stats.get("demographics_submitted", 0)),
                "complaint": int(raw_stats.get("complaint_submitted", 0)),
                "history": int(raw_stats.get("history_submitted", 0)),
                "lifestyle": int(raw_stats.get("lifestyle_submitted", 0)),
                "summary": int(raw_stats.get("summary_generated", 0)),
                "pdf": int(raw_stats.get("pdf_downloaded", 0)),
            }
            data.append(stats)
    except Exception as e:
        logging.error(f"Falha ao buscar analytics: {e}")
    return list(reversed(data))
