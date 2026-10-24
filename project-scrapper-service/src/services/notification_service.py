from typing import List
from datetime import datetime

from src.logger import get_logger
from src.config import settings
from src.services.message_sender import MessageSenderProtocol, UpdateMessage
from src.services.http_message_sender import HttpMessageSender
from src.services.kafka_message_sender import KafkaMessageSender

logger = get_logger()

_sender: MessageSenderProtocol | None = None
_fallback_sender: KafkaMessageSender | None = None


def init_sender() -> MessageSenderProtocol:
    global _sender

    if settings.notification_transport == "kafka":
        _sender = KafkaMessageSender()
        logger.info(
            "kafka_sender_initialized",
            bootstrap_servers=settings.kafka_bootstrap_servers,
            topic=settings.kafka_topic_notifications,
        )
    else:
        _sender = HttpMessageSender(settings.bot_callback_url)
        logger.info("http_sender_initialized", url=settings.bot_callback_url)

    return _sender


def get_sender() -> MessageSenderProtocol:
    if _sender is None:
        raise RuntimeError(
            "Notification sender not initialized. Call init_sender() first."
        )
    return _sender


def get_fallback_sender() -> KafkaMessageSender:
    global _fallback_sender
    if _fallback_sender is None:
        _fallback_sender = KafkaMessageSender()
    return _fallback_sender


async def shutdown_sender():
    global _sender, _fallback_sender
    if isinstance(_sender, KafkaMessageSender):
        await _sender.stop()
    if _fallback_sender is not None:
        await _fallback_sender.stop()
    _sender = None
    _fallback_sender = None


async def send_notification_with_fallback(message: UpdateMessage) -> bool:
    primary_sender = get_sender()

    if isinstance(primary_sender, HttpMessageSender):
        if not primary_sender.is_available:
            logger.warning(
                "http_transport_unavailable_circuit_open",
                update_type=message.update_type,
            )
            return await _send_via_kafka_fallback(message)

        try:
            success = await primary_sender.send_message(message)
            if success:
                return True

            logger.warning(
                "http_send_failed_switching_to_kafka",
                update_type=message.update_type,
            )
            return await _send_via_kafka_fallback(message)

        except Exception as e:
            logger.error(
                "http_send_exception_switching_to_kafka",
                error=str(e),
                exc_info=True,
            )
            return await _send_via_kafka_fallback(message)
    else:
        return await primary_sender.send_message(message)


async def _send_via_kafka_fallback(message: UpdateMessage) -> bool:
    fallback = get_fallback_sender()

    try:
        await fallback.start()
        success = await fallback.send_message(message)

        if success:
            logger.info(
                "fallback_kafka_send_success",
                update_type=message.update_type,
            )
        else:
            logger.error(
                "fallback_kafka_send_failed",
                update_type=message.update_type,
            )

        return success

    except Exception as e:
        logger.error(
            "fallback_kafka_exception",
            error=str(e),
            exc_info=True,
        )
        return False


async def send_github_issue_notification(
    chat_ids: List[int],
    issue_number: int,
    title: str,
    author: str,
    created_at: datetime,
    preview: str,
    url: str,
) -> bool:
    message = UpdateMessage(
        update_type="github_issue",
        source_url=url,
        title=title,
        author=author,
        created_at=created_at,
        preview=preview,
        chat_ids=chat_ids,
    )
    return await send_notification_with_fallback(message)


async def send_github_pr_notification(
    chat_ids: List[int],
    pr_number: int,
    title: str,
    author: str,
    created_at: datetime,
    preview: str,
    url: str,
) -> bool:
    message = UpdateMessage(
        update_type="github_pr",
        source_url=url,
        title=title,
        author=author,
        created_at=created_at,
        preview=preview,
        chat_ids=chat_ids,
    )
    return await send_notification_with_fallback(message)


async def send_stackoverflow_answer_notification(
    chat_ids: List[int],
    question_title: str,
    answer_id: int,
    author: str,
    created_at: datetime,
    preview: str,
    url: str,
) -> bool:
    message = UpdateMessage(
        update_type="stackoverflow_answer",
        source_url=url,
        title=question_title,
        author=author,
        created_at=created_at,
        preview=preview,
        chat_ids=chat_ids,
    )
    return await send_notification_with_fallback(message)


async def send_update_notification(
    link_id: int, url: str, description: str, chat_ids: List[int]
) -> bool:
    logger.warning("using_deprecated_send_update_notification")
    message = UpdateMessage(
        update_type="generic",
        source_url=url,
        title="Update",
        author="System",
        created_at=datetime.now(),
        preview=description,
        chat_ids=chat_ids,
    )
    return await send_notification_with_fallback(message)
