from dataclasses import dataclass
from datetime import datetime, timezone

from src.models import AddLinkRequest, LinkResponse


@dataclass
class Link:
    """Внутренняя модель ссылки."""

    id: int
    chat_id: int
    url: str
    tags: list[str]
    filters: list[str]
    last_checked: datetime | None = None
    last_updated: datetime | None = None

    def to_response(self) -> LinkResponse:
        """Конвертация в ответ для API."""
        return LinkResponse(
            id=self.id,
            url=self.url,
            tags=self.tags,
            filters=self.filters,
        )


class ChatRepository:
    """Хранилище зарегистрированных чатов."""

    def __init__(self):
        self._chats: set[int] = set()

    def exists(self, chat_id: int) -> bool:
        return chat_id in self._chats

    def add(self, chat_id: int) -> bool:
        """Добавить чат."""
        if chat_id in self._chats:
            return False
        self._chats.add(chat_id)
        return True

    def remove(self, chat_id: int) -> bool:
        """Удалить чат."""
        if chat_id not in self._chats:
            return False
        self._chats.remove(chat_id)
        return True


class LinkRepository:
    """Хранилище отслеживаемых ссылок."""

    def __init__(self):
        self._links: dict[int, dict[str, Link]] = {}
        self._next_id: int = 1

    def add(self, chat_id: int, request: AddLinkRequest) -> Link | None:
        """Добавить ссылку."""
        url_str = str(request.link)

        if chat_id not in self._links:
            self._links[chat_id] = {}

        if url_str in self._links[chat_id]:
            return None

        link = Link(
            id=self._next_id,
            chat_id=chat_id,
            url=url_str,
            tags=request.tags or [],
            filters=request.filters or [],
            last_checked=datetime.now(timezone.utc),
        )
        self._links[chat_id][url_str] = link
        self._next_id += 1
        return link

    def get_by_chat(self, chat_id: int, tag: str | None = None) -> list[Link]:
        """Получить ссылки чата."""
        if chat_id not in self._links:
            return []

        links = list(self._links[chat_id].values())
        if tag:
            links = [link for link in links if tag in link.tags]
        return links

    def remove(self, chat_id: int, url: str) -> bool:
        """Удалить ссылку."""
        if chat_id not in self._links:
            return False
        return self._links[chat_id].pop(url, None) is not None

    def get_all_for_check(self) -> list[Link]:
        """Получить все ссылки для планировщика."""
        return [
            link for chat_links in self._links.values() for link in chat_links.values()
        ]

    def update_last_checked(self, link_id: int, last_updated: datetime | None) -> bool:
        """Обновить время последней проверки для ссылки."""
        for chat_links in self._links.values():
            for link in chat_links.values():
                if link.id == link_id:
                    link.last_checked = datetime.now(timezone.utc)
                    if last_updated:
                        link.last_updated = last_updated
                    return True
        return False


chat_repository = ChatRepository()
link_repository = LinkRepository()
