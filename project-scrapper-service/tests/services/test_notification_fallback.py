import pytest
import respx
from httpx import Response
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from src.services.notification_service import (
    send_notification_with_fallback,
    init_sender,
)
from src.services.message_sender import UpdateMessage
from src.services.kafka_message_sender import KafkaMessageSender


@pytest.fixture(autouse=True)
def setup_sender():
    init_sender()


@pytest.mark.asyncio
async def test_fallback_to_kafka_on_http_failure():
    """Падение основного транспорта и переход на Kafka."""
    message = UpdateMessage(
        update_type="github_issue",
        source_url="https://github.com/test/repo/issues/1",
        title="Fallback Test",
        author="user",
        created_at=datetime.now(timezone.utc),
        preview="Preview text",
        chat_ids=[123456],
    )

    with respx.mock:
        respx.post("http://localhost:8080/updates").mock(
            return_value=Response(500, text="Internal Server Error")
        )

        with patch.object(KafkaMessageSender, "start", new_callable=AsyncMock):
            with patch.object(
                KafkaMessageSender,
                "send_message",
                new_callable=AsyncMock,
                return_value=True,
            ):
                result = await send_notification_with_fallback(message)

                assert result is True
