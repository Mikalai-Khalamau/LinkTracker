"""Тесты HTTP отправителя уведомлений."""

import pytest
import respx
from httpx import Response
from datetime import datetime, timezone

from src.services.http_message_sender import HttpMessageSender
from src.services.message_sender import UpdateMessage


@pytest.fixture
def sender():
    return HttpMessageSender(bot_callback_url="http://test-bot:8080/updates")


@pytest.fixture
def sample_github_issue():
    return UpdateMessage(
        update_type="github_issue",
        source_url="https://github.com/test/repo/issues/42",
        title="Fix bug in parser",
        author="john_doe",
        created_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        preview="This is a bug description",
        chat_ids=[123456, 789012],
    )


class TestHttpMessageSender:
    @respx.mock
    @pytest.mark.asyncio
    async def test_send_success_to_all_chats(self, sender, sample_github_issue):
        """Успешная отправка всем получателям."""
        respx.post("http://test-bot:8080/updates").mock(
            return_value=Response(200, json={"status": "ok"})
        )

        result = await sender.send_message(sample_github_issue)

        assert result is True
        assert len(respx.calls) == 2

        last_request = respx.calls.last.request
        payload = last_request.content
        assert b"Fix bug in parser" in payload
        assert b"john_doe" in payload

    @respx.mock
    @pytest.mark.asyncio
    async def test_send_partial_failure(self, sender, sample_github_issue):
        """Частичный успех (один чат недоступен)."""
        call_count = 0

        def response_handler(request):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return Response(200, json={"status": "ok"})
            else:
                return Response(500, text="Internal error")

        respx.post("http://test-bot:8080/updates").mock(side_effect=response_handler)

        result = await sender.send_message(sample_github_issue)

        assert result is False
        assert len(respx.calls) == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_send_network_error(self, sender, sample_github_issue):
        """Сетевая ошибка."""
        respx.post("http://test-bot:8080/updates").mock(
            side_effect=Exception("Connection refused")
        )

        result = await sender.send_message(sample_github_issue)
        assert result is False

    @respx.mock
    @pytest.mark.asyncio
    async def test_send_empty_chat_ids(self, sender):
        """Пустой список получателей."""
        message = UpdateMessage(
            update_type="github_issue",
            source_url="https://github.com/test/repo/issues/1",
            title="Test",
            author="user",
            created_at=datetime.now(),
            preview="Preview",
            chat_ids=[],
        )

        result = await sender.send_message(message)

        assert result is True
        assert len(respx.calls) == 0

    def test_extract_number_from_github_url(self, sender):
        assert sender._extract_number("https://github.com/user/repo/issues/42") == 42
        assert sender._extract_number("https://github.com/user/repo/pull/100") == 100

    def test_extract_number_from_so_url(self, sender):
        assert sender._extract_number("https://stackoverflow.com/a/67890") == 67890

    def test_extract_number_invalid_url(self, sender):
        assert sender._extract_number("https://example.com") == 0
