from pydantic import BaseModel, AnyUrl, Field

from src.config import settings
from src.logger import get_logger
from src.clients.resilient_http_client import ResilientHttpClient

logger = get_logger()


class AddLinkRequest(BaseModel):
    """Запрос на добавление ссылки."""

    link: AnyUrl
    tags: list[str] = Field(default_factory=list)
    filters: list[str] = Field(default_factory=list)


class LinkResponse(BaseModel):
    """Ответ с информацией о ссылке."""

    id: int
    url: AnyUrl
    tags: list[str]
    filters: list[str]


class ListLinksResponse(BaseModel):
    """Ответ со списком ссылок."""

    links: list[LinkResponse]
    size: int


class RemoveLinkRequest(BaseModel):
    """Запрос на удаление ссылки."""

    link: AnyUrl


class ApiError(BaseModel):
    """Формат ошибки от скраппера."""

    description: str
    code: str
    exceptionName: str | None = None
    exceptionMessage: str | None = None


class ScrapperClientError(Exception):
    """Базовое исключение для ошибок клиента."""

    pass


class ChatNotFoundError(ScrapperClientError):
    """Чат не найден в скраппере."""

    pass


class LinkAlreadyExistsError(ScrapperClientError):
    """Ссылка уже отслеживается."""

    pass


class ScrapperClient:
    """HTTP-клиент для общения со скраппером."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self._client = ResilientHttpClient()

    async def close(self):
        """Закрыть клиент при завершении приложения."""
        await self._client.close()

    def _get_headers(self, chat_id: int) -> dict:
        """Формирует заголовки с Tg-Chat-Id."""
        return {"Tg-Chat-Id": str(chat_id)}

    async def register_chat(self, chat_id: int) -> bool:
        """Зарегистрировать чат в скраппере."""
        url = f"{self.base_url}/tg-chat/{chat_id}"
        logger.info("register_chat_request", chat_id=chat_id, url=url)

        try:
            response = await self._client.post(url)
            if response.status_code == 200:
                logger.info("chat_registered", chat_id=chat_id)
                return True
            elif response.status_code == 409:
                logger.warning("chat_already_exists", chat_id=chat_id)
                return True
            else:
                logger.error(
                    "register_chat_failed", chat_id=chat_id, status=response.status_code
                )
                return False
        except Exception as e:
            logger.error("register_chat_error", chat_id=chat_id, error=str(e))
            raise ScrapperClientError(f"Не удалось связаться со скраппером: {e}")

    async def add_link(
        self, chat_id: int, url: str, tags: list[str] | None = None
    ) -> LinkResponse:
        """Добавить ссылку для отслеживания."""
        endpoint = f"{self.base_url}/links"
        headers = self._get_headers(chat_id)
        request_body = AddLinkRequest(link=AnyUrl(url), tags=tags or [], filters=[])

        logger.info("add_link_request", chat_id=chat_id, url=url, tags=tags)

        try:
            response = await self._client.post(
                endpoint,
                headers=headers,
                json=request_body.model_dump(by_alias=True, mode="json"),
            )

            if response.status_code == 200:
                result = LinkResponse(**response.json())
                logger.info("link_added", link_id=result.id, url=url)
                return result
            elif response.status_code == 404:
                logger.warning("chat_not_found", chat_id=chat_id)
                raise ChatNotFoundError("Чат не зарегистрирован в скраппере")
            elif response.status_code == 409:
                logger.warning("link_already_exists", chat_id=chat_id, url=url)
                raise LinkAlreadyExistsError("Ссылка уже отслеживается")
            else:
                error_data = response.json() if response.content else {}
                logger.error(
                    "add_link_failed", status=response.status_code, error=error_data
                )
                raise ScrapperClientError(f"Ошибка скраппера: {response.status_code}")
        except ScrapperClientError:
            raise
        except Exception as e:
            logger.error("add_link_network_error", url=url, error=str(e))
            raise ScrapperClientError(f"Не удалось связаться со скраппером: {e}")

    async def list_links(
        self, chat_id: int, tag: str | None = None
    ) -> list[LinkResponse]:
        """Получить список ссылок для чата."""
        endpoint = f"{self.base_url}/links"
        headers = self._get_headers(chat_id)
        params = {"tag": tag} if tag else {}

        logger.info("list_links_request", chat_id=chat_id, tag=tag)

        try:
            response = await self._client.get(endpoint, headers=headers, params=params)

            if response.status_code == 200:
                data = ListLinksResponse(**response.json())
                logger.info("links_retrieved", chat_id=chat_id, count=data.size)
                return data.links
            elif response.status_code == 404:
                logger.warning("chat_not_found", chat_id=chat_id)
                raise ChatNotFoundError("Чат не зарегистрирован")
            else:
                logger.error("list_links_failed", status=response.status_code)
                raise ScrapperClientError(
                    f"Ошибка при получении списка ссылок: {response.status_code}"
                )
        except ScrapperClientError:
            raise
        except Exception as e:
            logger.error("list_links_network_error", error=str(e))
            raise ScrapperClientError(f"Не удалось связаться со скраппером: {e}")

    async def remove_link(self, chat_id: int, url: str) -> bool:
        """Удалить ссылку из отслеживания."""
        endpoint = f"{self.base_url}/links"
        headers = self._get_headers(chat_id)
        request_body = RemoveLinkRequest(link=AnyUrl(url))

        logger.info("remove_link_request", chat_id=chat_id, url=url)

        try:
            response = await self._client.request(
                "DELETE",
                endpoint,
                headers=headers,
                json=request_body.model_dump(by_alias=True, mode="json"),
            )

            if response.status_code == 200:
                logger.info("link_removed", chat_id=chat_id, url=url)
                return True
            elif response.status_code == 404:
                logger.warning("link_or_chat_not_found", chat_id=chat_id, url=url)
                raise ChatNotFoundError("Чат или ссылка не найдены")
            else:
                logger.error("remove_link_failed", status=response.status_code)
                raise ScrapperClientError(
                    f"Ошибка при удалении ссылки: {response.status_code}"
                )
        except ScrapperClientError:
            raise
        except Exception as e:
            logger.error("remove_link_network_error", error=str(e))
            raise ScrapperClientError(f"Не удалось связаться со скраппером: {e}")


scrapper_client = ScrapperClient(base_url=str(settings.scrapper_base_url))
