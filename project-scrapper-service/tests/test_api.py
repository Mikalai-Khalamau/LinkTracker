"""Контрактные тесты для Scrapper API."""

import pytest
from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer
from alembic import command
from alembic.config import Config
from pathlib import Path

from src.main import app
from src.config import settings


def _normalize_db_url(base_url: str, driver: str) -> str:
    """Убирает старый драйвер и ставит нужный."""
    if "://" in base_url:
        _, rest = base_url.split("://", 1)
    else:
        rest = base_url
    params = ""
    if "?" in rest:
        rest, params = rest.split("?", 1)
        params = "?" + params
    return f"postgresql+{driver}://{rest}{params}"


@pytest.fixture(scope="module")
def postgres_container():
    """Запускает PostgreSQL для контрактных тестов."""
    with PostgresContainer("postgres:15-alpine", driver="psycopg2") as pg:
        yield pg


@pytest.fixture(scope="module")
def db_url(postgres_container):
    raw_url = postgres_container.get_connection_url()
    if "://" in raw_url:
        _, rest = raw_url.split("://", 1)
        return f"postgresql://{rest}"
    return raw_url


@pytest.fixture(scope="module", autouse=True)
def run_migrations(db_url):
    """Применяет миграции перед контрактными тестами."""
    cfg = Config(Path(__file__).parent.parent / "migrations" / "alembic.ini")
    migration_url = _normalize_db_url(db_url, "psycopg2")
    cfg.set_main_option("sqlalchemy.url", migration_url)
    command.upgrade(cfg, "head")


@pytest.fixture(scope="module")
def client(db_url):
    """Создаёт тестовый клиент с инициализированным app.state."""

    app_url = _normalize_db_url(db_url, "asyncpg")

    original_url = settings.db_url
    original_type = settings.db_access_type
    settings.db_url = app_url
    settings.db_access_type = "ORM"

    try:
        with TestClient(app) as client:
            yield client
    finally:
        settings.db_url = original_url
        settings.db_access_type = original_type


class TestBotWebhookContract:
    """Тесты Bot API."""

    def test_update_valid_request(self, client):
        """POST /updates: валидный запрос и 200 OK."""
        response = client.post(
            "/updates",
            json={
                "id": 1,
                "url": "https://github.com/test/repo",
                "description": "Test update",
                "tgChatIds": [123],
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "received"

    def test_update_invalid_request(self, client):
        """POST /updates: невалидный запрос и не 200."""
        response = client.post(
            "/updates", json={"id": 1, "description": "Test", "tgChatIds": [123]}
        )
        assert response.status_code in [400, 422]


class TestScrapperApiContract:
    """Контрактные тесты Scrapper API."""

    def test_add_and_get_link(self, client):
        """Добавление и получение."""
        resp = client.post("/tg-chat/1")
        assert resp.status_code == 200

        resp = client.post(
            "/links",
            headers={"Tg-Chat-Id": "1"},
            json={"link": "https://github.com/test/repo", "tags": ["work"]},
        )
        assert resp.status_code == 200

        resp = client.get("/links", headers={"Tg-Chat-Id": "1"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["size"] >= 1
        assert any(
            link["url"] == "https://github.com/test/repo" for link in data["links"]
        )

    def test_add_and_delete_link(self, client):
        """Добавление и удаление."""
        client.post("/tg-chat/1")
        client.post(
            "/links",
            headers={"Tg-Chat-Id": "1"},
            json={"link": "https://github.com/test/repo"},
        )

        resp = client.request(
            "DELETE",
            "/links",
            headers={"Tg-Chat-Id": "1"},
            json={"link": "https://github.com/test/repo"},
        )
        assert resp.status_code == 200

        resp = client.get("/links", headers={"Tg-Chat-Id": "1"})
        links = resp.json()["links"]
        assert not any(link["url"] == "https://github.com/test/repo" for link in links)

    def test_delete_from_nonexistent_chat(self, client):
        """Удаление из несуществующего чата."""
        client.post("/tg-chat/1")
        client.post(
            "/links",
            headers={"Tg-Chat-Id": "1"},
            json={"link": "https://github.com/test/repo"},
        )

        resp = client.request(
            "DELETE",
            "/links",
            headers={"Tg-Chat-Id": "999"},
            json={"link": "https://github.com/test/repo"},
        )
        assert resp.status_code != 200

        resp = client.get("/links", headers={"Tg-Chat-Id": "1"})
        assert any(
            link["url"] == "https://github.com/test/repo"
            for link in resp.json()["links"]
        )

    def test_add_to_nonexistent_chat(self, client):
        """Добавление в несуществующий чат."""
        resp = client.post(
            "/links",
            headers={"Tg-Chat-Id": "2"},
            json={"link": "https://github.com/test/repo"},
        )
        assert resp.status_code != 200

    def test_add_after_chat_deleted(self, client):
        """Работа с удалённым чатом."""
        client.post("/tg-chat/1")
        resp = client.delete("/tg-chat/1")
        assert resp.status_code == 200

        resp = client.post(
            "/links",
            headers={"Tg-Chat-Id": "1"},
            json={"link": "https://github.com/test/repo"},
        )
        assert resp.status_code != 200

    def test_delete_nonexistent_chat(self, client):
        """Удаление несуществующего чата."""
        resp = client.delete("/tg-chat/999")
        assert resp.status_code == 404
