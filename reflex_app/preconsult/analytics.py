import os
import httpx
import logging

API_BASE_URL = os.environ.get("API_BASE_URL", "/api")
API_KEY = os.environ.get("PRECONSULT_API_KEY", "")


async def log_analytics_event(event_name: str):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{API_BASE_URL}/analytics/event",
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
                f"{API_BASE_URL}/analytics/stats",
                headers={"X-API-KEY": API_KEY},
                timeout=10.0,
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logging.error(f"Erro ao buscar analytics: {e}")
    return []
