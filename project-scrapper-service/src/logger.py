import logging
import sys
import structlog


def setup_logger(log_level: str = "INFO") -> None:
    """Инициализация structlog."""

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.format_exc_info,
            (
                structlog.processors.JSONRenderer()
                if log_level != "DEBUG"
                else structlog.dev.ConsoleRenderer()
            ),
        ],
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger() -> structlog.typing.FilteringBoundLogger:
    """Получить логгер для использования в коде."""
    return structlog.get_logger()
