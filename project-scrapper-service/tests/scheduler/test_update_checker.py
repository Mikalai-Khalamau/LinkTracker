"""Тесты планировщика проверки обновлений."""

import pytest
import respx
from httpx import Response
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from src.scheduler.update_checker import (
    classify_url,
    check_link_for_updates,
    process_github_link,
    process_stackoverflow_link,
)
from src.models import LinkDomain
from src.services.message_sender import MessageSenderProtocol


@pytest.fixture
def mock_message_sender():
    """Создает мок отправителя уведомлений."""
    sender = AsyncMock(spec=MessageSenderProtocol)
    sender.send_message = AsyncMock(return_value=True)
    return sender


@pytest.fixture
def mock_link_repo():
    """Создает мок репозитория ссылок."""
    repo = AsyncMock()
    repo.update_last_checked = AsyncMock(return_value=True)
    return repo


@pytest.fixture
def sample_github_link():
    """Пример GitHub ссылки."""
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
def sample_so_link():
    """Пример StackOverflow ссылки."""
    return LinkDomain(
        id=2,
        chat_id=789012,
        url="https://stackoverflow.com/questions/12345/test-question",
        tags=["python"],
        filters=[],
        last_checked=datetime(2024, 1, 14, 10, 0, 0, tzinfo=timezone.utc),
        last_updated=None,
    )


class TestClassifyUrl:
    """Тесты классификации URL."""

    def test_github_url(self):
        assert classify_url("https://github.com/user/repo") == "github"
        assert classify_url("https://www.github.com/user/repo") == "github"

    def test_stackoverflow_url(self):
        assert (
            classify_url("https://stackoverflow.com/questions/123") == "stackoverflow"
        )
        assert (
            classify_url("https://www.stackoverflow.com/questions/123")
            == "stackoverflow"
        )

    def test_unsupported_url(self):
        assert classify_url("https://example.com") is None
        assert classify_url("https://gitlab.com/user/repo") is None


class TestProcessGithubLink:
    """Тесты обработки GitHub ссылок."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_process_with_new_issues(
        self, sample_github_link, mock_message_sender
    ):
        """Обработка ссылки с новыми Issues."""
        mock_response = [
            {
                "number": 42,
                "title": "Fix bug",
                "user": {"login": "john_doe"},
                "created_at": "2024-01-15T10:30:00Z",
                "body": "Bug description",
                "html_url": "https://github.com/test/repo/issues/42",
            }
        ]

        respx.get("https://api.github.com/repos/test/repo/issues").mock(
            return_value=Response(200, json=mock_response)
        )

        updates = await process_github_link(
            link=sample_github_link,
            message_sender=mock_message_sender,
        )

        assert len(updates) == 1
        assert updates[0].issue_number == 42

        mock_message_sender.send_message.assert_called_once()

        call_args = mock_message_sender.send_message.call_args
        message = call_args[0][0]
        assert message.update_type == "github_issue"
        assert message.title == "Fix bug"
        assert message.author == "john_doe"

    @respx.mock
    @pytest.mark.asyncio
    async def test_process_with_pull_requests(
        self, sample_github_link, mock_message_sender
    ):
        """Обработка ссылки с новыми PR."""
        mock_response = [
            {
                "number": 100,
                "title": "Add feature",
                "user": {"login": "jane_smith"},
                "created_at": "2024-01-16T12:00:00Z",
                "body": "PR description",
                "html_url": "https://github.com/test/repo/pull/100",
                "pull_request": {"url": "..."},
            }
        ]

        respx.get("https://api.github.com/repos/test/repo/issues").mock(
            return_value=Response(200, json=mock_response)
        )

        updates = await process_github_link(
            link=sample_github_link,
            message_sender=mock_message_sender,
        )

        assert len(updates) == 1
        assert updates[0].is_pull_request is True

        call_args = mock_message_sender.send_message.call_args
        message = call_args[0][0]
        assert message.update_type == "github_pr"

    @respx.mock
    @pytest.mark.asyncio
    async def test_process_no_updates(self, sample_github_link, mock_message_sender):
        """Обработка ссылки без новых обновлений."""
        respx.get("https://api.github.com/repos/test/repo/issues").mock(
            return_value=Response(200, json=[])
        )

        updates = await process_github_link(
            link=sample_github_link,
            message_sender=mock_message_sender,
        )

        assert len(updates) == 0
        mock_message_sender.send_message.assert_not_called()

    @respx.mock
    @pytest.mark.asyncio
    async def test_process_multiple_updates(
        self, sample_github_link, mock_message_sender
    ):
        """Обработка ссылки с несколькими обновлениями."""
        mock_response = [
            {
                "number": 1,
                "title": "Issue 1",
                "user": {"login": "user1"},
                "created_at": "2024-01-15T10:00:00Z",
                "body": "Description 1",
                "html_url": "https://github.com/test/repo/issues/1",
            },
            {
                "number": 2,
                "title": "Issue 2",
                "user": {"login": "user2"},
                "created_at": "2024-01-15T11:00:00Z",
                "body": "Description 2",
                "html_url": "https://github.com/test/repo/issues/2",
            },
        ]

        respx.get("https://api.github.com/repos/test/repo/issues").mock(
            return_value=Response(200, json=mock_response)
        )

        updates = await process_github_link(
            link=sample_github_link,
            message_sender=mock_message_sender,
        )

        assert len(updates) == 2
        assert mock_message_sender.send_message.call_count == 2


class TestProcessStackOverflowLink:
    """Тесты обработки StackOverflow ссылок."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_process_with_new_answers(self, sample_so_link, mock_message_sender):
        """Обработка ссылки с новыми ответами."""
        respx.get("https://api.stackexchange.com/2.3/questions/12345").mock(
            return_value=Response(
                200,
                json={"items": [{"title": "How to parse JSON?"}]},
            )
        )

        mock_response = {
            "items": [
                {
                    "answer_id": 67890,
                    "owner": {"display_name": "Expert User"},
                    "creation_date": 1705315800,
                    "body": "<p>Use json.loads()</p>",
                }
            ]
        }

        respx.get("https://api.stackexchange.com/2.3/questions/12345/answers").mock(
            return_value=Response(200, json=mock_response)
        )

        updates = await process_stackoverflow_link(
            link=sample_so_link,
            message_sender=mock_message_sender,
        )

        assert len(updates) == 1
        assert updates[0].answer_id == 67890

        mock_message_sender.send_message.assert_called_once()
        call_args = mock_message_sender.send_message.call_args
        message = call_args[0][0]
        assert message.update_type == "stackoverflow_answer"
        assert message.title == "How to parse JSON?"

    @respx.mock
    @pytest.mark.asyncio
    async def test_process_no_answers(self, sample_so_link, mock_message_sender):
        """Обработка ссылки без новых ответов."""
        respx.get("https://api.stackexchange.com/2.3/questions/12345").mock(
            return_value=Response(
                200,
                json={"items": [{"title": "Question"}]},
            )
        )

        respx.get("https://api.stackexchange.com/2.3/questions/12345/answers").mock(
            return_value=Response(200, json={"items": []})
        )

        updates = await process_stackoverflow_link(
            link=sample_so_link,
            message_sender=mock_message_sender,
        )

        assert len(updates) == 0
        mock_message_sender.send_message.assert_not_called()


class TestCheckLinkForUpdates:
    """Тесты полной проверки ссылки."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_github_link_with_updates(
        self, sample_github_link, mock_link_repo, mock_message_sender
    ):
        """GitHub ссылка с обновлениями."""
        mock_response = [
            {
                "number": 42,
                "title": "Fix bug",
                "user": {"login": "john_doe"},
                "created_at": "2024-01-15T10:30:00Z",
                "body": "Description",
                "html_url": "https://github.com/test/repo/issues/42",
            }
        ]

        respx.get("https://api.github.com/repos/test/repo/issues").mock(
            return_value=Response(200, json=mock_response)
        )

        result = await check_link_for_updates(
            link=sample_github_link,
            link_repo=mock_link_repo,
            message_sender=mock_message_sender,
        )

        assert result is True
        mock_link_repo.update_last_checked.assert_called_once()

    @respx.mock
    @pytest.mark.asyncio
    async def test_link_without_updates(
        self, sample_github_link, mock_link_repo, mock_message_sender
    ):
        """Ссылка без обновлений."""
        respx.get("https://api.github.com/repos/test/repo/issues").mock(
            return_value=Response(200, json=[])
        )

        result = await check_link_for_updates(
            link=sample_github_link,
            link_repo=mock_link_repo,
            message_sender=mock_message_sender,
        )

        assert result is False
        mock_link_repo.update_last_checked.assert_not_called()

    @pytest.mark.asyncio
    async def test_unsupported_url(self, mock_link_repo, mock_message_sender):
        """Неподдерживаемый URL."""
        link = LinkDomain(
            id=99,
            chat_id=123,
            url="https://example.com",
            tags=[],
            filters=[],
        )

        result = await check_link_for_updates(
            link=link,
            link_repo=mock_link_repo,
            message_sender=mock_message_sender,
        )

        assert result is False
        mock_link_repo.update_last_checked.assert_not_called()

    @respx.mock
    @pytest.mark.asyncio
    async def test_error_handling(
        self, sample_github_link, mock_link_repo, mock_message_sender
    ):
        """Обработка ошибок API."""
        respx.get("https://api.github.com/repos/test/repo/issues").mock(
            return_value=Response(500, text="Internal error")
        )

        result = await check_link_for_updates(
            link=sample_github_link,
            link_repo=mock_link_repo,
            message_sender=mock_message_sender,
        )

        assert result is False
        mock_link_repo.update_last_checked.assert_not_called()
