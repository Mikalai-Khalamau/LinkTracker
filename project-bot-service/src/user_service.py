from src.logger import get_logger
from src.user_repository import UserRepository
from src.config import settings

logger = get_logger()


class UserService:
    """Сервис работы с пользователем."""

    def __init__(self, repository: UserRepository):
        self._repository = repository

    def get_welcome_message(self, user_id: int) -> str:
        """Возвращает приветственное сообщение."""
        user = self._repository.get_or_create(user_id)
        logger.info("welcome_message_generated", user_id=user.id)
        return "Добро пожаловать! Используйте /help для просмотра доступных команд."

    @staticmethod
    def get_help_message() -> str:
        """Возвращает справку по командам."""
        commands = settings.bot_commands

        if not commands:
            return "Нет доступных команд."

        command_lines = [f"{cmd['command']} - {cmd['description']}" for cmd in commands]

        header = "Доступные команды:\n\n"
        body = "\n".join(command_lines)

        return header + body

    @staticmethod
    def get_unknown_message() -> str:
        """Сообщение о неизвестной команде."""
        return "Неизвестная команда. Воспользуйтесь /help, чтобы узнать список доступных команд."
