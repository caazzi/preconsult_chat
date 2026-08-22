import os
import reflex as rx

# Lock expiration (ms) for Redux/Redis state transactions. Must comfortably
# exceed the longest state-mutating handler — `get_interview_questions` streams
# up to 30s while mutating state, well over the 10s default. This prevents
# `LockExpiredError` for real users. The warning threshold must stay below it.
REDIS_LOCK_EXPIRATION_MS = 60000

config = rx.Config(
    app_name="preconsult",
    # The backend URL baked into the client's EVENT socket endpoint. This must
    # be the production origin so the built JS points at this server (not
    # `localhost`). The CI build arg `API_URL` is NOT consumed by Reflex; the
    # control field is this config attribute (or `REFLEX_API_URL`).
    api_url=os.environ.get("REFLEX_API_URL", "https://pre-consult.org"),
    # Reflex event transport. The project is served on Cloud Run, whose frontend
    # always offers HTTP/2 to browsers but cannot upgrade a browser's HTTP/2
    # connection to a WebSocket (Google issue 194314805). HTTP long-polling
    # avoids WebSockets entirely and works over HTTP/2, so we default to it to
    # keep the event channel functional. Defaultable/reversible via
    # `REFLEX_TRANSPORT=websocket` without a code change.
    transport=os.environ.get("REFLEX_TRANSPORT", "polling"),
    redis_url=os.environ.get("REDIS_URL"),
    redis_lock_expiration=REDIS_LOCK_EXPIRATION_MS,
    redis_lock_warning_threshold=REDIS_LOCK_EXPIRATION_MS // 2,
    show_reflex_badge=False,
)
