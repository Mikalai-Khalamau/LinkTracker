import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock

from src.main import app
from src.config import settings


@pytest.fixture(autouse=True)
async def setup_app_state():
    app.state.chat_repository = AsyncMock()
    app.state.chat_repository.add = AsyncMock(return_value=True)
    app.state.link_repository = AsyncMock()
    app.state.cache_client = None
    yield


@pytest.mark.asyncio
async def test_rate_limit_exceeded():
    """Превышение лимита запросов."""
    limit = settings.rate_limit_requests_per_minute
    excess = 10

    async with AsyncClient(app=app, base_url="http://test") as client:
        responses = []
        for _ in range(limit + excess):
            response = await client.post(
                "/tg-chat/999999",
            )
            responses.append(response.status_code)

        assert 429 in responses

        successful_responses = [r for r in responses if r == 200]
        assert len(successful_responses) == limit
