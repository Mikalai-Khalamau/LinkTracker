"""Тесты GitHub API клиента."""

import pytest
import respx
from httpx import Response

from src.clients.github_client import parse_github_url, get_repo_last_update


class TestParseGithubUrl:
    """Тесты парсинга GitHub URL."""

    def test_parse_valid_urls(self):
        assert parse_github_url("https://github.com/user/repo") == ("user", "repo")
        assert parse_github_url("https://github.com/user/repo/issues/123") == (
            "user",
            "repo",
        )

    def test_parse_invalid_urls(self):
        assert parse_github_url("https://example.com/user/repo") is None
        assert parse_github_url("https://github.com/user") is None  # нет repo


class TestGetRepoLastUpdate:
    """Тесты получения времени обновления."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_success(self):
        """Успешный ответ от GitHub API."""
        respx.get("https://api.github.com/repos/test/repo").mock(
            return_value=Response(200, json={"pushed_at": "2024-01-15T10:30:00Z"})
        )

        result = await get_repo_last_update("test", "repo")
        assert result is not None

    @respx.mock
    @pytest.mark.asyncio
    async def test_404_not_found(self):
        """Репозиторий не найден."""
        respx.get("https://api.github.com/repos/test/repo").mock(
            return_value=Response(404)
        )
        result = await get_repo_last_update("test", "repo")
        assert result is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_429_rate_limit(self):
        """Rate limit."""
        respx.get("https://api.github.com/repos/test/repo").mock(
            return_value=Response(429)
        )
        result = await get_repo_last_update("test", "repo")
        assert result is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_invalid_response_body(self):
        """Тело не соответствует схеме."""
        respx.get("https://api.github.com/repos/test/repo").mock(
            return_value=Response(200, json={"wrong_field": "value"})
        )
        result = await get_repo_last_update("test", "repo")
        assert result is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_network_error(self):
        """Сетевая ошибка."""
        respx.get("https://api.github.com/repos/test/repo").mock(
            side_effect=Exception("Connection timeout")
        )
        result = await get_repo_last_update("test", "repo")
        assert result is None
