from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import asyncpg
from src.config import settings


def _ensure_async_driver(db_url: str) -> str:
    """Гарантирует, что URL использует asyncpg драйвер."""
    if "://" not in db_url:
        return f"postgresql+asyncpg://{db_url}"

    prefix, rest = db_url.split("://", 1)

    if prefix == "postgresql+asyncpg":
        return db_url

    return f"postgresql+asyncpg://{rest}"


def create_async_engine_sqlalchemy(
    db_url: str, pool_size: int = 10, max_overflow: int = 20
):
    """Создание асинхронного engine для SQLAlchemy."""
    db_url = _ensure_async_driver(db_url)

    return create_async_engine(
        db_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,
        echo=settings.log_level == "DEBUG",
    )


def create_async_session_factory(engine):
    """Создание фабрики сессий."""
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


async def create_asyncpg_pool(db_url: str, min_size: int = 5, max_size: int = 20):
    """Создание пула соединений для asyncpg."""
    db_url = _ensure_async_driver(db_url)
    return await asyncpg.create_pool(
        db_url.replace("postgresql+asyncpg://", "postgresql://", 1),
        min_size=min_size,
        max_size=max_size,
        command_timeout=60,
    )
