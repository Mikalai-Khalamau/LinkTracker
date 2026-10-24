import asyncio
import json

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError
from telegram import Bot

from src.logger import get_logger
from src.config import settings

logger = get_logger()


class NotificationConsumer:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.bootstrap_servers = settings.kafka_bootstrap_servers
        self.topic = settings.kafka_topic_notifications
        self.group_id = settings.kafka_consumer_group_id
        self._consumer: AIOKafkaConsumer | None = None
        self._running = False

    async def start(self):
        self._consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers.split(","),
            group_id=self.group_id,
            auto_offset_reset=settings.kafka_auto_offset_reset,
            enable_auto_commit=settings.kafka_enable_auto_commit,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            key_deserializer=lambda k: k.decode("utf-8") if k else None,
        )
        await self._consumer.start()
        self._running = True
        logger.info(
            "kafka_consumer_started",
            topic=self.topic,
            group_id=self.group_id,
            bootstrap_servers=self.bootstrap_servers,
        )
        asyncio.create_task(self._consume_loop())

    async def stop(self):
        self._running = False
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None
            logger.info("kafka_consumer_stopped")

    async def _consume_loop(self):
        try:
            async for msg in self._consumer:
                if not self._running:
                    break
                try:
                    await self._process_message(msg.value)
                    if not settings.kafka_enable_auto_commit:
                        await self._consumer.commit()
                except Exception as e:
                    logger.error(
                        "kafka_message_processing_error",
                        topic=msg.topic,
                        partition=msg.partition,
                        offset=msg.offset,
                        error=str(e),
                        exc_info=True,
                    )
        except KafkaError as e:
            logger.error("kafka_consumer_error", error=str(e), exc_info=True)
        except asyncio.CancelledError:
            logger.info("kafka_consumer_cancelled")

    async def _process_message(self, payload: dict):
        chat_id = payload.get("chat_id")
        text = payload.get("text")
        parse_mode = payload.get("parse_mode", "HTML")

        if not chat_id or not text:
            logger.warning("invalid_kafka_message", payload=payload)
            return

        logger.debug(
            "kafka_message_received",
            chat_id=chat_id,
            text_length=len(text),
            update_type=payload.get("update_type"),
        )

        await self.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
        )

        logger.info("telegram_message_sent_from_kafka", chat_id=chat_id)
