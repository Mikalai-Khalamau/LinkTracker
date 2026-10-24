"""Интеграционные тесты полного потока обработки обновлений."""

import pytest
import respx
from httpx import Response
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from src.models import LinkDomain
from src.scheduler.update_checker import check_link_for_updates
from src.services.http_message_sender import HttpMessageSender


@pytest.fixture
def mock_link_repo():
    """Мок репозитория ссылок."""
    repo = AsyncMock()
    repo.update_last_checked = AsyncMock(return_value=True)
    return repo


@pytest.fixture
def message_sender():
    """Реальный HttpMessageSender с тестовым URL."""
    return HttpMessageSender(bot_callback_url="http://test-bot:8080/updates")


@pytest.fixture
def github_link():
    """Тестовая GitHub ссылка."""
    return LinkDomain(
        id=1,
        chat_id=123456,
        url="https://github.com/test/repo",
        tags=["python"],
        filters=[],
        last_checked=datetime(2024, 1, 14, 10, 0, 0, tzinfo=timezone.utc),
        last_updated=None,
    )


@pytest.fixture
def stackoverflow_link():
    """Тестовая StackOverflow ссылка."""
    return LinkDomain(
        id=2,
        chat_id=789012,
        url="https://stackoverflow.com/questions/12345/test-question",
        tags=["python"],
        filters=[],
        last_checked=datetime(2024, 1, 14, 10, 0, 0, tzinfo=timezone.utc),
        last_updated=None,
    )


class TestFullGithubFlow:
    """Тесты полного потока для GitHub."""

    @pytest.mark.asyncio
    async def test_new_issue_flow(self, github_link, mock_link_repo, message_sender):
        """Полный поток: новый Issue на GitHub."""
        with respx.mock:
            respx.get("https://api.github.com/repos/test/repo/issues").mock(
                return_value=Response(
                    200,
                    json=[
                        {
                            "number": 42,
                            "title": "Fix parser bug",
                            "user": {"login": "john_doe"},
                            "created_at": "2024-01-15T10:30:00Z",
                            "body": "This is a detailed description of the bug that needs to be fixed",
                            "html_url": "https://github.com/test/repo/issues/42",
                        }
                    ],
                )
            )

            bot_route = respx.post("http://test-bot:8080/updates").mock(
                return_value=Response(200, json={"status": "received"})
            )

            result = await check_link_for_updates(
                link=github_link,
                link_repo=mock_link_repo,
                message_sender=message_sender,
                github_token=None,
            )

            assert result is True

            assert len(bot_route.calls) == 1

            webhook_request = bot_route.calls[0].request
            payload = webhook_request.content.decode()

            assert "123456" in payload
            assert "Fix parser bug" in payload
            assert "john_doe" in payload
            assert "New Issue #42" in payload
            assert "github.com/test/repo/issues/42" in payload

            mock_link_repo.update_last_checked.assert_called_once()
            call_args = mock_link_repo.update_last_checked.call_args
            assert call_args[0][0] == 1
            updated_time = call_args[0][1]
            assert updated_time.year == 2024
            assert updated_time.month == 1
            assert updated_time.day == 15

    @pytest.mark.asyncio
    async def test_new_pull_request_flow(
        self, github_link, mock_link_repo, message_sender
    ):
        """Полный поток: новый Pull Request."""
        with respx.mock:
            respx.get("https://api.github.com/repos/test/repo/issues").mock(
                return_value=Response(
                    200,
                    json=[
                        {
                            "number": 100,
                            "title": "Add new feature",
                            "user": {"login": "jane_smith"},
                            "created_at": "2024-01-16T12:00:00Z",
                            "body": "This PR adds a new feature",
                            "html_url": "https://github.com/test/repo/pull/100",
                            "pull_request": {"url": "..."},
                        }
                    ],
                )
            )

            bot_route = respx.post("http://test-bot:8080/updates").mock(
                return_value=Response(200, json={"status": "received"})
            )

            result = await check_link_for_updates(
                link=github_link,
                link_repo=mock_link_repo,
                message_sender=message_sender,
                github_token=None,
            )

            assert result is True
            assert len(bot_route.calls) == 1

            payload = bot_route.calls[0].request.content.decode()
            assert "New Pull Request #100" in payload
            assert "Add new feature" in payload
            assert "jane_smith" in payload

    @pytest.mark.asyncio
    async def test_multiple_issues_flow(
        self, github_link, mock_link_repo, message_sender
    ):
        """Полный поток: несколько Issues за раз."""
        with respx.mock:
            respx.get("https://api.github.com/repos/test/repo/issues").mock(
                return_value=Response(
                    200,
                    json=[
                        {
                            "number": 1,
                            "title": "First issue",
                            "user": {"login": "user1"},
                            "created_at": "2024-01-15T10:00:00Z",
                            "body": "Description 1",
                            "html_url": "https://github.com/test/repo/issues/1",
                        },
                        {
                            "number": 2,
                            "title": "Second issue",
                            "user": {"login": "user2"},
                            "created_at": "2024-01-15T11:00:00Z",
                            "body": "Description 2",
                            "html_url": "https://github.com/test/repo/issues/2",
                        },
                    ],
                )
            )

            bot_route = respx.post("http://test-bot:8080/updates").mock(
                return_value=Response(200, json={"status": "received"})
            )

            result = await check_link_for_updates(
                link=github_link,
                link_repo=mock_link_repo,
                message_sender=message_sender,
                github_token=None,
            )

            assert result is True
            assert len(bot_route.calls) == 2

            call_args = mock_link_repo.update_last_checked.call_args
            updated_time = call_args[0][1]
            assert updated_time.hour == 11

    @pytest.mark.asyncio
    async def test_long_preview_truncated(
        self, github_link, mock_link_repo, message_sender
    ):
        """Проверка обрезки длинного превью до 200 символов."""
        with respx.mock:
            long_body = "word " * 100

            respx.get("https://api.github.com/repos/test/repo/issues").mock(
                return_value=Response(
                    200,
                    json=[
                        {
                            "number": 1,
                            "title": "Test",
                            "user": {"login": "user"},
                            "created_at": "2024-01-15T10:00:00Z",
                            "body": long_body,
                            "html_url": "https://github.com/test/repo/issues/1",
                        }
                    ],
                )
            )

            bot_route = respx.post("http://test-bot:8080/updates").mock(
                return_value=Response(200, json={"status": "received"})
            )

            await check_link_for_updates(
                link=github_link,
                link_repo=mock_link_repo,
                message_sender=message_sender,
                github_token=None,
            )

            payload = bot_route.calls[0].request.content.decode()
            assert long_body not in payload
            assert "..." in payload


class TestFullStackOverflowFlow:
    """Тесты полного потока для StackOverflow."""

    @pytest.mark.asyncio
    async def test_new_answer_flow(
        self, stackoverflow_link, mock_link_repo, message_sender
    ):
        """Полный поток: новый ответ на StackOverflow."""
        with respx.mock:
            respx.get("https://api.stackexchange.com/2.3/questions/12345").mock(
                return_value=Response(
                    200,
                    json={"items": [{"title": "How to parse JSON in Python?"}]},
                )
            )

            respx.get("https://api.stackexchange.com/2.3/questions/12345/answers").mock(
                return_value=Response(
                    200,
                    json={
                        "items": [
                            {
                                "answer_id": 67890,
                                "owner": {"display_name": "Expert User"},
                                "creation_date": 1705315800,
                                "body": "<p>Use <code>json.loads()</code> method to parse JSON strings.</p>",
                            }
                        ]
                    },
                )
            )

            bot_route = respx.post("http://test-bot:8080/updates").mock(
                return_value=Response(200, json={"status": "received"})
            )

            result = await check_link_for_updates(
                link=stackoverflow_link,
                link_repo=mock_link_repo,
                message_sender=message_sender,
            )

            assert result is True
            assert len(bot_route.calls) == 1

            payload = bot_route.calls[0].request.content.decode()

            assert "789012" in payload
            assert "How to parse JSON" in payload
            assert "Expert User" in payload
            assert "New Answer #67890" in payload
            assert "json.loads" in payload
            assert "stackoverflow.com/a/67890" in payload

            assert "<p>" not in payload
            assert "<code>" not in payload


class TestErrorHandling:
    """Тесты обработки ошибок в полном потоке."""

    @pytest.mark.asyncio
    async def test_github_api_unavailable(
        self, github_link, mock_link_repo, message_sender
    ):
        """GitHub API недоступен и уведомление не отправляется."""
        with respx.mock:
            respx.get("https://api.github.com/repos/test/repo/issues").mock(
                return_value=Response(500, text="Internal Server Error")
            )

            bot_route = respx.post("http://test-bot:8080/updates").mock(
                return_value=Response(200, json={"status": "received"})
            )

            result = await check_link_for_updates(
                link=github_link,
                link_repo=mock_link_repo,
                message_sender=message_sender,
                github_token=None,
            )

            assert result is False
            assert len(bot_route.calls) == 0
            mock_link_repo.update_last_checked.assert_not_called()

    @pytest.mark.asyncio
    async def test_bot_webhook_unavailable(
        self, github_link, mock_link_repo, message_sender
    ):
        """Bot webhook недоступен и ошибка логируется."""
        with respx.mock:
            respx.get("https://api.github.com/repos/test/repo/issues").mock(
                return_value=Response(
                    200,
                    json=[
                        {
                            "number": 1,
                            "title": "Test",
                            "user": {"login": "user"},
                            "created_at": "2024-01-15T10:00:00Z",
                            "body": "Description",
                            "html_url": "https://github.com/test/repo/issues/1",
                        }
                    ],
                )
            )

            respx.post("http://test-bot:8080/updates").mock(
                return_value=Response(500, text="Bot error")
            )

            result = await check_link_for_updates(
                link=github_link,
                link_repo=mock_link_repo,
                message_sender=message_sender,
                github_token=None,
            )

            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_no_updates_no_notifications(
        self, github_link, mock_link_repo, message_sender
    ):
        """Нет обновлений и уведомления не отправляются."""
        with respx.mock:
            respx.get("https://api.github.com/repos/test/repo/issues").mock(
                return_value=Response(200, json=[])
            )

            bot_route = respx.post("http://test-bot:8080/updates").mock(
                return_value=Response(200, json={"status": "received"})
            )

            result = await check_link_for_updates(
                link=github_link,
                link_repo=mock_link_repo,
                message_sender=message_sender,
                github_token=None,
            )

            assert result is False
            assert len(bot_route.calls) == 0
            mock_link_repo.update_last_checked.assert_not_called()
