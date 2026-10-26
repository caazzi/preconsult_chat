# Authz Matrix — `src/preconsult` API

One row per `/api/*` route. "Auth" is enforced by the router-level
`authenticate` dependency (session cookie **or** `X-API-KEY`) plus any per-route
ownership check. The single exception is the session bootstrap
(`POST /api/session/init`), which uses `init_access` — see the note below.
Error codes are stable and machine-readable (`src/preconsult/core/errors.py`).

| Method | Path | Auth | Ownership | Rate limit | Success | Error codes |
|---|---|---|---|---|---|---|
| POST | `/api/session/init` | bootstrap: credential unless `ALLOW_PUBLIC_INIT` | n/a (creates) | 2/min, 20/day per IP | 200 `{session_id}` + Set-Cookie | `auth_failed`, `validation_failed`, `rate_limited`, `redis_*`, `service_unavailable` |
| POST | `/api/initial-questions-stream` | cookie or key | cookie `session_id` must equal body `session_id` | 5/min per IP | 200 `text/event-stream` | `auth_failed`, `session_expired`, `rate_limited`, upstream codes |
| POST | `/api/interview-questions-stream` | cookie or key | cookie `session_id` must equal body `session_id` | 5/min per IP | 200 `text/event-stream` | `auth_failed`, `session_expired`, `rate_limited`, upstream codes |
| POST | `/api/generate-pdf` | cookie or key | cookie `session_id` must equal body `session_id` | none | 200 `application/pdf` | `auth_failed`, `session_expired` |
| POST | `/api/analytics/event` | cookie or key | n/a (anonymous counters) | none | 200 `{status: ok}` | `auth_failed` |
| GET | `/api/analytics/stats` | cookie or key | n/a (aggregate) | none | 200 `[...]` | `auth_failed` |

### The bootstrap exception

`POST /api/session/init` is the only route that may be reachable without a
credential. It is the call that **mints** the cookie every other row requires,
so requiring that cookie first would be circular (the React SPA at `/next`
holds no credential and no cookie on first load).

The **code default** is `ALLOW_PUBLIC_INIT=false` (fail closed), but the
**deployed environment sets it to `true`** — the SPA holds no API key, so it has
no other way to start a session. When enabled, the guards are the per-IP rate
limit (2/min, 20/day), the bot gate, and the bounds on `SessionInitRequest` — all
three are load-bearing, because an open bootstrap is also an open LLM-spend and
Redis-fill path. Client-IP bucketing was verified in the deployed container on
2026-10-26: each visitor produced its own `session_quota:<client ip>` key rather
than one shared key, which is what makes those limits per client instead of a
global cap. Re-verify that before raising the quota or trusting the flag on a new
topology.

## Non-`/api/*` routes

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/health`, `/health/live`, `/health/ready`, `/health/metrics` | none | PHI-free status/counters only |
| GET | `/privacy`, `/terms`, `/robots.txt`, `/sitemap.xml`, `/llms.txt` | none | static content |
| — | `/` (SPA shell), `/assets/*` | none | hashed assets immutable; document `no-store` |

## Decisions (Option A)

- **One browser concept for "not authenticated enough to proceed":**
  a missing/expired cookie or an aged-out session resolves to
  **`404 session_expired`** — the user restarts. There is deliberately **no**
  `401 unauthorized` for the browser.
- **`403 auth_failed`** is reserved for: missing/invalid credentials, a
  **cookie for a different session** (ownership), and `Origin`/CSRF rejects —
  i.e. security signals a real user should not normally see.
- Internal logs distinguish the cause (e.g. `auth.session_ownership_denied`)
  without exposing it as a client-visible concept.

## Enforcement points

- `authenticate` — router dependency (`endpoints.py`).
- `_require_session_ownership` — session-scoped endpoints (`endpoints.py`).
- `BotGateMiddleware` — pre-auth scanner block on Redis-backed paths
  (`src/preconsult/site/middleware.py`).
- Tests: `tests/test_session_auth.py`, `tests/test_authz_matrix.py`,
  `tests/test_api_integration.py`, `tests/test_security.py`.
