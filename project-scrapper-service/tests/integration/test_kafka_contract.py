import pytest
import asyncio
import json
from datetime import datetime, timezone
from aiokafka import AIOKafkaConsumer

from src.services.kafka_message_sender import KafkaMessageSender
from src.services.message_sender import UpdateMessage


@pytest.mark.asyncio
async def test_scrapper_to_kafka_contract(kafka_bootstrap_servers):
    sender = KafkaMessageSender(
        bootstrap_servers=kafka_bootstrap_servers, topic="contract-test-topic"
    )
    await sender.start()

    try:
        message = UpdateMessage(
            update_type="github_issue",
            source_url="https://github.com/test/repo/issues/99",
            title="Contract Test",
            author="tester",
            created_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            preview="Contract preview",
            chat_ids=[555666],
        )

        result = await sender.send_message(message)
        assert result is True

        consumer = AIOKafkaConsumer(
            "contract-test-topic",
            bootstrap_servers=[kafka_bootstrap_servers],
            auto_offset_reset="earliest",
            group_id="contract-test-group",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )
        await consumer.start()
        try:
            msg = await asyncio.wait_for(consumer.getone(), timeout=10.0)
            payload = msg.value

            assert payload["chat_id"] == 555666
            assert payload["parse_mode"] == "HTML"
            assert "Contract Test" in payload["text"]
            assert payload["update_type"] == "github_issue"
            assert payload["author"] == "tester"
        finally:
            await consumer.stop()
    finally:
        await sender.stop()
