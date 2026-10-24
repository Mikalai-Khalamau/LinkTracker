from fastapi import FastAPI, status, Request, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from src.config import settings
from src.logger import get_logger

logger = get_logger()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit_requests_per_minute}/minute"],
    enabled=settings.rate_limit_enabled,
)


class WebhookUpdateRequest(BaseModel):
    """Запрос на отправку уведомления от Scrapper."""

    chat_id: int = Field(..., description="ID Telegram чата пользователя")
    text: str = Field(..., description="Текст сообщения (с HTML разметкой)")
    parse_mode: Optional[str] = Field(
        default="HTML", description="Режим парсинга (HTML или Markdown)"
    )


def create_webhook_app() -> FastAPI:
    """Создает и настраивает FastAPI приложение для вебхука."""

    app = FastAPI(
        title="Bot Webhook API",
        docs_url="/webhook-docs",
        redoc_url=None,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.get("/health")
    async def health_check():
        """Health check."""
        return {"status": "ok", "service": "bot-webhook"}

    @app.post("/updates", status_code=status.HTTP_200_OK)
    @limiter.limit(f"{settings.rate_limit_requests_per_minute}/minute")
    async def handle_update(request: WebhookUpdateRequest, app_request: Request):
        """Прием уведомления от скраппера и отправка в Telegram."""

        bot = app_request.app.state.bot

        if bot is None:
            logger.error("bot_instance_not_found")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Bot instance is not initialized",
            )

        logger.info(
            "webhook_update_received",
            chat_id=request.chat_id,
            text_length=len(request.text),
            parse_mode=request.parse_mode,
        )

        try:
            await bot.send_message(
                chat_id=request.chat_id,
                text=request.text,
                parse_mode=request.parse_mode,
            )

            logger.info(
                "telegram_message_sent_success",
                chat_id=request.chat_id,
            )
            return {"status": "received", "message": "Update processed"}

        except Exception as e:
            logger.error(
                "telegram_send_error",
                chat_id=request.chat_id,
                error=str(e),
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to send message to Telegram: {str(e)}",
            )

    return app


app = create_webhook_app()
