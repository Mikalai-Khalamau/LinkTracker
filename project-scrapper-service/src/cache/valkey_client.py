import json

from redis.asyncio import Redis

from src.logger import get_logger
from src.config import settings

logger = get_logger()


class ValkeyClient:
    def __init__(self):
        self._client: Redis | None = None
        self.ttl = settings.valkey_cache_ttl
        self.prefix = settings.valkey_cache_prefix

    async def connect(self):
        host, port = settings.valkey_cluster_nodes.split(",")[0].strip().split(":")
        self._client = Redis(
            host=host,
            port=int(port),
            decode_responses=False,
        )
        await self._client.ping()
        logger.info("valkey_connected", host=host, port=port)

    async def disconnect(self):
        if self._client is not None:
            await self._client.close()
            self._client = None
            logger.info("valkey_disconnected")

    def _build_key(self, chat_id: int) -> str:
        return f"{self.prefix}{chat_id}"

    async def get(self, chat_id: int):
        if self._client is None:
            return None
        try:
            key = self._build_key(chat_id)
            value = await self._client.get(key)
            if value is None:
                logger.debug("cache_miss", chat_id=chat_id, key=key)
                return None
            logger.debug("cache_hit", chat_id=chat_id, key=key)
            if isinstance(value, bytes):
                value = value.decode("utf-8")
            return json.loads(value)
        except Exception as e:
            logger.error("valkey_get_error", chat_id=chat_id, error=str(e))
            return None

    async def set(self, chat_id: int, data: dict) -> bool:
        if self._client is None:
            return False
        try:
            key = self._build_key(chat_id)
            value = json.dumps(data, default=str, ensure_ascii=True)
            await self._client.set(key, value, ex=self.ttl)
            logger.debug("cache_set", chat_id=chat_id, key=key, ttl=self.ttl)
            return True
        except Exception as e:
            logger.error("valkey_set_error", chat_id=chat_id, error=str(e))
            return False

    async def invalidate(self, chat_id: int) -> bool:
        if self._client is None:
            return False
        try:
            key = self._build_key(chat_id)
            await self._client.delete(key)
            logger.debug("cache_invalidated", chat_id=chat_id, key=key)
            return True
        except Exception as e:
            logger.error("valkey_invalidate_error", chat_id=chat_id, error=str(e))
            return False
