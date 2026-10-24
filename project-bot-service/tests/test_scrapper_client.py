"""Тесты HTTP-клиента к скрапперу."""

import pytest
import respx
from httpx import Response, RequestError
from unittest.mock import patch
from src.clients.scrapper_client import (
    ScrapperClient,
    ScrapperClientError,
    LinkAlreadyExistsError,
)


@pytest.fixture
def client():
    """Фикстура: клиент для тестов."""
    return ScrapperClient(base_url="http://test-scrapper:8000")


class TestScrapperClient:
    """Тесты методов клиента."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_add_link_success(self, client):
        """Добавление ссылки."""
        respx.post("http://test-scrapper:8000/links").mock(
            return_value=Response(
                200,
                json={
                    "id": 1,
                    "url": "https://github.com/test/repo",
                    "tags": ["work"],
                    "filters": [],
                },
            )
        )

        result = await client.add_link(
            123, "https://github.com/test/repo", tags=["work"]
        )
        assert result.id == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_add_link_already_exists(self, client):
        """Добавление ссылки и она уже отслеживается."""
        respx.post("http://test-scrapper:8000/links").mock(
            return_value=Response(409, json={"code": "LINK_ALREADY_EXISTS"})
        )

        with pytest.raises(LinkAlreadyExistsError):
            await client.add_link(123, "https://github.com/test/repo")

    @respx.mock
    @pytest.mark.asyncio
    async def test_list_links_success(self, client):
        """Получение списка ссылок."""
        respx.get("http://test-scrapper:8000/links").mock(
            return_value=Response(
                200,
                json={
                    "links": [
                        {
                            "id": 1,
                            "url": "https://github.com/test/repo",
                            "tags": [],
                            "filters": [],
                        }
                    ],
                    "size": 1,
                },
            )
        )

        links = await client.list_links(123)
        assert len(links) == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_network_error(self, client):
        """Сетевая ошибка."""
        with patch.object(
            client._client,
            "post",
            side_effect=RequestError("Connection refused", request=None),
        ):
            with pytest.raises(ScrapperClientError, match="Не удалось связаться"):
                await client.register_chat(123)
