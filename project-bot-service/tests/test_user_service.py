import pytest
from src.user_service import UserService
from src.user_repository import UserRepository


class TestUserService:
    """Тестирование UserService."""

    @pytest.fixture
    def user_repository(self):
        """Фикстура: репозиторий пользователей."""
        return UserRepository()

    @pytest.fixture
    def user_service(self, user_repository):
        """Фикстура: сервис пользователей."""
        return UserService(repository=user_repository)

    def test_welcome_message_contains_help(self, user_service):
        """Приветственное сообщение содержит упоминание /help."""
        message = user_service.get_welcome_message(user_id=12345)

        assert "Добро пожаловать" in message
        assert "/help" in message
        assert isinstance(message, str)

    def test_welcome_message_creates_user(self, user_service, user_repository):
        """При генерации приветствия пользователь создаётся в репозитории."""
        user_id = 999

        user_service.get_welcome_message(user_id=user_id)

        user = user_repository.get_user(user_id)
        assert user is not None
        assert user.id == user_id

    def test_help_message_lists_commands(self, user_service):
        """Справка содержит список команд."""
        message = user_service.get_help_message()

        assert "start" in message
        assert "help" in message

    def test_unknown_message_mentions_help(self, user_service):
        """Сообщение о неизвестной команде предлагает /help."""
        message = user_service.get_unknown_message()

        assert "Неизвестная команда" in message
        assert "/help" in message
