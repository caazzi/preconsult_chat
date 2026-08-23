import asyncio
import os
import json
import uuid
import logging
import time
from typing import Dict, Any, Optional
from collections import OrderedDict
import redis.asyncio as redis

from preconsult.core.errors import RedisUnavailableError, RedisQuotaExceededError
from preconsult.core.observability import log_event, new_request_id

SESSION_TTL = 30 * 60

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

_redis_pool = None
_redis_available: Optional[bool] = None

# Best-effort in-memory session store used when Redis is down/unavailable so a
# transient storage outage degrades gracefully instead of hard-failing. Per
# instance, so it cannot span workers — it is a resilience shim, not a store of
# truth (the README's model keeps ephemeral session state server-side in Redis).
_memory_sessions: Dict[str, Dict[str, Any]] = {}
_memory_sessions_lock = asyncio.Lock()

INCR_EXPIRE_SCRIPT = """
local key = KEYS[1]
local window = tonumber(ARGV[1])
local count = redis.call('INCR', key)
if count == 1 then
    redis.call('EXPIRE', key, window)
end
return count
"""


def _is_quota_error(exc: BaseException) -> bool:
    """Whether a redis error is an Upstash request-quota exhaustion.

    Upstash raises ``ResponseError`` whose message contains
    ``max requests limit exceeded``. Quota exhaustion is distinct from a general
    outage: it is intentional, resets daily, and deserves its own alert/signal.
    """
    return "max requests limit" in str(exc).lower()


def _mark_quota_exceeded(where: str) -> None:
    global _redis_available
    _redis_available = False
    log_event(
        logging.ERROR,
        "redis.quota_exceeded",
        request_id=new_request_id(),
        where=where,
    )


def _mark_redis_down(where: str) -> None:
    global _redis_available
    _redis_available = False
    log_event(
        logging.WARNING,
        "redis.unavailable",
        request_id=new_request_id(),
        where=where,
    )


class MemoryRateLimitStore:
    def __init__(self):
        self._store: Dict[str, tuple[int, float]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def incr(self, key: str, window: int) -> int:
        async with self._lock:
            now = time.monotonic()
            if key in self._store:
                count, expiry = self._store[key]
                if now < expiry:
                    new_count = count + 1
                    self._store[key] = (new_count, expiry)
                    return new_count
            self._store[key] = (1, now + window)
            return 1

    async def get(self, key: str) -> Optional[int]:
        async with self._lock:
            if key in self._store:
                count, expiry = self._store[key]
                if time.monotonic() < expiry:
                    return count
                del self._store[key]
            return None

    async def delete(self, key: str):
        async with self._lock:
            self._store.pop(key, None)

    async def clear(self):
        async with self._lock:
            self._store.clear()


_memory_limiter = MemoryRateLimitStore()


def get_redis() -> Optional[redis.Redis]:
    global _redis_pool, _redis_available
    if _redis_available is False:
        return None
    if _redis_pool is None:
        try:
            _redis_pool = redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2, socket_timeout=2)
        except Exception:
            _redis_available = False
            logging.error("Redis indisponivel. Usando fallback em memoria.")
            _redis_pool = None
            return None
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
    if client is not None:
        try:
            await client.hset(key, mapping=_serialize(data))
            await client.expire(key, SESSION_TTL)
            logging.info(f"Criada sessao {session_id} no Redis")
            return session_id
        except Exception as e:
            if _is_quota_error(e):
                _mark_quota_exceeded("create_session")
                raise RedisQuotaExceededError() from e
            _mark_redis_down("create_session")
            logging.error(f"Redis indisponivel ao criar sessao, usando memoria: {e}")
    else:
        logging.info(f"Sessao {session_id} criada em memoria (Redis indisponivel)")

    # Best-effort in-memory persistence so the same worker can read it back.
    async with _memory_sessions_lock:
        _memory_sessions[session_id] = dict(_serialize(data))
    return session_id


async def get_session(session_id: str) -> Dict[str, Any]:
    if not session_id:
        return {}

    client = get_redis()
    key = f"session:{session_id}"

    async def _memory_lookup() -> Dict[str, Any]:
        async with _memory_sessions_lock:
            raw = _memory_sessions.get(session_id)
        return _deserialize(raw) if raw else {}

    if client is None:
        data = await _memory_lookup()
        if not data:
            # Redis unavailable and we have no in-memory copy: surface the real
            # cause (redis_unavailable) rather than a misleading session_expired.
            raise RedisUnavailableError()
        return data

    try:
        raw_data = await client.hgetall(key)
    except Exception as e:
        if _is_quota_error(e):
            _mark_quota_exceeded("get_session")
            raise RedisQuotaExceededError() from e
        _mark_redis_down("get_session")
        logging.error(f"Redis indisponivel ao ler sessao, usando memoria: {e}")
        data = await _memory_lookup()
        if not data:
            raise RedisUnavailableError() from e
        return data

    if raw_data:
        await client.expire(key, SESSION_TTL)
        return _deserialize(raw_data)
    # Genuine miss in Redis; fall back to the (per-worker) in-memory shim.
    return await _memory_lookup()


async def update_session(session_id: str, new_data: Dict[str, Any]) -> None:
    if not session_id or not new_data:
        return

    client = get_redis()
    key = f"session:{session_id}"
    if client is not None:
        try:
            await client.hset(key, mapping=_serialize(new_data))
            await client.expire(key, SESSION_TTL)
            logging.debug(f"Atualizada sessao {session_id} no Redis: {list(new_data.keys())}")
            return
        except Exception as e:
            if _is_quota_error(e):
                _mark_quota_exceeded("update_session")
                raise RedisQuotaExceededError() from e
            _mark_redis_down("update_session")
            logging.error(f"Redis indisponivel ao atualizar sessao, usando memoria: {e}")

    async with _memory_sessions_lock:
        existing = _memory_sessions.get(session_id, {})
        existing.update(_serialize(new_data))
        _memory_sessions[session_id] = existing

async def check_redis_status() -> str:
    """Probe Redis and return a stable status: ``ok`` | ``quota_exceeded`` | ``unavailable``.

    Used by /health and /health/ready so an exhausted Upstash quota is surfaced
    explicitly (quota_exceeded) instead of being reported as a generic outage.
    """
    global _redis_available
    client = get_redis()
    if client is None:
        if not _reconnect_redis():
            return "unavailable"
        client = get_redis()
        if client is None:
            return "unavailable"
    try:
        pong = await client.ping()
        ok = bool(pong)
        _redis_available = ok
        if not ok:
            log_event(logging.WARNING, "redis.ping_failed", request_id=new_request_id())
        return "ok" if ok else "unavailable"
    except Exception as e:
        _redis_available = False
        if _is_quota_error(e):
            _mark_quota_exceeded("health")
            return "quota_exceeded"
        logging.error(f"Redis ping falhou: {e}")
        return "unavailable"


async def check_redis_health() -> bool:
    """Probe Redis and return whether it is reachable and healthy.

    ``check_redis_status() == 'ok'``. Retained as a convenience bool for the
    throttled health path and existing callers.
    """
    return (await check_redis_status()) == "ok"


def _reconnect_redis() -> bool:
    """Reset the failure latch and rebuild the pool to retry Redis.

    Returns True if a fresh pool handle is available to try, else False.
    """
    global _redis_pool, _redis_available
    try:
        _redis_pool = redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2, socket_timeout=2)
        _redis_available = None
        return True
    except Exception as e:
        logging.error(f"Reconexao Redis falhou: {e}")
        _redis_pool = None
        _redis_available = False
        return False


async def _try_redis(fn, fallback_fn):
    global _redis_available
    client = get_redis()
    if client is not None:
        try:
            result = await fn(client)
            _redis_available = True
            return result
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
        count = await _memory_limiter.incr(key, window)
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
        count = await _memory_limiter.get(key)
        if count and count >= limit:
            return False
        return True

    return await _try_redis(_redis_check, _fallback_check)

async def increment_session_quota(ip: str, window: int = 86400) -> None:
    key = f"session_quota:{ip}"

    async def _redis_incr(client):
        await client.eval(INCR_EXPIRE_SCRIPT, 1, key, window)

    async def _fallback_incr():
        await _memory_limiter.incr(key, window)

    await _try_redis(_redis_incr, _fallback_incr)
