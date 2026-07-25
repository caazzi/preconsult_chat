import os
import reflex as rx

config = rx.Config(
    app_name="preconsult",
    redis_url=os.environ.get("REDIS_URL"),
    show_reflex_badge=False,
)