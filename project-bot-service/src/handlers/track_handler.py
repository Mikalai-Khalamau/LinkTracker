import re
from typing import Final

from telegram import Update
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from src.clients.scrapper_client import (
    scrapper_client,
    LinkAlreadyExistsError,
    ChatNotFoundError,
)
from src.logger import get_logger

logger = get_logger()

WAITING_FOR_LINK: Final = 1
WAITING_FOR_TAGS: Final = 2

ALLOWED_DOMAINS: Final = [
    "github.com",
    "stackoverflow.com",
    "www.github.com",
    "www.stackoverflow.com",
]
URL_PATTERN: Final = re.compile(
    r"^https?://"  # http:// или https://
    r"(?:www\.)?"  # опционально www.
    r"(github\.com|stackoverflow\.com)"  # разрешённые домены
    r"(/[^\s]*)?$"  # опционально путь
)


def is_valid_url(text: str) -> bool:
    """Проверяет, что ссылка валидна и на разрешённом домене."""
    if not text.startswith(("http://", "https://")):
        return False
    return bool(URL_PATTERN.match(text.strip()))


def extract_tags(text: str) -> list[str]:
    """Превращает строку тегов в список."""
    if not text or text.strip() == "/skip":
        return []
    return [tag.strip() for tag in text.split(",") if tag.strip()]


async def start_track(update: Update, context: "ContextTypes.DEFAULT_TYPE") -> int:
    """Начало диалога /track."""
    user_id = update.effective_user.id
    logger.info("track_started", user_id=user_id)

    await update.message.reply_text(
        "Отправьте ссылку для отслеживания.\n"
        "Поддерживаются: GitHub, Stack Overflow.\n"
        "Напишите /cancel в любой момент, чтобы отменить."
    )
    return WAITING_FOR_LINK


async def receive_link(update: Update, context: "ContextTypes.DEFAULT_TYPE") -> int:
    """Получили ссылку от пользователя."""
    user_id = update.effective_user.id
    text = update.message.text.strip()

    logger.info("link_received", user_id=user_id, url=text)

    if not is_valid_url(text):
        await update.message.reply_text(
            "Это не похоже на валидную ссылку.\n"
            "Отправьте ссылку вида:\n"
            "https://github.com/user/repo\n"
            "https://stackoverflow.com/questions/12345"
        )
        return WAITING_FOR_LINK

    context.user_data["track_url"] = text

    await update.message.reply_text(
        "Хотите добавить теги? (необязательно)\n"
        "Пример: work, important, bug\n"
        "Или напишите /skip, чтобы пропустить."
    )
    return WAITING_FOR_TAGS


async def receive_tags(update: Update, context: "ContextTypes.DEFAULT_TYPE") -> int:
    """Получили теги (или /skip)."""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    url = context.user_data.get("track_url")

    logger.info("tags_received", user_id=user_id, tags_input=text)

    if text == "/skip":
        tags = []
    else:
        tags = extract_tags(text)

    try:
        await scrapper_client.register_chat(user_id)
        await scrapper_client.add_link(chat_id=user_id, url=url, tags=tags)

        tags_str = f" с тегами: {', '.join(tags)}" if tags else ""
        await update.message.reply_text(
            f"Ссылка добавлена{tags_str}!\n"
            f"Теперь я буду следить за обновлениями:\n"
            f"{url}"
        )
        logger.info("link_tracked_success", user_id=user_id, url=url, tags=tags)

    except ChatNotFoundError:
        await update.message.reply_text("Ошибка: чат не найден. Попробуйте ещё раз.")
        logger.error("chat_not_found", user_id=user_id)
    except LinkAlreadyExistsError:
        await update.message.reply_text(
            "Вы уже отслеживаете эту ссылку.\n"
            "Используйте /list, чтобы посмотреть все отслеживаемые ссылки."
        )
        logger.warning("link_already_exists", user_id=user_id, url=url)
    except Exception as e:
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
        logger.error("track_error", user_id=user_id, error=str(e))

    return ConversationHandler.END


async def cancel_track(update: Update, context: "ContextTypes.DEFAULT_TYPE") -> int:
    """Отмена диалога по команде /cancel."""
    user_id = update.effective_user.id
    logger.info("track_cancelled", user_id=user_id)

    await update.message.reply_text("Отменено. Диалог завершён.")
    return ConversationHandler.END


async def unknown_in_track(update: Update, context: "ContextTypes.DEFAULT_TYPE") -> int:
    """Если пользователь отправил другую команду во время диалога."""
    user_id = update.effective_user.id
    logger.warning(
        "unknown_command_in_track", user_id=user_id, text=update.message.text
    )

    await update.message.reply_text(
        "Во время диалога /track отправляйте только ссылки, теги или /cancel.\n"
        "Чтобы начать заново, напишите /track."
    )
    return (
        WAITING_FOR_LINK
        if context.user_data.get("track_url") is None
        else WAITING_FOR_TAGS
    )


def get_track_conv_handler() -> ConversationHandler:
    """Создаёт и возвращает ConversationHandler для команды /track."""
    return ConversationHandler(
        entry_points=[CommandHandler("track", start_track)],
        states={
            WAITING_FOR_LINK: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_link),
                CommandHandler("cancel", cancel_track),
                MessageHandler(filters.COMMAND, unknown_in_track),
            ],
            WAITING_FOR_TAGS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_tags),
                CommandHandler("skip", receive_tags),
                CommandHandler("cancel", cancel_track),
                MessageHandler(filters.COMMAND, unknown_in_track),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_track)],
        name="track_conversation",
        persistent=False,
    )
