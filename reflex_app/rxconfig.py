import os
import reflex as rx

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
    # IMPORTANT: Reflex state/token management intentionally does NOT use Redis.
    # Pointing Reflex at REDIS_URL spun up its RedisTokenManager (continuous
    # keyspace/pubsub + per-socket token ops) on every /_event connect, burning
    # the serverless Redis request quota and starving real user sessions. Reflex
    # now uses its in-memory LocalTokenManager; Cloud Run --session-affinity
    # keeps each user on one instance, and the app's own session store
    # (preconsult.services.session_service) still owns real-user session state.
    # Do not re-introduce redis_url here without a dedicated Redis budget.
    show_reflex_badge=False,
)
