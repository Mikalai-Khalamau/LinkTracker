from src.logger import get_logger
from src.config import settings
from src.services.message_sender import UpdateMessage
from src.services.message_formatter import format_update_message
from src.clients.resilient_http_client import ResilientHttpClient

logger = get_logger()


class HttpMessageSender:
    """Отправляет уведомления через HTTP в Bot Service."""

    def __init__(self, bot_callback_url: str | None = None):
        self.bot_callback_url = bot_callback_url or settings.bot_callback_url
        self.client = ResilientHttpClient()

    @property
    def is_available(self) -> bool:
        return self.client.is_available

    async def send_message(self, message: UpdateMessage) -> bool:
        """Отправляет уведомление всем получателям."""
        text = self._format_message(message)
        success_count = 0
        total_count = len(message.chat_ids)

        for chat_id in message.chat_ids:
            try:
                success = await self._send_to_chat(chat_id, text)
                if success:
                    success_count += 1
            except Exception as e:
                logger.error(
                    "send_to_chat_error",
                    chat_id=chat_id,
                    update_type=message.update_type,
                    error=str(e),
                )

        if success_count == total_count:
            logger.info(
                "all_notifications_sent",
                update_type=message.update_type,
                title=message.title[:50],
                recipients=total_count,
            )
            return True
        else:
            logger.warning(
                "partial_notification_failure",
                update_type=message.update_type,
                success=success_count,
                total=total_count,
            )
            return False

    def _format_message(self, message: UpdateMessage) -> str:
        """Форматирует UpdateMessage в текст для телеграма."""
        if message.update_type == "github_issue":
            return format_update_message(
                update_type="github_issue",
                title=message.title,
                author=message.author,
                created_at=message.created_at,
                preview=message.preview,
                url=message.source_url,
                issue_number=self._extract_number(message.source_url),
            )
        elif message.update_type == "github_pr":
            return format_update_message(
                update_type="github_pr",
                title=message.title,
                author=message.author,
                created_at=message.created_at,
                preview=message.preview,
                url=message.source_url,
                pr_number=self._extract_number(message.source_url),
            )
        elif message.update_type == "stackoverflow_answer":
            return format_update_message(
                update_type="stackoverflow_answer",
                question_title=message.title,
                author=message.author,
                created_at=message.created_at,
                preview=message.preview,
                url=message.source_url,
                answer_id=self._extract_number(message.source_url),
            )
        else:
            logger.warning("unknown_update_type", update_type=message.update_type)
            return f"Обновление: {message.title}"

    def _extract_number(self, url: str) -> int:
        """Извлекает номер из URL."""
        try:
            parts = url.rstrip("/").split("/")
            return int(parts[-1])
        except (ValueError, IndexError):
            logger.warning("cannot_extract_number_from_url", url=url)
            return 0

    async def _send_to_chat(self, chat_id: int, text: str) -> bool:
        """Отправляет сообщение в конкретный чат."""
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        logger.debug(
            "sending_notification",
            chat_id=chat_id,
            url=self.bot_callback_url,
            text_preview=text[:100],
        )

        try:
            response = await self.client.post(self.bot_callback_url, json=payload)
            if response.status_code == 200:
                logger.debug("notification_sent_success", chat_id=chat_id)
                return True
            else:
                logger.error(
                    "notification_send_failed",
                    chat_id=chat_id,
                    status=response.status_code,
                    response_text=response.text[:200],
                )
                return False
        except Exception as e:
            logger.error("notification_request_error", chat_id=chat_id, error=str(e))
            return False

    async def close(self):
        await self.client.close()
