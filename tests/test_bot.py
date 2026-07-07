import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from src.infrastructure.telegram.bot import (
    is_authorized,
    authorized_users,
    cmd_start,
    check_auth,
    cmd_setchannel,
    cmd_addsource,
    cmd_sources
)
from src.domain.entities import Source

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

@pytest.mark.asyncio
@patch("src.infrastructure.telegram.bot.is_authorized", return_value=True)
@patch("src.infrastructure.telegram.bot.os.path.exists", return_value=True)
@patch("src.infrastructure.telegram.bot.open")
@patch("src.infrastructure.telegram.bot.yaml.safe_load")
@patch("src.infrastructure.telegram.bot.yaml.dump")
async def test_cmd_setchannel_updates_config(
    mock_dump: MagicMock,
    mock_safe_load: MagicMock,
    mock_open: MagicMock,
    mock_exists: MagicMock,
    mock_auth: MagicMock
) -> None:
    message = AsyncMock()
    message.text = "/setchannel @new_target_channel"
    message.answer = AsyncMock()
    
    mock_safe_load.return_value = {"publisher": {"telegram": {"channel_id": "@old"}}}
    
    await cmd_setchannel(message)
    
    message.answer.assert_called_once()
    assert "@new_target_channel" in message.answer.call_args[0][0]
    mock_dump.assert_called_once()

@pytest.mark.asyncio
@patch("src.infrastructure.telegram.bot.is_authorized", return_value=True)
@patch("src.infrastructure.telegram.bot.async_session_maker")
async def test_cmd_addsource_saves_source(
    mock_session_maker: MagicMock,
    mock_auth: MagicMock
) -> None:
    message = AsyncMock()
    message.text = "/addsource @durov"
    message.answer = AsyncMock()
    
    mock_session = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session_maker.return_value.__aenter__.return_value = mock_session
    
    mock_source_repo = MagicMock()
    mock_source_repo.find_all_active = AsyncMock(return_value=[])
    mock_source_repo.save = AsyncMock()
    
    with patch("src.infrastructure.telegram.bot.SqlAlchemySourceRepository", return_value=mock_source_repo):
        await cmd_addsource(message)
        
        message.answer.assert_called_once()
        assert "успешно добавлен" in message.answer.call_args[0][0]
        mock_source_repo.save.assert_called_once()
        mock_session.commit.assert_called_once()

@pytest.mark.asyncio
@patch("src.infrastructure.telegram.bot.is_authorized", return_value=True)
@patch("src.infrastructure.telegram.bot.async_session_maker")
async def test_cmd_sources_lists_sources(
    mock_session_maker: MagicMock,
    mock_auth: MagicMock
) -> None:
    message = AsyncMock()
    message.text = "/sources"
    message.answer = AsyncMock()
    
    mock_session = MagicMock()
    mock_session_maker.return_value.__aenter__.return_value = mock_session
    
    mock_source = Source(
        id=uuid.uuid4(),
        name="@durov",
        type="TELEGRAM",
        config={"channel_handle": "@durov"},
        status="ACTIVE"
    )
    
    mock_source_repo = MagicMock()
    mock_source_repo.find_all_active = AsyncMock(return_value=[mock_source])
    
    with patch("src.infrastructure.telegram.bot.SqlAlchemySourceRepository", return_value=mock_source_repo):
        await cmd_sources(message)
        
        message.answer.assert_called_once()
        assert "Активные источники контента" in message.answer.call_args[0][0]
        assert "@durov" in message.answer.call_args[0][0]
