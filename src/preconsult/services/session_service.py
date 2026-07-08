import os
import json
import uuid
import logging
import time
from typing import Dict, Any, Optional
from collections import OrderedDict
import redis.asyncio as redis

SESSION_TTL = 30 * 60

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

_redis_pool = None
_redis_available: Optional[bool] = None

INCR_EXPIRE_SCRIPT = """
local key = KEYS[1]
local window = tonumber(ARGV[1])
local count = redis.call('INCR', key)
if count == 1 then
    redis.call('EXPIRE', key, window)
end
return count
"""


class MemoryRateLimitStore:
    def __init__(self):
        self._store: Dict[str, tuple[int, float]] = OrderedDict()

    def incr(self, key: str, window: int) -> int:
        now = time.monotonic()
        if key in self._store:
            count, expiry = self._store[key]
            if now < expiry:
                new_count = count + 1
                self._store[key] = (new_count, expiry)
                return new_count
        self._store[key] = (1, now + window)
        return 1

    def get(self, key: str) -> Optional[int]:
        if key in self._store:
            count, expiry = self._store[key]
            if time.monotonic() < expiry:
                return count
            del self._store[key]
        return None

    def delete(self, key: str):
        self._store.pop(key, None)

    def clear(self):
        self._store.clear()


_memory_limiter = MemoryRateLimitStore()


def get_redis() -> redis.Redis:
    global _redis_pool, _redis_available
    if _redis_pool is None:
        try:
            _redis_pool = redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2, socket_timeout=2)
        except Exception:
            _redis_available = False
            logging.error("Falha ao conectar ao Redis. Rate limit usara fallback em memoria.")
            _redis_pool = None
    return _redis_pool


def _serialize(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        k: (json.dumps(v) if isinstance(v, (list, dict)) else v)
        for k, v in data.items()
    }


def _deserialize(raw: Dict[str, Any]) -> Dict[str, Any]:
    result = {}
    for k, v in raw.items():
        try:
            parsed = json.loads(v)
            if isinstance(parsed, (list, dict)):
                result[k] = parsed
            else:
                result[k] = v
        except (json.JSONDecodeError, TypeError):
            result[k] = v
    return result

async def create_session(data: Dict[str, Any]) -> str:
    session_id = str(uuid.uuid4())
    key = f"session:{session_id}"

    client = get_redis()
    await client.hset(key, mapping=_serialize(data))
    await client.expire(key, SESSION_TTL)
    logging.info(f"Criada sessao {session_id} no Redis")
    return session_id

async def get_session(session_id: str) -> Dict[str, Any]:
    if not session_id:
        return {}

    client = get_redis()
    key = f"session:{session_id}"
    raw_data = await client.hgetall(key)

    if raw_data:
        await client.expire(key, SESSION_TTL)
        return _deserialize(raw_data)
    return {}

async def update_session(session_id: str, new_data: Dict[str, Any]) -> None:
    if not session_id or not new_data:
        return

    client = get_redis()
    key = f"session:{session_id}"
    await client.hset(key, mapping=_serialize(new_data))
    await client.expire(key, SESSION_TTL)
    logging.debug(f"Atualizada sessao {session_id} no Redis: {list(new_data.keys())}")

async def _try_redis(fn, fallback_fn):
    global _redis_available
    if _redis_available is not False:
        try:
            client = get_redis()
            if client:
                return await fn(client)
        except Exception as e:
            _redis_available = False
            logging.error(f"Redis offline. Usando fallback em memoria: {e}")
    return await fallback_fn()

async def check_rate_limit(ip: str, limit: int = 10, window: int = 60) -> bool:
    key = f"rate_limit:{ip}"

    async def _redis_check(client):
        count = await client.eval(INCR_EXPIRE_SCRIPT, 1, key, window)
        return count <= limit

    async def _fallback_check():
        count = _memory_limiter.incr(key, window)
        return count <= limit

    return await _try_redis(_redis_check, _fallback_check)

async def check_session_quota(ip: str, limit: int = 20) -> bool:
    key = f"session_quota:{ip}"

    async def _redis_check(client):
        count = await client.get(key)
        if count and int(count) >= limit:
            return False
        return True

    async def _fallback_check():
        count = _memory_limiter.get(key)
        if count and count >= limit:
            return False
        return True

    return await _try_redis(_redis_check, _fallback_check)

async def increment_session_quota(ip: str, window: int = 86400) -> None:
    key = f"session_quota:{ip}"

    async def _redis_incr(client):
        await client.eval(INCR_EXPIRE_SCRIPT, 1, key, window)

    async def _fallback_incr():
        _memory_limiter.incr(key, window)

    await _try_redis(_redis_incr, _fallback_incr)
