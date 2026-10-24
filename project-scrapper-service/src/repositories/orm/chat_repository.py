from sqlalchemy import select, insert, delete
from src.repositories.base import ChatRepositoryProtocol
from src.repositories.orm.models import ChatORM


class OrmChatRepository(ChatRepositoryProtocol):
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def exists(self, chat_id: int) -> bool:
        async with self.session_factory() as session:
            stmt = select(ChatORM).where(ChatORM.chat_id == chat_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none() is not None

    async def add(self, chat_id: int) -> bool:
        async with self.session_factory() as session:
            stmt = select(ChatORM).where(ChatORM.chat_id == chat_id)
            result = await session.execute(stmt)
            if result.scalar_one_or_none():
                return False
            await session.execute(insert(ChatORM).values(chat_id=chat_id))
            await session.commit()
            return True

    async def remove(self, chat_id: int) -> bool:
        async with self.session_factory() as session:
            stmt = delete(ChatORM).where(ChatORM.chat_id == chat_id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
