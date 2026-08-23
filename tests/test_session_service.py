import pytest
from unittest.mock import patch, AsyncMock
from preconsult.core.errors import RedisUnavailableError, RedisQuotaExceededError
from preconsult.services.session_service import create_session, get_session, update_session

@pytest.mark.asyncio
@patch("preconsult.services.session_service.get_redis")
async def test_create_session(mock_get_redis):
    mock_client = AsyncMock()
    mock_get_redis.return_value = mock_client
    
    data = {"age": "30", "gender": "Male"}
    session_id = await create_session(data)
    
    assert session_id is not None
    assert mock_client.hset.called
    assert mock_client.expire.called

@pytest.mark.asyncio
@patch("preconsult.services.session_service.get_redis")
async def test_get_session_success(mock_get_redis):
    mock_client = AsyncMock()
    mock_get_redis.return_value = mock_client
    
    fake_data = {"age": "35"}
    mock_client.hgetall.return_value = fake_data
    
    result = await get_session("fake-id")
    assert result == fake_data
    assert mock_client.expire.called

@pytest.mark.asyncio
@patch("preconsult.services.session_service.get_redis")
async def test_get_session_not_found(mock_get_redis):
    mock_client = AsyncMock()
    mock_get_redis.return_value = mock_client
    mock_client.hgetall.return_value = {}
    
    result = await get_session("invalid-id")
    assert result == {}

@pytest.mark.asyncio
@patch("preconsult.services.session_service.get_redis")
async def test_update_session(mock_get_redis):
    mock_client = AsyncMock()
    mock_get_redis.return_value = mock_client
    
    await update_session("fake-id", {"gender": "Female"})
    
    assert mock_client.hset.called
    assert mock_client.expire.called


@pytest.mark.asyncio
async def test_rate_limit_recovers_after_redis_comes_back():
    import preconsult.services.session_service as srv
    from preconsult.services.session_service import _memory_limiter, check_rate_limit

    srv._redis_available = False
    await _memory_limiter.clear()

    assert await check_rate_limit("recovery-ip", limit=2, window=60) is True

    srv._redis_available = None
    await _memory_limiter.clear()


@pytest.mark.asyncio
@patch("preconsult.services.session_service.get_redis", return_value=None)
async def test_create_session_redis_unavailable(mock_get_redis):
    session_id = await create_session({"age": "30"})
    assert session_id is not None
    assert isinstance(session_id, str)
    assert len(session_id) > 0


@pytest.mark.asyncio
@patch("preconsult.services.session_service.get_redis", return_value=None)
async def test_get_session_redis_unavailable_raises_redis_unavailable(mock_get_redis):
    # Redis is unavailable and there is no in-memory copy: surface the real
    # cause (redis_unavailable), not a misleading session_expired.
    with pytest.raises(RedisUnavailableError):
        await get_session("any-id")


@pytest.mark.asyncio
async def test_get_session_returns_memory_fallback_when_redis_down():
    import preconsult.services.session_service as srv

    # Seed the in-memory shim as if create_session had run during an outage.
    srv._memory_sessions["sess-x"] = (float("inf"), {"chat": None})
    try:
        with patch("preconsult.services.session_service.get_redis", return_value=None):
            result = await get_session("sess-x")
        assert result == {"chat": None}
    finally:
        srv._memory_sessions.clear()


@pytest.mark.asyncio
@patch("preconsult.services.session_service.get_redis")
async def test_get_session_quota_without_memory_copy_raises_quota_exceeded(mock_get_redis):
    """Quota exhausted + no in-memory copy -> surface redis_quota_exceeded."""
    client = AsyncMock()
    client.hgetall.side_effect = Exception("max requests limit exceeded. Limit: 500000")
    mock_get_redis.return_value = client

    with pytest.raises(RedisQuotaExceededError):
        await get_session("any-id")


@pytest.mark.asyncio
@patch("preconsult.services.session_service.get_redis")
async def test_get_session_quota_serves_memory_fallback(mock_get_redis):
    """Quota exhausted but a per-worker in-memory copy exists -> still serve it."""
    import preconsult.services.session_service as srv
    srv._memory_sessions["sess-q"] = (float("inf"), {"gender": "Male"})
    try:
        client = AsyncMock()
        client.hgetall.side_effect = Exception("max requests limit exceeded. Limit: 500000")
        mock_get_redis.return_value = client

        result = await get_session("sess-q")
        assert result == {"gender": "Male"}
    finally:
        srv._memory_sessions.clear()


@pytest.mark.asyncio
@patch("preconsult.services.session_service.get_redis")
async def test_create_session_quota_degrades_to_memory(mock_get_redis):
    """On quota exhaustion create_session must NOT block the user: it stores the
    session in the per-worker memory shim and returns a usable session id."""
    import preconsult.services.session_service as srv
    client = AsyncMock()
    client.hset.side_effect = Exception("ResponseError: max requests limit exceeded. Limit: 500000")
    mock_get_redis.return_value = client

    session_id = await create_session({"gender": "Male"})
    assert session_id
    async with srv._memory_sessions_lock:
        assert session_id in srv._memory_sessions


@pytest.mark.asyncio
@patch("preconsult.services.session_service.get_redis", return_value=None)
async def test_update_session_redis_unavailable(mock_get_redis):
    result = await update_session("any-id", {"gender": "Female"})
    assert result is None


@pytest.mark.asyncio
async def test_check_redis_health_ok_sets_available_true():
    import preconsult.services.session_service as srv

    client = AsyncMock()
    client.ping.return_value = True
    srv._redis_pool = client
    srv._redis_available = None

    assert await srv.check_redis_health() is True
    assert srv._redis_available is True

    srv._redis_pool = None
    srv._redis_available = None


@pytest.mark.asyncio
async def test_check_redis_health_down_sets_available_false():
    import preconsult.services.session_service as srv

    client = AsyncMock()
    client.ping.side_effect = Exception("boom")
    srv._redis_pool = client
    srv._redis_available = None

    assert await srv.check_redis_health() is False
    assert srv._redis_available is False

    srv._redis_pool = None
    srv._redis_available = None


@pytest.mark.asyncio
@patch("preconsult.services.session_service._reconnect_redis", return_value=True)
@patch("preconsult.services.session_service.get_redis")
async def test_check_redis_health_reconnects_when_latched_down(mock_get_redis, mock_reconnect):
    import preconsult.services.session_service as srv

    # First call returns None (latched down), reconnect builds a fresh pool,
    # second call returns a healthy client.
    client = AsyncMock()
    client.ping.return_value = True
    mock_get_redis.side_effect = [None, client]
    srv._redis_available = False

    assert await srv.check_redis_health() is True
    assert srv._redis_available is True
    assert mock_reconnect.called

    srv._redis_pool = None
    srv._redis_available = None


@pytest.mark.asyncio
@patch("preconsult.services.session_service.get_redis", return_value=None)
async def test_memory_fallback_treats_expired_entry_as_gone(mock_get_redis):
    """The in-memory shim must honour the same 30-minute ephemeral contract as
    Redis: an expired entry is treated as a miss (data gone), not served."""
    import preconsult.services.session_service as srv
    srv._memory_sessions["sess-expired"] = (0.0, {"gender": "Male"})  # expires immediately
    try:
        with pytest.raises(RedisUnavailableError):
            await get_session("sess-expired")
        # Expired entry was pruned on access.
        async with srv._memory_sessions_lock:
            assert "sess-expired" not in srv._memory_sessions
    finally:
        srv._memory_sessions.clear()


@pytest.mark.asyncio
@patch("preconsult.services.session_service.get_redis", return_value=None)
async def test_memory_fallback_refreshes_ttl_on_update(mock_get_redis):
    import preconsult.services.session_service as srv
    srv._memory_sessions["sess-upd"] = (float("inf") - 1, {"gender": "Male"})
    try:
        await update_session("sess-upd", {"allergies_flag": True})
        async with srv._memory_sessions_lock:
            entry = srv._memory_sessions["sess-upd"]
        assert entry[1]["allergies_flag"] is True
        # TTL refreshed to the future (not the far-past seed).
        assert entry[0] > 0
    finally:
        srv._memory_sessions.clear()


@pytest.mark.asyncio
@patch("preconsult.services.session_service.get_redis")
async def test_memory_fallback_evicts_oldest_over_cap(mock_get_redis):
    """Past the cap the store evicts the oldest-by-expiry entry so a prolonged
    outage cannot accumulate unbounded session data in a worker's RAM."""
    import preconsult.services.session_service as srv
    client = AsyncMock()
    client.hset.side_effect = Exception("max requests limit exceeded. Limit: 500000")
    mock_get_redis.return_value = client

    srv._memory_sessions.clear()
    try:
        created = []
        for i in range(srv._MEMORY_SESSIONS_MAX + 10):
            sid = await create_session({"gender": str(i)})
            created.append(sid)
        async with srv._memory_sessions_lock:
            assert len(srv._memory_sessions) <= srv._MEMORY_SESSIONS_MAX
            # Newest entries survive the cap.
            assert created[-1] in srv._memory_sessions
    finally:
        srv._memory_sessions.clear()
