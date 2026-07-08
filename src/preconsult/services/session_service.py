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

class MemoryTTLCache:
    def __init__(self, default_ttl: int):
        self._default_ttl = default_ttl
        self._store: Dict[str, tuple[Any, float]] = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        if key in self._store:
            value, expiry = self._store[key]
            if time.monotonic() < expiry:
                return value
            del self._store[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        expiry = time.monotonic() + (ttl or self._default_ttl)
        self._store[key] = (value, expiry)

    def delete(self, key: str):
        self._store.pop(key, None)

    def exists(self, key: str) -> bool:
        return self.get(key) is not None

    def incr(self, key: str) -> int:
        val = self.get(key)
        if val is None:
            val = 0
        new_val = int(val) + 1
        self.set(key, new_val, self._default_ttl)
        return new_val

    def clear(self):
        self._store.clear()

_memory_cache = MemoryTTLCache(SESSION_TTL)

def get_redis() -> redis.Redis:
    global _redis_pool, _redis_available
    if _redis_pool is None:
        try:
            _redis_pool = redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2, socket_timeout=2)
        except Exception:
            _redis_available = False
            logging.error("Falha ao conectar ao Redis. Usando cache em memoria.")
            _redis_pool = None
    return _redis_pool

def is_redis_available() -> bool:
    global _redis_available, _redis_pool
    if _redis_available is False:
        return False
    return True

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

    if is_redis_available():
        try:
            client = get_redis()
            await client.hset(key, mapping=_serialize(data))
            await client.expire(key, SESSION_TTL)
            logging.info(f"Criada sessao {session_id} no Redis")
            return session_id
        except Exception as e:
            logging.error(f"Redis offline ao criar sessao. Usando fallback em memoria: {e}")
            _redis_available = False

    _memory_cache.set(key, data)
    logging.info(f"Criada sessao {session_id} em memoria (fallback)")
    return session_id

async def get_session(session_id: str) -> Dict[str, Any]:
    if not session_id:
        return {}

    key = f"session:{session_id}"

    if is_redis_available():
        try:
            client = get_redis()
            raw_data = await client.hgetall(key)
            if raw_data:
                await client.expire(key, SESSION_TTL)
                return _deserialize(raw_data)
            return {}
        except Exception as e:
            logging.error(f"Redis offline ao ler sessao. Usando fallback: {e}")
            _redis_available = False

    data = _memory_cache.get(key)
    if data is not None:
        return data
    return {}

async def update_session(session_id: str, new_data: Dict[str, Any]) -> None:
    if not session_id or not new_data:
        return

    key = f"session:{session_id}"

    if is_redis_available():
        try:
            client = get_redis()
            await client.hset(key, mapping=_serialize(new_data))
            await client.expire(key, SESSION_TTL)
            logging.debug(f"Atualizada sessao {session_id} no Redis: {list(new_data.keys())}")
            return
        except Exception as e:
            logging.error(f"Redis offline ao atualizar sessao. Usando fallback: {e}")
            _redis_available = False

    existing = _memory_cache.get(key) or {}
    existing.update(new_data)
    _memory_cache.set(key, existing)

async def check_rate_limit(ip: str, limit: int = 10, window: int = 60) -> bool:
    key = f"rate_limit:{ip}"

    if is_redis_available():
        try:
            client = get_redis()
            count = await client.eval(INCR_EXPIRE_SCRIPT, 1, key, window)
            return count <= limit
        except Exception as e:
            logging.error(f"Redis offline no rate limit. Usando fallback: {e}")
            _redis_available = False

    count = _memory_cache.incr(key)
    return count <= limit

async def check_session_quota(ip: str, limit: int = 20) -> bool:
    key = f"session_quota:{ip}"

    if is_redis_available():
        try:
            client = get_redis()
            count = await client.get(key)
            if count and int(count) >= limit:
                return False
            return True
        except Exception as e:
            logging.error(f"Redis offline no check quota. Usando fallback: {e}")
            _redis_available = False

    count = _memory_cache.get(key)
    if count and int(count) >= limit:
        return False
    return True

async def increment_session_quota(ip: str, window: int = 86400) -> None:
    key = f"session_quota:{ip}"

    if is_redis_available():
        try:
            client = get_redis()
            await client.eval(INCR_EXPIRE_SCRIPT, 1, key, window)
            return
        except Exception as e:
            logging.error(f"Redis offline ao incrementar quota. Usando fallback: {e}")
            _redis_available = False

    _memory_cache.incr(key)
