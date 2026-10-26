"""Session-creation logging must not leak the full session UUID.

The session id is a bearer-ish handle; logging it whole lets anyone reading the
logs hijack a live 30-minute session. Only an 8-char prefix (matching the
`session_id_short` style in `api/endpoints.py`) is allowed.
"""

import logging
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from preconsult.services.session_service import create_session

FULL_UUID = uuid.UUID("12345678-1234-4abc-9def-1234567890ab")
PREFIX = str(FULL_UUID)[:8]


@pytest.mark.asyncio
@patch("preconsult.services.session_service.get_redis")
async def test_create_session_logs_only_short_prefix(mock_get_redis, caplog):
    mock_get_redis.return_value = AsyncMock()

    with patch(
        "preconsult.services.session_service.uuid.uuid4", return_value=FULL_UUID
    ):
        with caplog.at_level(logging.INFO):
            session_id = await create_session({"age": "30", "gender": "Male"})

    # The id itself is returned unchanged.
    assert session_id == str(FULL_UUID)

    messages = [record.getMessage() for record in caplog.records]
    combined = "\n".join(messages)

    # The short prefix is logged...
    assert any(PREFIX in message for message in messages)
    # ...but the full UUID never appears in any record.
    assert str(FULL_UUID) not in combined
    for record in caplog.records:
        assert str(FULL_UUID) not in record.getMessage()
