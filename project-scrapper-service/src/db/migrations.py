from alembic import command
from alembic.config import Config
from pathlib import Path
from src.logger import get_logger

logger = get_logger()


def _ensure_sync_driver(db_url: str) -> str:
    """Гарантирует использование psycopg2 для миграций."""
    if "://" not in db_url:
        return f"postgresql+psycopg2://{db_url}"

    prefix, rest = db_url.split("://", 1)

    if prefix == "postgresql+psycopg2":
        return db_url

    return f"postgresql+psycopg2://{rest}"


def run_migrations(db_url: str) -> None:
    """Применение миграций к БД."""
    migrations_path = Path(__file__).parent.parent.parent / "migrations"
    alembic_cfg = Config(migrations_path / "alembic.ini")

    migration_url = _ensure_sync_driver(db_url)
    alembic_cfg.set_main_option("sqlalchemy.url", migration_url)

    logger.info("running_alembic_migrations", path=str(migrations_path))
    command.upgrade(alembic_cfg, "head")
    logger.info("migrations_completed")
