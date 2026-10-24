"""Тесты StackOverflow API клиента."""

import pytest
import respx
from httpx import Response

from src.clients.stackoverflow_client import (
    parse_stackoverflow_url,
    get_question_last_activity,
)


class TestParseStackOverflowUrl:
    """Тесты парсинга SO URL."""

    def test_parse_valid_urls(self):
        assert (
            parse_stackoverflow_url("https://stackoverflow.com/questions/12345/title")
            == 12345
        )

    def test_parse_invalid_urls(self):
        assert parse_stackoverflow_url("https://stackoverflow.com/a/12345") is None
        assert parse_stackoverflow_url("https://example.com/questions/123") is None


class TestGetQuestionLastActivity:
    """Тесты получения времени активности."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_success(self):
        """Успешный ответ от SO API."""
        respx.get("https://api.stackexchange.com/2.3/questions/12345").mock(
            return_value=Response(
                200,
                json={
                    "items": [{"question_id": 12345, "last_activity_date": 1705315800}]
                },
            )
        )

        result = await get_question_last_activity(12345)
        assert result is not None

    @respx.mock
    @pytest.mark.asyncio
    async def test_404_not_found(self):
        """Вопрос не найден."""
        respx.get("https://api.stackexchange.com/2.3/questions/999999").mock(
            return_value=Response(404)
        )
        result = await get_question_last_activity(999999)
        assert result is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_429_rate_limit(self):
        """Rate limit."""
        respx.get("https://api.stackexchange.com/2.3/questions/12345").mock(
            return_value=Response(429)
        )
        result = await get_question_last_activity(12345)
        assert result is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_empty_items(self):
        """items пустой."""
        respx.get("https://api.stackexchange.com/2.3/questions/12345").mock(
            return_value=Response(200, json={"items": []})
        )
        result = await get_question_last_activity(12345)
        assert result is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_missing_field(self):
        """Нет last_activity_date."""
        respx.get("https://api.stackexchange.com/2.3/questions/12345").mock(
            return_value=Response(200, json={"items": [{"question_id": 12345}]})
        )
        result = await get_question_last_activity(12345)
        assert result is None
