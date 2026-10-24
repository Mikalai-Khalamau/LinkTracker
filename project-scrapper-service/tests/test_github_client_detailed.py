import pytest
import respx
from httpx import Response
from datetime import datetime, timezone

from src.clients.github_client import (
    get_repo_issues_and_prs,
    _truncate_text,
)


class TestTruncateText:
    """Тесты обрезки текста."""

    def test_short_text(self):
        """Короткий текст не обрезается."""
        assert _truncate_text("Hello world", 200) == "Hello world"

    def test_exact_length(self):
        """Текст ровно 200 символов."""
        text = "a" * 200
        assert _truncate_text(text, 200) == text

    def test_long_text(self):
        """Длинный текст обрезается с многоточием."""
        text = "word " * 100
        result = _truncate_text(text, 200)
        assert len(result) <= 203  # 200 + ...
        assert result.endswith("...")

    def test_empty_text(self):
        """Пустой текст."""
        assert _truncate_text("", 200) == ""
        assert _truncate_text(None, 200) == ""

    def test_whitespace_normalization(self):
        """Нормализация пробелов."""
        text = "Hello\n\nWorld\t\tTest"
        assert _truncate_text(text, 200) == "Hello World Test"


class TestGetRepoIssuesAndPrs:
    """Тесты получения Issues и PRs."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_success_with_issues(self):
        """Успешное получение Issues."""
        mock_response = [
            {
                "number": 42,
                "title": "Bug in parser",
                "user": {"login": "john_doe"},
                "created_at": "2024-01-15T10:30:00Z",
                "body": "This is a bug description",
                "html_url": "https://github.com/test/repo/issues/42",
            }
        ]

        respx.get("https://api.github.com/repos/test/repo/issues").mock(
            return_value=Response(200, json=mock_response)
        )

        updates = await get_repo_issues_and_prs("test", "repo")

        assert len(updates) == 1
        assert updates[0].issue_number == 42
        assert updates[0].title == "Bug in parser"
        assert updates[0].author == "john_doe"
        assert updates[0].is_pull_request is False
        assert updates[0].preview == "This is a bug description"

    @respx.mock
    @pytest.mark.asyncio
    async def test_success_with_pull_requests(self):
        """Успешное получение PRs."""
        mock_response = [
            {
                "number": 100,
                "title": "Add new feature",
                "user": {"login": "jane_smith"},
                "created_at": "2024-01-16T12:00:00Z",
                "body": "This PR adds...",
                "html_url": "https://github.com/test/repo/pull/100",
                "pull_request": {"url": "..."},
            }
        ]

        respx.get("https://api.github.com/repos/test/repo/issues").mock(
            return_value=Response(200, json=mock_response)
        )

        updates = await get_repo_issues_and_prs("test", "repo")

        assert len(updates) == 1
        assert updates[0].is_pull_request is True
        assert updates[0].issue_number == 100

    @respx.mock
    @pytest.mark.asyncio
    async def test_long_body_truncated(self):
        """Длинное описание обрезается."""
        long_body = "word " * 100

        mock_response = [
            {
                "number": 1,
                "title": "Test",
                "user": {"login": "user"},
                "created_at": "2024-01-15T10:30:00Z",
                "body": long_body,
                "html_url": "https://github.com/test/repo/issues/1",
            }
        ]

        respx.get("https://api.github.com/repos/test/repo/issues").mock(
            return_value=Response(200, json=mock_response)
        )

        updates = await get_repo_issues_and_prs("test", "repo")

        assert len(updates[0].preview) <= 203
        assert updates[0].preview.endswith("...")

    @respx.mock
    @pytest.mark.asyncio
    async def test_with_since_parameter(self):
        """Фильтрация по дате since."""
        since = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

        mock_response = [
            {
                "number": 1,
                "title": "New issue",
                "user": {"login": "user"},
                "created_at": "2024-01-16T10:30:00Z",
                "body": "Description",
                "html_url": "https://github.com/test/repo/issues/1",
            }
        ]

        route = respx.get("https://api.github.com/repos/test/repo/issues").mock(
            return_value=Response(200, json=mock_response)
        )

        updates = await get_repo_issues_and_prs("test", "repo", since=since)

        assert len(updates) == 1
        assert route.calls[0].request.url.params.get("since") is not None

    @respx.mock
    @pytest.mark.asyncio
    async def test_404_not_found(self):
        """Репозиторий не найден."""
        respx.get("https://api.github.com/repos/test/repo/issues").mock(
            return_value=Response(404)
        )

        updates = await get_repo_issues_and_prs("test", "repo")
        assert updates == []

    @respx.mock
    @pytest.mark.asyncio
    async def test_429_rate_limit(self):
        """Rate limit."""
        respx.get("https://api.github.com/repos/test/repo/issues").mock(
            return_value=Response(429)
        )

        updates = await get_repo_issues_and_prs("test", "repo")
        assert updates == []

    @respx.mock
    @pytest.mark.asyncio
    async def test_empty_response(self):
        """Пустой ответ."""
        respx.get("https://api.github.com/repos/test/repo/issues").mock(
            return_value=Response(200, json=[])
        )

        updates = await get_repo_issues_and_prs("test", "repo")
        assert updates == []

    @respx.mock
    @pytest.mark.asyncio
    async def test_malformed_item(self):
        """Некорректный элемент в ответе."""
        mock_response = [
            {
                "number": 1,
            },
            {
                "number": 2,
                "title": "Valid issue",
                "user": {"login": "user"},
                "created_at": "2024-01-15T10:30:00Z",
                "body": "Description",
                "html_url": "https://github.com/test/repo/issues/2",
            },
        ]

        respx.get("https://api.github.com/repos/test/repo/issues").mock(
            return_value=Response(200, json=mock_response)
        )

        updates = await get_repo_issues_and_prs("test", "repo")

        assert len(updates) == 1
        assert updates[0].issue_number == 2
