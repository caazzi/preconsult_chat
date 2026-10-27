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

- Base URL resolution (`web/src/api/client.ts`: `API_BASE` + `apiUrl()`):
  - The SPA is served from the same origin as the API, so it calls `/api<path>`.
  - A build can point at another origin with `VITE_API_BASE_URL`; the value is
    used verbatim as the prefix, so it must **not** already end in `/api`
    (that would produce `/api/api/...`).
  - Requests always send `credentials: "include"` so the session cookie rides
    along; the SPA holds no API key (`web/src/api/client.ts`).
- Every `/api/**` request must authenticate with the signed session cookie **or**
  the `X-API-KEY` header (see `docs/authz-matrix.md`). A missing/invalid
  credential returns `403` with a stable `auth_failed` code (gated by the bot gate
  before shipping for scanner-like user-agents).
- **Bootstrap exception:** `POST /api/session/init` issues the cookie, so it
  cannot require one. The code default is `ALLOW_PUBLIC_INIT=false` (behaves like
  every other route), and the **deployed environment sets it to `true`** because
  the SPA at `/` is cookie-only and holds no API key. Guards: the per-IP
  limits, the bot gate and bounded payloads. Request bodies are bounded
  (`SessionInitRequest`), and an oversized/invalid body returns `422
  validation_failed` without echoing the submitted values.

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
- **Structured terminal event (tool-use).** The model returns its final answer
  via the `report_questions` tool, so the stream may additionally emit one
  terminal event whose JSON is an object rather than a string:
  ```
  data: {"type": "questions", "questions": ["...", "..."]}
  ```
  Text deltas still precede it (`data: "<text chunk>"`) for progressive
  rendering; a client that only understands strings simply ignores the object
  event (back-compat). A client that understands it may use the typed list
  directly instead of re-parsing numbered text with `split_questions`. The
  structured list is authoritative when present.
- **Mid-stream errors are served as a normal SSE event — never an HTTP error.**
  The endpoint resolves `200` even on failure; the final `data:` payload is a
  localized, generic error string (e.g. `"Service temporarily unavailable..."`).
  Server exceptions/internals must never leak into the body.
- Client stream consumer responsibilities:
  - Accumulate chunks into a local buffer.
  - Re-parse the buffer on each chunk after `is_emergency_trigger` gate (a
    red-flag token aborts into the emergency dialog). The SPA port lives in
    `web/src/api/sse.ts` + `web/src/contracts/parsing.ts`.
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
  Upstash quota). `get_client_ip()` (`src/preconsult/api/endpoints.py`) reads proxy
  headers only when `TRUST_PROXY_HEADERS=true` (parsed in
  `src/preconsult/core/config.py`), and then takes the last `x-forwarded-for` hop
  (the one Cloud Run appended) — see the measurement recorded in `AGENTS.md`. The
  deployed container sets it to `true`; without it every client shares one bucket
  (`169.254.169.126`).

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
- `/api` app assembly (handler registration order): `src/preconsult/api/app.py`
- Error codes & handlers: `src/preconsult/core/errors.py`
- Browser client (base URL, cookie auth, typed error codes): `web/src/api/client.ts`
- SSE/pin tests: `tests/test_sse_contract.py`, `tests/test_api_integration.py`
- Error-handler/privacy-contract tests: `tests/test_error_handlers.py`
- Client IP / proxy policy: `src/preconsult/api/endpoints.py::get_client_ip`,
  `src/preconsult/core/config.py`, `tests/test_client_ip.py`

> This document is intentionally scoped to behavioral gaps. When in doubt,
> prefer the generated OpenAPI schema; if a rule has no representation in
> OpenAPI, pin it here and add/update a test.
