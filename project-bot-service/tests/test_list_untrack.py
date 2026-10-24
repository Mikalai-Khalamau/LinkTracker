"""Тесты команд /list и /untrack."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from src.handlers.list_untrack import list_command, untrack_command
from tests.conftest import make_update


class TestListCommand:
    """Тесты команды /list."""

    @pytest.mark.asyncio
    @patch("src.handlers.list_untrack.scrapper_client")
    async def test_list_with_links(self, mock_client, mock_context):
        """/list: есть активные подписки."""
        update = make_update("/list")

        mock_link = MagicMock()
        mock_link.url = "https://github.com/test/repo"
        mock_link.tags = ["work"]
        mock_link.filters = []
        mock_client.list_links = AsyncMock(return_value=[mock_link])

        await list_command(update, mock_context)

        mock_client.list_links.assert_called_once_with(chat_id=12345, tag=None)
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        assert "https://github.com/test/repo" in call_args

    @pytest.mark.asyncio
    @patch("src.handlers.list_untrack.scrapper_client")
    async def test_list_no_links(self, mock_client, mock_context):
        """/list: нет подписок."""
        update = make_update("/list")
        mock_client.list_links = AsyncMock(return_value=[])

        await list_command(update, mock_context)

        call_args = update.message.reply_text.call_args[0][0]
        assert "нет отслеживаемых ссылок" in call_args.lower()

    @pytest.mark.asyncio
    @patch("src.handlers.list_untrack.scrapper_client")
    async def test_list_with_tag_filter(self, mock_client, mock_context):
        """/list work: фильтр по тегу."""
        update = make_update("/list work")
        mock_context.args = ["work"]

        mock_link = MagicMock()
        mock_link.url = "https://github.com/test/repo"
        mock_link.tags = ["work"]
        mock_link.filters = []
        mock_client.list_links = AsyncMock(return_value=[mock_link])

        await list_command(update, mock_context)

        mock_client.list_links.assert_called_once_with(chat_id=12345, tag="work")


class TestUntrackCommand:
    """Тесты команды /untrack."""

    @pytest.mark.asyncio
    @patch("src.handlers.list_untrack.scrapper_client")
    async def test_untrack_success(self, mock_client, mock_context):
        """Успешное удаление."""
        url = "https://github.com/test/repo"
        update = make_update(f"/untrack {url}")
        mock_context.args = [url]

        mock_client.remove_link = AsyncMock(return_value=True)

        await untrack_command(update, mock_context)

        mock_client.remove_link.assert_called_once_with(chat_id=12345, url=url)
        call_args = update.message.reply_text.call_args[0][0]
        assert "удалена" in call_args.lower()

    @pytest.mark.asyncio
    async def test_untrack_no_url(self, mock_context):
        """Без URL ошибка."""
        update = make_update("/untrack")
        mock_context.args = []

        await untrack_command(update, mock_context)

        call_args = update.message.reply_text.call_args[0][0]
        assert "укажите ссылку" in call_args.lower()
