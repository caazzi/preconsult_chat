import os
import reflex as rx

# Lock expiration (ms) for Redux/Redis state transactions. Must comfortably
# exceed the longest state-mutating handler — `get_interview_questions` streams
# up to 30s while mutating state, well over the 10s default. This prevents
# `LockExpiredError` for real users. The warning threshold must stay below it.
REDIS_LOCK_EXPIRATION_MS = 60000

config = rx.Config(
    app_name="preconsult",
    redis_url=os.environ.get("REDIS_URL"),
    redis_lock_expiration=REDIS_LOCK_EXPIRATION_MS,
    redis_lock_warning_threshold=REDIS_LOCK_EXPIRATION_MS // 2,
    show_reflex_badge=False,
)
