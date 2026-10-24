"""Общие фикстуры для тестов бота."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from telegram import User
from testcontainers.kafka import KafkaContainer


def make_update(text: str, user_id: int = 12345):
    """Создаёт тестовый Update с полностью замоканым Message."""
    user = User(id=user_id, first_name="Test", is_bot=False)

    message = MagicMock()
    message.reply_text = AsyncMock()
    message.text = text
    message.from_user = user
    message.message_id = 1
    message.date = None
    message.chat = None

    update = MagicMock()
    update.update_id = 1
    update.message = message
    update.effective_user = user

    return update


@pytest.fixture
def mock_context():
    """Фикстура: мок контекста для хендлеров."""
    context = MagicMock()
    context.args = []
    context.user_data = {}
    return context


@pytest.fixture(scope="session")
def kafka_container():
    with KafkaContainer("confluentinc/cp-kafka:7.6.0") as kafka:
        yield kafka


@pytest.fixture(scope="session")
def kafka_bootstrap_servers(kafka_container):
    return kafka_container.get_bootstrap_server()
