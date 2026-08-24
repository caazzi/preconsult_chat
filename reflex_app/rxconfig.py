import os
import reflex as rx

config = rx.Config(
    app_name="preconsult",
    # The backend URL baked into the client's EVENT socket endpoint. This must
    # be the production origin so the built JS points at this server (not
    # `localhost`). The CI build arg `API_URL` is NOT consumed by Reflex; the
    # control field is this config attribute (or `REFLEX_API_URL`).
    api_url=os.environ.get("REFLEX_API_URL", "https://pre-consult.org"),
    # Reflex event transport. We deploy with `--no-use-http2`, so the browser
    # talks HTTP/1.1 and CAN upgrade to a WebSocket there (the old "cannot upgrade
    # from HTTP/2" warning applied to the pre-`--no-use-http2` setup). Long-polling
    # over Cloud Run proved unstable (endless re-handshake, no state delta), so we
    # trial `websocket`. Defaultable/reversible via `REFLEX_TRANSPORT`.
    transport=os.environ.get("REFLEX_TRANSPORT", "websocket"),
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
