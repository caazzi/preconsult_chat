import asyncio
import pytest
import httpx
from httpx import ASGITransport
from preconsult.main import app
from preconsult.core.config import PRECONSULT_API_KEY
import redis.asyncio as redis
import os

@pytest.mark.asyncio
async def test_rate_limit_session_init():
    headers = {"X-API-KEY": PRECONSULT_API_KEY}
    payload = {
        "age_bracket": "26-35",
        "sex": "Female",
        "lang": "en",
        "specialist": "Cardiology",
        "chief_complaint": "Chest pain",
        "duration": "2 days",
        "smoking": "No",
        "alcohol": "No"
    }

    # Clear redis for testing
    async with redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0")) as r:
        await r.flushdb()

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # First and second requests should succeed
        resp1 = await client.post("/api/session/init", json=payload, headers=headers)
        assert resp1.status_code == 200
        
        resp2 = await client.post("/api/session/init", json=payload, headers=headers)
        assert resp2.status_code == 200

        # Third request should be rate limited (limit=2)
        resp3 = await client.post("/api/session/init", json=payload, headers=headers)
        assert resp3.status_code == 429
        assert "Too many session requests" in resp3.json()["detail"]

@pytest.mark.asyncio
async def test_session_quota():
    headers = {"X-API-KEY": PRECONSULT_API_KEY}
    payload = {
        "age_bracket": "26-35",
        "sex": "Female",
        "lang": "en",
        "specialist": "Cardiology",
        "chief_complaint": "Valid complaint",
        "duration": "1 day",
        "smoking": "No",
        "alcohol": "No"
    }

    from preconsult.services.session_service import _memory_limiter
    _memory_limiter.clear()

    async with redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0")) as r:
        await r.flushdb()

        async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for i in range(20):
                resp = await client.post("/api/session/init", json=payload, headers=headers)
                if resp.status_code == 429 and "Too many session requests" in resp.json()["detail"]:
                    await r.delete("rate_limit:init:127.0.0.1")
                    _memory_limiter.delete("rate_limit:init:127.0.0.1")
                    resp = await client.post("/api/session/init", json=payload, headers=headers)

                assert resp.status_code == 200, f"Falhou na iteracao {i}: {resp.status_code} - {resp.text}"

            await r.delete("rate_limit:init:127.0.0.1")
            _memory_limiter.delete("rate_limit:init:127.0.0.1")
            resp21 = await client.post("/api/session/init", json=payload, headers=headers)
            assert resp21.status_code == 429
            assert "Daily session limit reached" in resp21.json()["detail"]


@pytest.mark.asyncio
async def test_rate_limit_fallback_memory():
    import preconsult.services.session_service as srv
    from preconsult.services.session_service import _memory_limiter, check_rate_limit, check_session_quota, increment_session_quota

    srv._redis_available = False
    _memory_limiter.clear()

    assert await check_rate_limit("test-ip", limit=2, window=60) is True
    assert await check_rate_limit("test-ip", limit=2, window=60) is True
    assert await check_rate_limit("test-ip", limit=2, window=60) is False

    assert await check_session_quota("test-quota", limit=20) is True
    for _ in range(20):
        await increment_session_quota("test-quota")
    assert await check_session_quota("test-quota", limit=20) is False

    srv._redis_available = None
    _memory_limiter.clear()


@pytest.mark.asyncio
async def test_concurrent_rate_limit():
    import preconsult.services.session_service as srv
    from preconsult.services.session_service import _memory_limiter
    srv._redis_available = False
    _memory_limiter.clear()

    headers = {"X-API-KEY": PRECONSULT_API_KEY}
    payload = {
        "age_bracket": "26-35",
        "sex": "Female",
        "lang": "en",
        "specialist": "Cardiology",
        "chief_complaint": "Chest pain",
        "duration": "2 days",
        "smoking": "No",
        "alcohol": "No"
    }

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async def req():
            return await client.post("/api/session/init", json=payload, headers=headers)

        results = await asyncio.gather(req(), req(), req(), return_exceptions=True)

    ok_count = sum(1 for r in results if isinstance(r, httpx.Response) and r.status_code == 200)
    limited_count = sum(1 for r in results if isinstance(r, httpx.Response) and r.status_code == 429)

    assert ok_count == 2
    assert limited_count >= 1


@pytest.mark.asyncio
async def test_concurrent_session_quota():
    import preconsult.services.session_service as srv
    from preconsult.services.session_service import _memory_limiter
    srv._redis_available = False
    _memory_limiter.clear()

    headers = {"X-API-KEY": PRECONSULT_API_KEY}
    payload = {
        "age_bracket": "26-35",
        "sex": "Female",
        "lang": "en",
        "specialist": "Cardiology",
        "chief_complaint": "Valid complaint",
        "duration": "1 day",
        "smoking": "No",
        "alcohol": "No"
    }

    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        ok_count = 0
        quota_reached = False

        for i in range(25):
            resp = await client.post("/api/session/init", json=payload, headers=headers)
            if resp.status_code == 200:
                ok_count += 1
            elif resp.status_code == 429:
                detail = resp.json().get("detail", "")
                if "Daily session limit" in detail:
                    quota_reached = True
                    break
                else:
                    _memory_limiter.delete("rate_limit:init:127.0.0.1")
                    resp = await client.post("/api/session/init", json=payload, headers=headers)
                    if resp.status_code == 200:
                        ok_count += 1
                    else:
                        break

    assert ok_count == 20, f"Esperado 20 OK, obtido {ok_count}"
    assert quota_reached, "Quota diaria deveria ter sido atingida"
