"""Тесты пакетной обработки в scheduler."""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

from src.models import LinkDomain
from src.scheduler.update_checker import run_scheduler


@pytest.fixture
def mock_link_repo():
    """Создает мок репозитория ссылок."""
    repo = AsyncMock()
    repo.get_all_for_check = AsyncMock(return_value=[])
    repo.update_last_checked = AsyncMock(return_value=True)
    return repo


@pytest.fixture
def mock_message_sender():
    """Создает мок отправителя."""
    sender = AsyncMock()
    sender.send_message = AsyncMock(return_value=True)
    return sender


class TestBatchProcessing:
    """Тесты пакетной обработки."""

    @pytest.mark.asyncio
    async def test_scheduler_processes_batch(self, mock_link_repo, mock_message_sender):
        """Scheduler обрабатывает пакет ссылок."""
        links = [
            LinkDomain(
                id=i,
                chat_id=123456,
                url=f"https://github.com/test/repo{i}",
                tags=[],
                filters=[],
                last_checked=datetime(2024, 1, 14, 10, 0, 0, tzinfo=timezone.utc),
            )
            for i in range(5)
        ]

        mock_link_repo.get_all_for_check.return_value = links

        with patch("src.scheduler.update_checker.settings") as mock_settings:
            mock_settings.check_interval = 60
            mock_settings.batch_size = 100
            mock_settings.github_token = None

            async def cancel_after_first_iteration(*args):
                raise asyncio.CancelledError()

            with patch("asyncio.sleep", side_effect=cancel_after_first_iteration):
                try:
                    await run_scheduler(mock_link_repo, mock_message_sender)
                except asyncio.CancelledError:
                    pass

        mock_link_repo.get_all_for_check.assert_called_once_with(limit=100)

    @pytest.mark.asyncio
    async def test_scheduler_handles_empty_batch(
        self, mock_link_repo, mock_message_sender
    ):
        """Scheduler корректно обрабатывает пустой пакет."""
        mock_link_repo.get_all_for_check.return_value = []

        with patch("src.scheduler.update_checker.settings") as mock_settings:
            mock_settings.check_interval = 60
            mock_settings.batch_size = 100

            async def cancel_after_first_iteration(*args):
                raise asyncio.CancelledError()

            with patch("asyncio.sleep", side_effect=cancel_after_first_iteration):
                try:
                    await run_scheduler(mock_link_repo, mock_message_sender)
                except asyncio.CancelledError:
                    pass

        mock_link_repo.get_all_for_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_scheduler_isolates_errors(self, mock_link_repo, mock_message_sender):
        """Scheduler изолирует ошибки между ссылками."""
        links = [
            LinkDomain(
                id=1,
                chat_id=123,
                url="https://github.com/test/repo1",
                tags=[],
                filters=[],
                last_checked=datetime(2024, 1, 14, 10, 0, 0, tzinfo=timezone.utc),
            ),
            LinkDomain(
                id=2,
                chat_id=123,
                url="https://github.com/test/repo2",
                tags=[],
                filters=[],
                last_checked=datetime(2024, 1, 14, 10, 0, 0, tzinfo=timezone.utc),
            ),
        ]

        mock_link_repo.get_all_for_check.return_value = links

        with patch("src.scheduler.update_checker.check_link_for_updates") as mock_check:
            mock_check.side_effect = [
                Exception("API error"),
                True,
            ]

            with patch("src.scheduler.update_checker.settings") as mock_settings:
                mock_settings.check_interval = 60
                mock_settings.batch_size = 100
                mock_settings.github_token = None

                async def cancel_after_first_iteration(*args):
                    raise asyncio.CancelledError()

                with patch("asyncio.sleep", side_effect=cancel_after_first_iteration):
                    try:
                        await run_scheduler(mock_link_repo, mock_message_sender)
                    except asyncio.CancelledError:
                        pass

        assert mock_check.call_count == 2
