import pytest
import asyncio

from src.cache.valkey_client import ValkeyClient
from src.config import settings


@pytest.fixture
def cache_client(valkey_url):
    original_nodes = settings.valkey_cluster_nodes
    original_ttl = settings.valkey_cache_ttl
    settings.valkey_cluster_nodes = valkey_url
    settings.valkey_cache_ttl = 5

    client = ValkeyClient()
    yield client

    settings.valkey_cluster_nodes = original_nodes
    settings.valkey_cache_ttl = original_ttl


@pytest.mark.asyncio
async def test_set_and_get(cache_client):
    await cache_client.connect()
    try:
        data = {"links": [{"id": 1, "url": "https://example.com"}], "size": 1}
        await cache_client.set(123, data)
        result = await cache_client.get(123)
        assert result == data
    finally:
        await cache_client.disconnect()


@pytest.mark.asyncio
async def test_cache_miss(cache_client):
    await cache_client.connect()
    try:
        result = await cache_client.get(999999)
        assert result is None
    finally:
        await cache_client.disconnect()


@pytest.mark.asyncio
async def test_invalidate(cache_client):
    await cache_client.connect()
    try:
        data = {"links": [], "size": 0}
        await cache_client.set(456, data)
        result = await cache_client.get(456)
        assert result is not None

        await cache_client.invalidate(456)
        result = await cache_client.get(456)
        assert result is None
    finally:
        await cache_client.disconnect()


@pytest.mark.asyncio
async def test_ttl_expiration(cache_client):
    await cache_client.connect()
    try:
        data = {"links": [], "size": 0}
        await cache_client.set(789, data)
        result = await cache_client.get(789)
        assert result is not None

        await asyncio.sleep(6)
        result = await cache_client.get(789)
        assert result is None
    finally:
        await cache_client.disconnect()


@pytest.mark.asyncio
async def test_key_prefix(cache_client):
    await cache_client.connect()
    try:
        data = {"links": [], "size": 0}
        await cache_client.set(111, data)
        key = cache_client._build_key(111)
        assert key.startswith("list:")
        assert "111" in key
    finally:
        await cache_client.disconnect()


@pytest.mark.asyncio
async def test_get_without_connection(cache_client):
    result = await cache_client.get(123)
    assert result is None


@pytest.mark.asyncio
async def test_set_without_connection(cache_client):
    result = await cache_client.set(123, {"data": 1})
    assert result is False


@pytest.mark.asyncio
async def test_invalidate_without_connection(cache_client):
    result = await cache_client.invalidate(123)
    assert result is False
