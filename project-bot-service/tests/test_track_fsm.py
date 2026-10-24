"""Тесты для команды /track."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from src.handlers.track_handler import (
    receive_link,
    receive_tags,
    cancel_track,
    is_valid_url,
    extract_tags,
    WAITING_FOR_LINK,
)
from src.clients.scrapper_client import LinkAlreadyExistsError
from telegram.ext import ConversationHandler
from tests.conftest import make_update


class TestUrlValidation:
    """Тесты валидации ссылок."""

    def test_valid_github_url(self):
        assert is_valid_url("https://github.com/user/repo") is True
        assert is_valid_url("http://github.com/user/repo") is True

    def test_valid_stackoverflow_url(self):
        assert is_valid_url("https://stackoverflow.com/questions/123") is True

    def test_invalid_urls(self):
        """Некорректные ссылки отклоняются."""
        assert is_valid_url("tbank://github.com/user/repo") is False
        assert is_valid_url("not-a-url") is False
        assert is_valid_url("https://example.com") is False

    def test_extract_tags(self):
        assert extract_tags("work, bug") == ["work", "bug"]
        assert extract_tags("") == []
        assert extract_tags("/skip") == []

    class TestTrackFlow:
        """Тесты полного потока /track."""

        @pytest.mark.asyncio
        @patch("src.handlers.track_handler.scrapper_client")
        async def test_track_success(self, mock_client, mock_context):
            """Позитивный сценарий: ссылка + теги."""
            update = make_update("https://github.com/user/repo")
            mock_context.user_data["track_url"] = "https://github.com/user/repo"

            mock_result = MagicMock()
            mock_result.id = 1
            mock_result.url = "https://github.com/user/repo"
            mock_result.tags = []
            mock_result.filters = []

            mock_client.register_chat = AsyncMock(return_value=True)
            mock_client.add_link = AsyncMock(return_value=mock_result)

            result = await receive_tags(update, mock_context)

            assert result == ConversationHandler.END
            mock_client.add_link.assert_called_once()
            update.message.reply_text.assert_called_once()
            response_text = update.message.reply_text.call_args[0][0]
            assert "Ссылка добавлена" in response_text
            assert "github.com/user/repo" in response_text

        @pytest.mark.asyncio
        async def test_track_invalid_url(self, mock_context):
            """Некорректная ссылка."""
            update = make_update("tbank://github.com/user/repo")

            result = await receive_link(update, mock_context)

            assert result == WAITING_FOR_LINK
            update.message.reply_text.assert_called_once()
            response_text = update.message.reply_text.call_args[0][0]
            assert "не похоже на валидную ссылку" in response_text.lower()

    @pytest.mark.asyncio
    @patch("src.handlers.track_handler.scrapper_client")
    async def test_track_already_exists(self, mock_client, mock_context):
        """Ссылка уже отслеживается."""
        update = make_update("https://github.com/user/repo")
        mock_context.user_data["track_url"] = "https://github.com/user/repo"

        mock_client.register_chat = AsyncMock(return_value=True)
        mock_client.add_link = AsyncMock(
            side_effect=LinkAlreadyExistsError("Already exists")
        )

        result = await receive_tags(update, mock_context)

        assert result == ConversationHandler.END
        update.message.reply_text.assert_called_once()
        assert "уже отслеживаете" in update.message.reply_text.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_track_cancel(self, mock_context):
        """Отмена диалога по /cancel."""
        update = make_update("/cancel")

        result = await cancel_track(update, mock_context)

        assert result == ConversationHandler.END
        update.message.reply_text.assert_called_once()
        assert "Отменено" in update.message.reply_text.call_args[0][0]
