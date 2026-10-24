from pydantic import SecretStr


class TestConfig:
    """Тестирование конфигурации приложения."""

    def test_bot_token_is_secret(self):
        """Токен хранится как SecretStr."""
        from src.config import settings

        assert isinstance(settings.bot_token, SecretStr)

        token_value = settings.bot_token.get_secret_value()
        assert isinstance(token_value, str)
        assert len(token_value) > 0

    def test_required_commands_exist(self):
        """Обязательные команды присутствуют."""
        from src.config import settings

        commands = {cmd["command"] for cmd in settings.bot_commands}

        assert "start" in commands
        assert "help" in commands
