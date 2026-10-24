import asyncio
from threading import Thread
import uvicorn
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from src.setup_commands import setup_commands
from src.config import settings
from src.logger import get_logger, setup_logger
from src.handlers import (
    start_command,
    help_command,
    unknown_command,
    get_track_conv_handler,
    list_command,
    untrack_command,
)
from src.webhook_server import app as webhook_app
from src.clients.scrapper_client import scrapper_client
from src.kafka_consumer import NotificationConsumer

logger = get_logger()

consumer: NotificationConsumer | None = None


def run_webhook_server():
    uvicorn.run(
        webhook_app,
        host="0.0.0.0",
        port=8080,
        log_level="warning",
    )


async def post_init(application: Application):
    await setup_commands(application)
    webhook_app.state.bot = application.bot

    if settings.notification_transport == "kafka":
        global consumer
        consumer = NotificationConsumer(application.bot)
        await consumer.start()
        logger.info("kafka_consumer_enabled")
    else:
        logger.info("http_webhook_enabled")


async def shutdown():
    global consumer
    if consumer is not None:
        await consumer.stop()
    await scrapper_client.close()


def main() -> None:
    setup_logger()
    logger.info("application_started", bot_token_preview="***")

    webhook_thread = Thread(target=run_webhook_server, daemon=True)
    webhook_thread.start()
    logger.info("webhook_server_started", port=8080)

    application = (
        Application.builder().token(settings.bot_token.get_secret_value()).build()
    )

    application.post_init = post_init

    application.add_handler(get_track_conv_handler())
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list", list_command))
    application.add_handler(CommandHandler("untrack", untrack_command))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    logger.info(
        "handlers_registered",
        handlers=["/start", "/help", "/track", "/list", "/untrack", "unknown"],
    )

    logger.info("bot_starting", mode="long_polling")

    try:
        application.run_polling(
            allowed_updates=Update.ALL_TYPES, drop_pending_updates=True
        )
    finally:
        asyncio.run(shutdown())


if __name__ == "__main__":
    main()
