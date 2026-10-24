import asyncpg
from src.repositories.base import ChatRepositoryProtocol


class SqlChatRepository(ChatRepositoryProtocol):
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def exists(self, chat_id: int) -> bool:
        async with self.pool.acquire() as conn:
            return (
                await conn.fetchval("SELECT 1 FROM chats WHERE chat_id = $1", chat_id)
                is not None
            )

    async def add(self, chat_id: int) -> bool:
        async with self.pool.acquire() as conn:
            try:
                await conn.execute("INSERT INTO chats (chat_id) VALUES ($1)", chat_id)
                return True
            except asyncpg.UniqueViolationError:
                return False

    async def remove(self, chat_id: int) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute("DELETE FROM chats WHERE chat_id = $1", chat_id)
            return result.split()[-1] != "0"
