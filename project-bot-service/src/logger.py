import logging
import sys
import structlog


def setup_logger() -> None:

    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(),
    )


def get_logger():
    """Возвращает логгер для использования в коде."""
    return structlog.get_logger()
