# API Contract — Behavioral Gaps Not Expressible in OpenAPI

The **structural** API contract is auto-generated and always in sync: it is the
OpenAPI schema produced by FastAPI from `src/preconsult/api/endpoints.py`.

- Interactive UI: `GET /api/docs` (Swagger UI) or `GET /api/redoc` (ReDoc)
- Machine-readable: `GET /api/openapi.json`

Any frontend (or its developer) should treat `/api/openapi.json` as the
authoritative source for request/response schemas, Pydantic models, and
auth requirement. This document covers only the **behavioral** rules that
OpenAPI 3.1 cannot encode but that a client must honour.

---

## 1. Transport & auth

- Base URL resolution (`reflex_app/preconsult/analytics.py::_api_url` /
  `state.py::_api_url`):
  - If `API_BASE_URL` is an absolute `http(s)://` origin, call
    `<origin>/api<path>`.
  - Else call the same-origin `/api<path>` (dev / same-image serving).
  - **Never** append `/api` again when `API_BASE_URL` already ends in `/api`
    (would produce `/api/api/...`).
- Every `/api/**` request must send the header `X-API-KEY`. A missing/invalid
  key returns `403` with a stable `auth_failed` code (gated by the bot gate
  before shipping for scanner-like user-agents).

---

## 2. Session lifecycle

- `POST /api/session/init` returns `{ "session_id": "..." }`.
- The session is **ephemeral**: a 30-minute TTL from creation, no persistence
  beyond it (plus a bounded per-worker in-memory fallback during Redis outage).
- `session_id` is required by every subsequent endpoint
  (`initial-questions-stream`, `interview-questions-stream`, `generate-pdf`).
- Error-classification contract (stable codes, see `src/preconsult/core/errors.py`
  and `AGENTS.md`):
  - Unknown/expired session → `404 session_expired`.
  - Redis down *with no in-memory copy* → `503 redis_unavailable` (NOT a
    misleading `session_expired`).
  - Upstash daily `max requests limit exceeded` → `503 redis_quota_exceeded`;
    session CRUD degrades to the in-memory fallback rather than blocking the user.

---

## 3. Server-Sent Events (SSE) framing — the stream endpoints

Both `POST /api/initial-questions-stream` and `POST /api/interview-questions-stream`
respond `content-type: text/event-stream`. Wire contract pins:

- Each chunk is emitted as a **single logical line**:
  `data: <json.dumps(chunk)>` (note trailing newlines are consumed; the
  `data: ` prefix + JSON is one event).
- Client parses exactly:
  ```python
  async for line in response.aiter_lines():
      if line.startswith("data: "):
          chunk = json.loads(line[len("data: "):])
  ```
  (Mirrored in `tests/test_sse_contract.py`.)
- **Mid-stream errors are served as a normal SSE event — never an HTTP error.**
  The endpoint resolves `200` even on failure; the final `data:` payload is a
  localized, generic error string (e.g. `"Service temporarily unavailable..."`).
  Server exceptions/internals must never leak into the body.
- Client stream consumer responsibilities:
  - Accumulate chunks into a local buffer.
  - Re-parse the buffer on each chunk after `is_emergency_trigger` gate (a
    red-flag token aborts into the emergency dialog).
  - Re-run `split_questions(buffer)` to derive the live question list (see
    `docs/parsing-port-spec.md`).

Tests that pin this contract: `tests/test_sse_contract.py`,
`tests/test_api_integration.py`.

---

## 4. Rate limits & quotas (per IP)

| Endpoint | Limit |
|---|---|
| `POST /api/session/init` | 2/min, 20/day per IP |
| `POST /api/*-questions-stream` | 5/min per IP |

- Exceeding returns `429 rate_limited` (or `redis_quota_exceeded` for the daily
  Upstash quota). `get_client_ip()` only honours proxy headers when
  `TRUST_PROXY_HEADERS=true` (see `src/preconsult/core/config.py`).

---

## 5. PDF generation

- `POST /api/generate-pdf` accepts `session_id` + `qa_pairs` (1–5 pairs, each
  `question`/`answer`, answer ≤2000 chars). No LLM call; fully deterministic.
- Responds `200` with `application/pdf` and a `Content-Disposition` attachment
  filename; the client triggers a browser download of the bytes.

---

## Sources of truth

- Request/response schemas & route list: `GET /api/openapi.json`
- Endpoint implementations: `src/preconsult/api/endpoints.py`
- Error codes & handlers: `src/preconsult/core/errors.py`
- SSE/pin tests: `tests/test_sse_contract.py`, `tests/test_api_integration.py`
- Error-handler/privacy-contract tests: `tests/test_error_handlers.py`
- Client IP / proxy policy: `src/preconsult/core/config.py`,
  `tests/test_client_ip.py`

> This document is intentionally scoped to behavioral gaps. When in doubt,
> prefer the generated OpenAPI schema; if a rule has no representation in
> OpenAPI, pin it here and add/update a test.
