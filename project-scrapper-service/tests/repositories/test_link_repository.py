import pytest
from src.models import AddLinkRequest, LinkDomain
from src.repositories.factory import create_repositories, close_repositories


@pytest.mark.parametrize("access_type", ["SQL", "ORM"])
@pytest.mark.asyncio
async def test_add_link_success(settings, access_type):
    settings.db_access_type = access_type

    repos = await create_repositories(settings)
    chat_repo = repos["chat"]
    link_repo = repos["link"]

    await chat_repo.add(123)

    request = AddLinkRequest(link="https://github.com/test/repo", tags=["test"])
    result = await link_repo.add(chat_id=123, request=request)

    assert result is not None
    assert isinstance(result, LinkDomain)
    assert result.url == "https://github.com/test/repo"
    assert result.chat_id == 123

    await close_repositories(repos)


@pytest.mark.parametrize("access_type", ["SQL", "ORM"])
@pytest.mark.asyncio
async def test_add_duplicate_link(settings, access_type):
    settings.db_access_type = access_type

    repos = await create_repositories(settings)
    chat_repo = repos["chat"]
    link_repo = repos["link"]

    await chat_repo.add(123)

    request = AddLinkRequest(link="https://github.com/test/repo", tags=["test"])
    await link_repo.add(chat_id=123, request=request)
    result = await link_repo.add(chat_id=123, request=request)

    assert result is None

    await close_repositories(repos)


@pytest.mark.parametrize("access_type", ["SQL", "ORM"])
@pytest.mark.asyncio
async def test_get_links_by_chat(settings, access_type):
    settings.db_access_type = access_type

    repos = await create_repositories(settings)
    chat_repo = repos["chat"]
    link_repo = repos["link"]

    await chat_repo.add(123)

    req1 = AddLinkRequest(link="https://github.com/a/b", tags=["work"])
    req2 = AddLinkRequest(link="https://github.com/c/d", tags=["personal"])

    await link_repo.add(123, req1)
    await link_repo.add(123, req2)

    links = await link_repo.get_by_chat(123)
    assert len(links) == 2

    work_links = await link_repo.get_by_chat(123, tag="work")
    assert len(work_links) == 1
    assert work_links[0].url == "https://github.com/a/b"

    await close_repositories(repos)


@pytest.mark.parametrize("access_type", ["SQL", "ORM"])
@pytest.mark.asyncio
async def test_remove_link(settings, access_type):
    settings.db_access_type = access_type

    repos = await create_repositories(settings)
    chat_repo = repos["chat"]
    link_repo = repos["link"]

    await chat_repo.add(123)

    request = AddLinkRequest(link="https://github.com/a/b")
    await link_repo.add(123, request)

    success = await link_repo.remove(123, "https://github.com/a/b")
    assert success is True

    links = await link_repo.get_by_chat(123)
    assert len(links) == 0

    await close_repositories(repos)


@pytest.mark.parametrize("access_type", ["SQL", "ORM"])
@pytest.mark.asyncio
async def test_scheduler_filter(settings, access_type):
    settings.db_access_type = access_type

    repos = await create_repositories(settings)
    chat_repo = repos["chat"]
    link_repo = repos["link"]

    await chat_repo.add(123)

    req = AddLinkRequest(link="https://github.com/a/b")
    await link_repo.add(123, req)

    links = await link_repo.get_all_for_check()
    assert len(links) > 0

    await link_repo.update_last_checked(links[0].id, None)

    links = await link_repo.get_all_for_check()
    assert len(links) == 0

    await close_repositories(repos)
