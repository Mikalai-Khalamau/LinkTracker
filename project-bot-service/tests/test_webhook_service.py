import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient

from src.webhook_server import create_webhook_app


@pytest.fixture
def mock_bot():
    """Создает мок бота."""
    bot = AsyncMock()
    bot.send_message = AsyncMock(return_value=True)
    return bot


@pytest.fixture
def client(mock_bot):
    """Создает тестовый клиент с моком бота."""
    app = create_webhook_app()
    app.state.bot = mock_bot
    return TestClient(app)


class TestWebhookServer:
    """Тесты обработки входящих уведомлений."""

    def test_health_check(self, client):
        """Проверка health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_handle_update_success(self, client, mock_bot):
        """Успешная обработка уведомления."""
        payload = {
            "chat_id": 123456,
            "text": "New Issue #42: Fix bug\nAuthor: john_doe",
            "parse_mode": "HTML",
        }

        response = client.post("/updates", json=payload)

        assert response.status_code == 200
        assert response.json()["status"] == "received"

        mock_bot.send_message.assert_called_once_with(
            chat_id=123456,
            text="New Issue #42: Fix bug\nAuthor: john_doe",
            parse_mode="HTML",
        )

    def test_handle_update_markdown(self, client, mock_bot):
        """Обработка уведомления в md формате."""
        payload = {"chat_id": 789012, "text": "*Bold text*", "parse_mode": "Markdown"}

        response = client.post("/updates", json=payload)

        assert response.status_code == 200

        mock_bot.send_message.assert_called_once_with(
            chat_id=789012, text="*Bold text*", parse_mode="Markdown"
        )

    def test_handle_update_telegram_error(self, client, mock_bot):
        """Обработка ошибки от Telegram API."""
        mock_bot.send_message.side_effect = Exception(
            "Telegram API Error: chat not found"
        )

        payload = {"chat_id": 999999, "text": "Test message", "parse_mode": "HTML"}

        response = client.post("/updates", json=payload)

        assert response.status_code == 502
        assert "Failed to send message" in response.json()["detail"]

    def test_handle_update_invalid_payload(self, client):
        """Обработка невалидного payload."""
        payload = {
            "text": "Test message"
            # chat_id отсутствует
        }

        response = client.post("/updates", json=payload)

        assert response.status_code == 422

    def test_handle_update_bot_not_initialized(self, client):
        """Обработка случая, когда бот не инициализирован."""
        client.app.state.bot = None

        payload = {"chat_id": 123456, "text": "Test message", "parse_mode": "HTML"}

        response = client.post("/updates", json=payload)

        assert response.status_code == 500
        assert "Bot instance is not initialized" in response.json()["detail"]
