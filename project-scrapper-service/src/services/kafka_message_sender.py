import asyncio
import json

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from src.logger import get_logger
from src.config import settings
from src.services.message_sender import UpdateMessage
from src.services.message_formatter import format_update_message

logger = get_logger()


class KafkaMessageSender:
    def __init__(self, bootstrap_servers: str | None = None, topic: str | None = None):
        self.bootstrap_servers = bootstrap_servers or settings.kafka_bootstrap_servers
        self.topic = topic or settings.kafka_topic_notifications
        self._producer: AIOKafkaProducer | None = None
        self._lock = asyncio.Lock()

    async def start(self):
        async with self._lock:
            if self._producer is None:
                self._producer = AIOKafkaProducer(
                    bootstrap_servers=self.bootstrap_servers.split(","),
                    client_id=settings.kafka_producer_client_id,
                    acks=settings.kafka_ack_mode,
                    linger_ms=settings.kafka_linger_ms,
                    max_batch_size=settings.kafka_batch_size,
                    value_serializer=lambda v: json.dumps(v, default=str).encode(
                        "utf-8"
                    ),
                )
                await self._producer.start()
                logger.info(
                    "kafka_producer_started",
                    bootstrap_servers=self.bootstrap_servers,
                    topic=self.topic,
                )

    async def stop(self):
        async with self._lock:
            if self._producer is not None:
                await self._producer.stop()
                self._producer = None
                logger.info("kafka_producer_stopped")

    async def send_message(self, message: UpdateMessage) -> bool:
        if self._producer is None:
            await self.start()

        text = self._build_text(message)
        success_count = 0

        for chat_id in message.chat_ids:
            try:
                payload = {
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "update_type": message.update_type,
                    "source_url": message.source_url,
                    "title": message.title,
                    "author": message.author,
                    "created_at": message.created_at.isoformat(),
                    "preview": message.preview,
                }

                result = await self._producer.send(
                    topic=self.topic,
                    value=payload,
                    key=str(chat_id).encode("utf-8"),
                )
                await result

                success_count += 1
                logger.debug(
                    "kafka_message_sent",
                    chat_id=chat_id,
                    topic=self.topic,
                    update_type=message.update_type,
                )
            except KafkaError as e:
                logger.error(
                    "kafka_send_error",
                    chat_id=chat_id,
                    error=str(e),
                    exc_info=True,
                )
            except Exception as e:
                logger.error(
                    "kafka_unexpected_error",
                    chat_id=chat_id,
                    error=str(e),
                    exc_info=True,
                )

        if success_count == len(message.chat_ids):
            logger.info(
                "all_kafka_notifications_sent",
                update_type=message.update_type,
                title=message.title[:50],
                recipients=len(message.chat_ids),
            )
            return True
        else:
            logger.warning(
                "partial_kafka_notification_failure",
                update_type=message.update_type,
                success=success_count,
                total=len(message.chat_ids),
            )
            return False

    def _build_text(self, message: UpdateMessage) -> str:
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
            return f"Update: {message.title}"

    def _extract_number(self, url: str) -> int:
        try:
            parts = url.rstrip("/").split("/")
            return int(parts[-1])
        except (ValueError, IndexError):
            logger.warning("cannot_extract_number_from_url", url=url)
            return 0
