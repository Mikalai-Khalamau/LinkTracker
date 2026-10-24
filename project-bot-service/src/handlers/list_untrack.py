from telegram import Update
from telegram.ext import ContextTypes

from src.clients.scrapper_client import (
    scrapper_client,
    ChatNotFoundError,
    ScrapperClientError,
)
from src.logger import get_logger

logger = get_logger()


async def list_command(update: Update, context: "ContextTypes.DEFAULT_TYPE") -> None:
    """Показать отслеживаемые ссылки."""
    user_id = update.effective_user.id

    tag = None
    if context.args and len(context.args) > 0:
        tag = context.args[0].strip()

    logger.info("list_command", user_id=user_id, tag=tag)

    try:
        links = await scrapper_client.list_links(chat_id=user_id, tag=tag)

        if not links:
            filter_msg = f" с тегом '{tag}'" if tag else ""
            await update.message.reply_text(
                f"У вас нет отслеживаемых ссылок{filter_msg}.\n"
                f"Используйте /track, чтобы добавить ссылку."
            )
            logger.info("no_links_found", user_id=user_id, tag=tag)
            return

        filter_msg = f" (тег: {tag})" if tag else ""
        message = f"Ваши отслеживаемые ссылки{filter_msg}:\n\n"

        for i, link in enumerate(links, 1):
            tags_str = f" [{', '.join(link.tags)}]" if link.tags else ""
            url_display = (
                link.url if len(str(link.url)) <= 50 else str(link.url)[:47] + "..."
            )
            message += f"{i}. {url_display}{tags_str}\n"

        await update.message.reply_text(message)
        logger.info("list_sent", user_id=user_id, count=len(links))

    except ChatNotFoundError:
        await update.message.reply_text(
            "Вы ещё не зарегистрированы в системе.\n"
            "Используйте /track, чтобы начать отслеживание."
        )
        logger.warning("chat_not_found", user_id=user_id)
    except ScrapperClientError as e:
        await update.message.reply_text(
            "Ошибка при получении списка. Попробуйте позже."
        )
        logger.error("list_error", user_id=user_id, error=str(e))
    except Exception as e:
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
        logger.error("list_unexpected_error", user_id=user_id, error=str(e))


async def untrack_command(update: Update, context: "ContextTypes.DEFAULT_TYPE") -> None:
    """Перестать отслеживать ссылку."""
    user_id = update.effective_user.id

    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "Укажите ссылку для удаления.\n"
            "Пример: /untrack https://github.com/user/repo"
        )
        logger.warning("untrack_no_url", user_id=user_id)
        return

    url = context.args[0].strip()
    logger.info("untrack_command", user_id=user_id, url=url)

    try:
        success = await scrapper_client.remove_link(chat_id=user_id, url=url)

        if success:
            await update.message.reply_text(f"Ссылка удалена из отслеживания:\n{url}")
            logger.info("link_untracked", user_id=user_id, url=url)
        else:
            await update.message.reply_text(
                "Не удалось удалить ссылку. Возможно, она не отслеживается."
            )
            logger.warning("untrack_failed", user_id=user_id, url=url)

    except ChatNotFoundError:
        await update.message.reply_text(
            "Чат не найден. Возможно, вы ещё не добавляли ссылки."
        )
        logger.warning("chat_not_found", user_id=user_id)
    except ScrapperClientError as e:
        await update.message.reply_text("Ошибка при удалении. Попробуйте позже.")
        logger.error("untrack_error", user_id=user_id, error=str(e))
    except Exception as e:
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
        logger.error("untrack_unexpected_error", user_id=user_id, error=str(e))
