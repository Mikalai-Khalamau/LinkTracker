import pytest
import asyncio
import respx
import httpx
from httpx import Response
from unittest.mock import patch

from src.clients.resilient_http_client import ResilientHttpClient
from src.config import settings


@pytest.mark.asyncio
async def test_timeout_exceeded():
    """Превышение времени ожидания."""
    client = ResilientHttpClient()

    async def raise_timeout(*args, **kwargs):
        raise httpx.TimeoutException("Connection timed out")

    with patch.object(httpx.AsyncClient, "request", side_effect=raise_timeout):
        start = asyncio.get_event_loop().time()

        with pytest.raises(httpx.TimeoutException):
            await client.get("http://slow-api/test")

        elapsed = asyncio.get_event_loop().time() - start

        assert elapsed < settings.http_timeout_seconds * settings.retry_max_attempts + 1

    await client.close()


@pytest.mark.asyncio
async def test_retry_on_5xx():
    """Retry на 5xx ошибки."""
    client = ResilientHttpClient()
    call_count = 0

    def response_handler(request):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            return Response(500, text="Internal Error")
        return Response(200, json={"status": "ok"})

    with respx.mock:
        respx.get("http://api/test").mock(side_effect=response_handler)

        response = await client.get("http://api/test")

        assert response.status_code == 200
        assert call_count == 3

    await client.close()


@pytest.mark.asyncio
async def test_no_retry_on_4xx():
    """Отсутствие Retry на 4xx."""
    client = ResilientHttpClient()

    with respx.mock:
        respx.get("http://api/test").mock(
            return_value=Response(400, text="Bad Request")
        )

        response = await client.get("http://api/test")

        assert response.status_code == 400
        assert len(respx.calls) == 1

    await client.close()


@pytest.mark.asyncio
async def test_constant_backoff_interval():
    """Соблюдение интервала retry."""
    client = ResilientHttpClient()
    timestamps = []

    def response_handler(request):
        timestamps.append(asyncio.get_event_loop().time())
        return Response(500, text="Internal Error")

    with respx.mock:
        respx.get("http://api/test").mock(side_effect=response_handler)

        with pytest.raises(httpx.HTTPStatusError):
            await client.get("http://api/test")

        for i in range(1, len(timestamps)):
            interval = timestamps[i] - timestamps[i - 1]
            assert abs(interval - settings.retry_wait_seconds) < 0.2

    await client.close()
