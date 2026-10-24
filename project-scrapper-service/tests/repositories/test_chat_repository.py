import pytest
from src.repositories.factory import create_repositories, close_repositories


@pytest.mark.parametrize("access_type", ["SQL", "ORM"])
@pytest.mark.asyncio
async def test_add_chat(settings, access_type):
    settings.db_access_type = access_type

    repos = await create_repositories(settings)
    chat_repo = repos["chat"]

    await chat_repo.remove(999)

    result = await chat_repo.add(999)
    assert result is True
    assert await chat_repo.exists(999) is True

    result = await chat_repo.add(999)
    assert result is False

    await close_repositories(repos)


@pytest.mark.parametrize("access_type", ["SQL", "ORM"])
@pytest.mark.asyncio
async def test_remove_chat(settings, access_type):
    settings.db_access_type = access_type

    repos = await create_repositories(settings)
    chat_repo = repos["chat"]

    await chat_repo.remove(999)
    await chat_repo.add(999)

    result = await chat_repo.remove(999)
    assert result is True
    assert await chat_repo.exists(999) is False

    result = await chat_repo.remove(888)
    assert result is False

    await close_repositories(repos)
