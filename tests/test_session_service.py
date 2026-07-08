import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from preconsult.services.session_service import create_session, get_session, update_session

@pytest.mark.asyncio
@patch("preconsult.services.session_service.get_redis")
async def test_create_session(mock_get_redis):
    from preconsult.services.session_service import _memory_cache, _redis_pool, _redis_available
    _memory_cache.clear()
    mock_client = AsyncMock()
    mock_get_redis.return_value = mock_client
    
    data = {"age": "30", "gender": "Male"}
    session_id = await create_session(data)
    
    assert session_id is not None
    assert mock_client.hset.called
    assert mock_client.expire.called
    _memory_cache.clear()

@pytest.mark.asyncio
@patch("preconsult.services.session_service.get_redis")
async def test_get_session_success(mock_get_redis):
    from preconsult.services.session_service import _memory_cache
    _memory_cache.clear()
    mock_client = AsyncMock()
    mock_get_redis.return_value = mock_client
    
    fake_data = {"age": "35"}
    mock_client.hgetall.return_value = fake_data
    
    result = await get_session("fake-id")
    assert result == fake_data
    assert mock_client.expire.called
    _memory_cache.clear()

@pytest.mark.asyncio
@patch("preconsult.services.session_service.get_redis")
async def test_get_session_not_found(mock_get_redis):
    from preconsult.services.session_service import _memory_cache
    _memory_cache.clear()
    mock_client = AsyncMock()
    mock_get_redis.return_value = mock_client
    mock_client.hgetall.return_value = {}
    
    result = await get_session("invalid-id")
    assert result == {}
    _memory_cache.clear()

@pytest.mark.asyncio
@patch("preconsult.services.session_service.get_redis")
async def test_update_session(mock_get_redis):
    from preconsult.services.session_service import _memory_cache
    _memory_cache.clear()
    mock_client = AsyncMock()
    mock_get_redis.return_value = mock_client
    
    await update_session("fake-id", {"gender": "Female"})
    
    assert mock_client.hset.called
    assert mock_client.expire.called
    _memory_cache.clear()
