import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from datetime import date
from fastapi import FastAPI
from fastapi.responses import Response
from pydantic import ValidationError
from google.api_core.exceptions import GoogleAPIError
from preconsult.api.endpoints import router as api_router
from preconsult.core.config import SENTRY_DSN
from preconsult.services.session_service import get_redis, _redis_available
from preconsult.core.errors import (
    RedisUnavailableError,
    LLMUnavailableError,
    redis_unavailable_handler,
    llm_unavailable_handler,
    validation_handler,
    google_api_handler,
    generic_handler,
)

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            FastApiIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        traces_sample_rate=0.1,
    )
    logging.info("Sentry SDK inicializado.")

app = FastAPI(
    title="PreConsult API",
    description="An API to help patients prepare for their doctor's visit.",
    version="1.0.0"
)

app.add_exception_handler(RedisUnavailableError, redis_unavailable_handler)
app.add_exception_handler(LLMUnavailableError, llm_unavailable_handler)
app.add_exception_handler(ValidationError, validation_handler)
app.add_exception_handler(GoogleAPIError, google_api_handler)
app.add_exception_handler(Exception, generic_handler)

app.include_router(api_router, prefix="/api", tags=["Medical Chat"])

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the PreConsult API. Go to /docs for the API documentation."}


@app.get("/health", tags=["Health"])
async def health():
    redis_status = "ok" if _redis_available is not False else "unavailable"
    return {"status": "healthy", "redis": redis_status}


@app.get("/robots.txt", include_in_schema=False)
async def robots_txt():
    content = (
        "User-agent: *\n"
        "Disallow: /admin/\n"
        "Disallow: /api/\n"
        "Allow: /\n\n"
        "Sitemap: https://pre-consult.org/sitemap.xml\n"
    )
    return Response(
        content=content,
        media_type="text/plain",
        headers={"Cache-Control": "public, max-age=86400"}
    )


@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap_xml():
    today = date.today().isoformat()
    content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"\n'
        '        xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        '  <url>\n'
        '    <loc>https://pre-consult.org/</loc>\n'
        f'    <lastmod>{today}</lastmod>\n'
        '    <changefreq>weekly</changefreq>\n'
        '    <priority>1.0</priority>\n'
        '    <xhtml:link rel="alternate" hreflang="en" href="https://pre-consult.org/?lang=en"/>\n'
        '    <xhtml:link rel="alternate" hreflang="pt" href="https://pre-consult.org/?lang=pt"/>\n'
        '    <xhtml:link rel="alternate" hreflang="x-default" href="https://pre-consult.org/"/>\n'
        '  </url>\n'
        '</urlset>\n'
    )
    return Response(
        content=content,
        media_type="application/xml",
        headers={"Cache-Control": "public, max-age=86400"}
    )
