from fastapi import APIRouter, Header, HTTPException, status, Request

from src.logger import get_logger
from src.models import (
    AddLinkRequest,
    ApiErrorResponse,
    LinkResponse,
    LinkUpdate,
    ListLinksResponse,
    RemoveLinkRequest,
)
from src.limiter import limiter
from src.config import settings

logger = get_logger()
router = APIRouter()


def get_repositories(request: Request):
    """Получает репозитории из app.state."""
    return {
        "chat": request.app.state.chat_repository,
        "link": request.app.state.link_repository,
    }


@router.post(
    "/tg-chat/{chat_id}",
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ApiErrorResponse},
        409: {"model": ApiErrorResponse},
    },
)
@limiter.limit(f"{settings.rate_limit_requests_per_minute}/minute")
async def register_chat(request: Request, chat_id: int):
    """Зарегистрировать чат."""
    repos = get_repositories(request)
    logger.info("register_chat_requested", chat_id=chat_id)

    if not await repos["chat"].add(chat_id):
        logger.warning("chat_already_exists", chat_id=chat_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ApiErrorResponse(
                description="Чат уже зарегистрирован",
                code="CHAT_ALREADY_EXISTS",
                exceptionName="ConflictException",
            ).model_dump(by_alias=True),
        )

    logger.info("chat_registered", chat_id=chat_id)
    return {"status": "ok"}


@router.delete(
    "/tg-chat/{chat_id}",
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ApiErrorResponse},
        404: {"model": ApiErrorResponse},
    },
)
@limiter.limit(f"{settings.rate_limit_requests_per_minute}/minute")
async def delete_chat(request: Request, chat_id: int):
    """Удалить чат."""
    repos = get_repositories(request)
    logger.info("delete_chat_requested", chat_id=chat_id)

    if not await repos["chat"].remove(chat_id):
        logger.warning("chat_not_found", chat_id=chat_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ApiErrorResponse(
                description="Чат не найден",
                code="CHAT_NOT_FOUND",
                exceptionName="NotFoundException",
            ).model_dump(by_alias=True),
        )

    logger.info("chat_deleted", chat_id=chat_id)
    return {"status": "ok"}


@router.get("/links", response_model=ListLinksResponse)
@limiter.limit(f"{settings.rate_limit_requests_per_minute}/minute")
async def list_links(
    request: Request, tg_chat_id: int = Header(..., alias="Tg-Chat-Id")
):
    repos = get_repositories(request)
    logger.info("list_links_requested", chat_id=tg_chat_id)

    try:
        if not await repos["chat"].exists(tg_chat_id):
            logger.warning("chat_not_found", chat_id=tg_chat_id)
            raise HTTPException(status_code=404, detail="Chat not found")

        cache_client = request.app.state.cache_client

        if cache_client is not None:
            cached = await cache_client.get(tg_chat_id)
            if cached is not None:
                logger.info("cache_hit_response", chat_id=tg_chat_id)
                return ListLinksResponse(**cached)

        logger.debug("calling_get_by_chat", chat_id=tg_chat_id)
        links = await repos["link"].get_by_chat(tg_chat_id, tag=None)
        logger.info("links_retrieved", chat_id=tg_chat_id, count=len(links))

        response = ListLinksResponse(
            links=[link.to_response() for link in links],
            size=len(links),
        )

        if cache_client is not None:
            response_data = response.model_dump(mode="json", by_alias=True)
            await cache_client.set(tg_chat_id, response_data)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "list_links_error", chat_id=tg_chat_id, error=str(e), exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post(
    "/links",
    response_model=LinkResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ApiErrorResponse},
        404: {"model": ApiErrorResponse},
        409: {"model": ApiErrorResponse},
    },
)
@limiter.limit(f"{settings.rate_limit_requests_per_minute}/minute")
async def add_link(
    request: Request,
    body: AddLinkRequest,
    tg_chat_id: int = Header(..., alias="Tg-Chat-Id"),
):
    repos = get_repositories(request)
    logger.info("add_link_requested", chat_id=tg_chat_id, url=str(body.link))

    if not await repos["chat"].exists(tg_chat_id):
        logger.warning("chat_not_found", chat_id=tg_chat_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ApiErrorResponse(
                description="Chat not found",
                code="CHAT_NOT_FOUND",
                exceptionName="NotFoundException",
            ).model_dump(by_alias=True),
        )

    link = await repos["link"].add(tg_chat_id, body)
    if link is None:
        logger.warning("link_already_tracked", chat_id=tg_chat_id, url=str(body.link))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ApiErrorResponse(
                description="Link already tracked",
                code="LINK_ALREADY_EXISTS",
                exceptionName="ConflictException",
            ).model_dump(by_alias=True),
        )

    cache_client = request.app.state.cache_client
    if cache_client is not None:
        await cache_client.invalidate(tg_chat_id)

    logger.info("link_added", link_id=link.id, url=str(body.link))
    return link.to_response()


@router.delete(
    "/links",
    response_model=LinkResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ApiErrorResponse},
        404: {"model": ApiErrorResponse},
    },
)
@limiter.limit(f"{settings.rate_limit_requests_per_minute}/minute")
async def remove_link(
    request: Request,
    body: RemoveLinkRequest,
    tg_chat_id: int = Header(..., alias="Tg-Chat-Id"),
):
    repos = get_repositories(request)
    logger.info("remove_link_requested", chat_id=tg_chat_id, url=str(body.link))

    if not await repos["chat"].exists(tg_chat_id):
        logger.warning("chat_not_found", chat_id=tg_chat_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ApiErrorResponse(
                description="Chat not found",
                code="CHAT_NOT_FOUND",
                exceptionName="NotFoundException",
            ).model_dump(by_alias=True),
        )

    if not await repos["link"].remove(tg_chat_id, str(body.link)):
        logger.warning("link_not_found", chat_id=tg_chat_id, url=str(body.link))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ApiErrorResponse(
                description="Link not found",
                code="LINK_NOT_FOUND",
                exceptionName="NotFoundException",
            ).model_dump(by_alias=True),
        )

    cache_client = request.app.state.cache_client
    if cache_client is not None:
        await cache_client.invalidate(tg_chat_id)

    logger.info("link_removed", chat_id=tg_chat_id, url=str(body.link))
    return LinkResponse(id=0, url=body.link, tags=[], filters=[])


@router.post(
    "/updates",
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ApiErrorResponse},
    },
)
@limiter.limit(f"{settings.rate_limit_requests_per_minute}/minute")
async def receive_update(request: Request, update: LinkUpdate):
    """Получение уведомления об обновлении от скраппера."""
    logger.info("update_received", url=str(update.url), chat_ids=update.tg_chat_ids)
    return {"status": "received"}
