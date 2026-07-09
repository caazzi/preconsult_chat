import pytest
from unittest.mock import patch, AsyncMock
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
    _memory_limiter.clear()

    assert await check_rate_limit("recovery-ip", limit=2, window=60) is True

    srv._redis_available = None
    _memory_limiter.clear()


@pytest.mark.asyncio
@patch("preconsult.services.session_service.get_redis", return_value=None)
async def test_create_session_redis_unavailable(mock_get_redis):
    session_id = await create_session({"age": "30"})
    assert session_id is not None
    assert isinstance(session_id, str)
    assert len(session_id) > 0


@pytest.mark.asyncio
@patch("preconsult.services.session_service.get_redis", return_value=None)
async def test_get_session_redis_unavailable(mock_get_redis):
    result = await get_session("any-id")
    assert result == {}


@pytest.mark.asyncio
@patch("preconsult.services.session_service.get_redis", return_value=None)
async def test_update_session_redis_unavailable(mock_get_redis):
    result = await update_session("any-id", {"gender": "Female"})
    assert result is None
