import pytest
import asyncpg
from testcontainers.postgres import PostgresContainer
from testcontainers.kafka import KafkaContainer
from testcontainers.redis import RedisContainer
from alembic import command
from alembic.config import Config
from pathlib import Path

from src.config import Settings


def _normalize_db_url(base_url: str, driver: str) -> str:
    if "://" in base_url:
        _, rest = base_url.split("://", 1)
    else:
        rest = base_url
    params = ""
    if "?" in rest:
        rest, params = rest.split("?", 1)
        params = "?" + params
    return f"postgresql+{driver}://{rest}{params}"


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:15-alpine", driver="psycopg2") as pg:
        yield pg


@pytest.fixture(scope="session")
def kafka_container():
    with KafkaContainer("confluentinc/cp-kafka:7.6.0") as kafka:
        yield kafka


@pytest.fixture(scope="session")
def kafka_bootstrap_servers(kafka_container):
    return kafka_container.get_bootstrap_server()


@pytest.fixture(scope="session")
def valkey_container():
    with RedisContainer("valkey/valkey:8.0", port=6379) as valkey:
        yield valkey


@pytest.fixture
def valkey_url(valkey_container):
    host = valkey_container.get_container_host_ip()
    port = valkey_container.get_exposed_port(6379)
    return f"{host}:{port}"


@pytest.fixture(scope="session")
def db_url(postgres_container):
    raw_url = postgres_container.get_connection_url()
    if "://" in raw_url:
        _, rest = raw_url.split("://", 1)
        return f"postgresql://{rest}"
    return raw_url


@pytest.fixture(scope="session", autouse=True)
def run_migrations(db_url):
    cfg = Config(Path(__file__).parent.parent / "migrations" / "alembic.ini")
    cfg.set_main_option("sqlalchemy.url", _normalize_db_url(db_url, "psycopg2"))
    command.upgrade(cfg, "head")


@pytest.fixture(autouse=True)
async def clean_db(db_url):
    pool = await asyncpg.create_pool(db_url, min_size=1, max_size=1)
    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE TABLE chat_links, links, chats CASCADE;")
    await pool.close()
    yield


@pytest.fixture
def settings(db_url):
    app_url = _normalize_db_url(db_url, "asyncpg")
    return Settings(db_url=app_url)
