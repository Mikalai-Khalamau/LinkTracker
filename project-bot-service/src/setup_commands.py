from telegram import BotCommand
from telegram.ext import Application

from src.config import settings
from src.logger import get_logger


async def setup_commands(application: Application) -> None:
    commands = [
        BotCommand(cmd["command"], cmd["description"]) for cmd in settings.bot_commands
    ]
    await application.bot.set_my_commands(commands)
    logger = get_logger()
    logger.info("commands_registered", commands=[c.command for c in commands])
