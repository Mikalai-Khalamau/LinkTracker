from src.config import Settings
from src.db.connections import (
    create_async_engine_sqlalchemy,
    create_async_session_factory,
    create_asyncpg_pool,
)
from src.repositories.sql.chat_repository import SqlChatRepository
from src.repositories.sql.link_repository import SqlLinkRepository
from src.repositories.orm.chat_repository import OrmChatRepository
from src.repositories.orm.link_repository import OrmLinkRepository


async def create_repositories(settings: Settings):
    access_type = settings.db_access_type.upper()

    if access_type == "SQL":
        pool = await create_asyncpg_pool(
            settings.db_url, min_size=5, max_size=settings.db_pool_size
        )
        return {
            "chat": SqlChatRepository(pool),
            "link": SqlLinkRepository(pool),
            "pool": pool,
            "type": "SQL",
        }

    engine = create_async_engine_sqlalchemy(
        settings.db_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
    )
    session_factory = create_async_session_factory(engine)
    return {
        "chat": OrmChatRepository(session_factory),
        "link": OrmLinkRepository(session_factory),
        "engine": engine,
        "type": "ORM",
    }


async def close_repositories(repos: dict):
    if "pool" in repos:
        await repos["pool"].close()
    elif "engine" in repos:
        await repos["engine"].dispose()
