import os
import httpx
import logging

API_KEY = os.environ.get("PRECONSULT_API_KEY", "")


def _api_url(path: str) -> str:
    base = os.environ.get("API_BASE_URL", "").rstrip("/")
    if base.startswith("http://") or base.startswith("https://"):
        return f"{base}/api{path}"
    return f"/api{path}"


async def log_analytics_event(event_name: str):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _api_url("/analytics/event"),
                json={"event": event_name},
                headers={"X-API-KEY": API_KEY},
                timeout=5.0,
            )
            if resp.status_code != 200:
                logging.warning(f"Falha ao registrar analytics: {resp.status_code}")
    except Exception as e:
        logging.error(f"Erro ao registrar analytics: {e}")


async def fetch_analytics_data() -> list[dict]:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                _api_url("/analytics/stats"),
                headers={"X-API-KEY": API_KEY},
                timeout=10.0,
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logging.error(f"Erro ao buscar analytics: {e}")
    return []
