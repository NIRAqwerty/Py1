import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.infrastructure.telegram.bot import is_authorized, authorized_users, cmd_start, check_auth

@pytest.mark.asyncio
async def test_bot_is_authorized() -> None:
    authorized_users.clear()
    authorized_users.add(12345)
    
    assert is_authorized(12345) is True
    assert is_authorized(67890) is False

@pytest.mark.asyncio
async def test_bot_cmd_start() -> None:
    message = AsyncMock()
    message.answer = AsyncMock()
    
    await cmd_start(message)
    
    message.answer.assert_called_once()
    args, kwargs = message.answer.call_args
    assert "Telegram AI Publisher Management Bot" in args[0]
    assert kwargs.get("parse_mode") == "HTML"

@pytest.mark.asyncio
async def test_check_auth_denied() -> None:
    authorized_users.clear()
    message = AsyncMock()
    message.from_user.id = 99999
    message.answer = AsyncMock()
    
    result = await check_auth(message)
    assert result is False
    message.answer.assert_called_once()
    assert "Доступ ограничен" in message.answer.call_args[0][0]
