from telegram import Update

from src.user_repository import UserRepository
from src.user_service import UserService
from src.logger import get_logger

logger = get_logger()
user_repository = UserRepository()
user_service = UserService(user_repository)


async def start_command(update: Update, _context) -> None:
    """Обработчик команды /start."""
    try:
        user_id = update.effective_user.id
        logger.info("command_received", user_id=user_id, command="/start")
        message = user_service.get_welcome_message(user_id)
        await update.message.reply_text(message)
    except Exception as e:
        logger.error("handler_error", handler="start_command", error=e)
        await update.message.reply_text("Произошла ошибка. Попробуйте еще раз.")


async def help_command(update: Update, _context) -> None:
    """Обработчик команды /help."""
    try:
        user_id = update.effective_user.id
        logger.info("command_received", user_id=user_id, command="/help")
        message = user_service.get_help_message()
        await update.message.reply_text(message)
    except Exception as e:
        logger.error("handler_error", handler="help_command", error=e)
        await update.message.reply_text("Произошла ошибка. Попробуйте еще раз.")


async def unknown_command(update: Update, _context) -> None:
    """Обработчик неизвестной команды."""
    try:
        user_id = update.effective_user.id
        command = update.message.text
        logger.warning("unknown_command", user_id=user_id, command=command)
        message = user_service.get_unknown_message()
        await update.message.reply_text(message)
    except Exception as e:
        logger.error("handler_error", handler="unknown_command", error=e)
        await update.message.reply_text("Произошла ошибка. Попробуйте еще раз.")
