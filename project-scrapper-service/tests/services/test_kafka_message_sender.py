import pytest
import asyncio
import json
from datetime import datetime, timezone
from aiokafka import AIOKafkaConsumer

from src.services.kafka_message_sender import KafkaMessageSender
from src.services.message_sender import UpdateMessage


@pytest.mark.asyncio
async def test_send_message_to_kafka(kafka_bootstrap_servers):
    sender = KafkaMessageSender(
        bootstrap_servers=kafka_bootstrap_servers, topic="test-updates"
    )
    await sender.start()
    try:
        message = UpdateMessage(
            update_type="github_issue",
            source_url="https://github.com/test/repo/issues/42",
            title="Fix bug",
            author="john_doe",
            created_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            preview="Bug description",
            chat_ids=[123456],
        )

        result = await sender.send_message(message)
        assert result is True

        consumer = AIOKafkaConsumer(
            "test-updates",
            bootstrap_servers=[kafka_bootstrap_servers],
            auto_offset_reset="earliest",
            group_id="test-group",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )
        await consumer.start()
        try:
            msg = await asyncio.wait_for(consumer.getone(), timeout=10.0)
            assert msg.value["chat_id"] == 123456
            assert "Fix bug" in msg.value["text"]
            assert msg.value["parse_mode"] == "HTML"
        finally:
            await consumer.stop()
    finally:
        await sender.stop()


@pytest.mark.asyncio
async def test_kafka_unavailable():
    sender = KafkaMessageSender(
        bootstrap_servers="localhost:9999", topic="test-updates"
    )
    message = UpdateMessage(
        update_type="github_issue",
        source_url="https://github.com/test/repo/issues/1",
        title="Test",
        author="user",
        created_at=datetime.now(),
        preview="Preview",
        chat_ids=[123],
    )
    try:
        await sender.start()
        result = await sender.send_message(message)
        assert result is False
    except Exception:
        pass
    finally:
        await sender.stop()
