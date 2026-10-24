import pytest
import asyncio
import json
from unittest.mock import AsyncMock
from aiokafka import AIOKafkaProducer

from src.kafka_consumer import NotificationConsumer
from src.config import settings


@pytest.mark.asyncio
async def test_consume_valid_message(kafka_bootstrap_servers):
    mock_bot = AsyncMock()
    mock_bot.send_message = AsyncMock(return_value=True)

    original_servers = settings.kafka_bootstrap_servers
    original_topic = settings.kafka_topic_notifications
    original_group = settings.kafka_consumer_group_id

    settings.kafka_bootstrap_servers = kafka_bootstrap_servers
    settings.kafka_topic_notifications = "test-bot-topic"
    settings.kafka_consumer_group_id = "test-group-valid"

    consumer = NotificationConsumer(mock_bot)
    await consumer.start()

    try:
        producer = AIOKafkaProducer(
            bootstrap_servers=[kafka_bootstrap_servers],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await producer.start()
        try:
            payload = {"chat_id": 789012, "text": "New Issue #1", "parse_mode": "HTML"}
            await producer.send_and_wait("test-bot-topic", value=payload)
        finally:
            await producer.stop()

        await asyncio.sleep(3)

        mock_bot.send_message.assert_called_with(
            chat_id=789012, text="New Issue #1", parse_mode="HTML"
        )
    finally:
        await consumer.stop()
        settings.kafka_bootstrap_servers = original_servers
        settings.kafka_topic_notifications = original_topic
        settings.kafka_consumer_group_id = original_group


@pytest.mark.asyncio
async def test_consume_invalid_message(kafka_bootstrap_servers):
    mock_bot = AsyncMock()
    mock_bot.send_message = AsyncMock(return_value=True)

    original_servers = settings.kafka_bootstrap_servers
    original_topic = settings.kafka_topic_notifications
    original_group = settings.kafka_consumer_group_id

    settings.kafka_bootstrap_servers = kafka_bootstrap_servers
    settings.kafka_topic_notifications = "test-bot-topic-invalid"
    settings.kafka_consumer_group_id = "test-group-invalid"

    consumer = NotificationConsumer(mock_bot)
    await consumer.start()

    try:
        producer = AIOKafkaProducer(
            bootstrap_servers=[kafka_bootstrap_servers],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await producer.start()
        try:
            payload = {"invalid_field": "data"}
            await producer.send_and_wait("test-bot-topic-invalid", value=payload)
        finally:
            await producer.stop()

        await asyncio.sleep(2)

        mock_bot.send_message.assert_not_called()
    finally:
        await consumer.stop()
        settings.kafka_bootstrap_servers = original_servers
        settings.kafka_topic_notifications = original_topic
        settings.kafka_consumer_group_id = original_group
