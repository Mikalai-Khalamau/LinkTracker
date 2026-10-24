from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime

from src.models import AddLinkRequest, LinkDomain


class ChatRepositoryProtocol(ABC):
    @abstractmethod
    async def exists(self, chat_id: int) -> bool:
        pass

    @abstractmethod
    async def add(self, chat_id: int) -> bool:
        pass

    @abstractmethod
    async def remove(self, chat_id: int) -> bool:
        pass


class LinkRepositoryProtocol(ABC):
    @abstractmethod
    async def add(self, chat_id: int, request: AddLinkRequest) -> Optional[LinkDomain]:
        pass

    @abstractmethod
    async def get_by_chat(
        self, chat_id: int, tag: Optional[str] = None
    ) -> List[LinkDomain]:
        pass

    @abstractmethod
    async def remove(self, chat_id: int, url: str) -> bool:
        pass

    @abstractmethod
    async def get_all_for_check(self, limit: int = 100) -> List[LinkDomain]:
        pass

    @abstractmethod
    async def update_last_checked(
        self, link_id: int, last_updated: Optional[datetime]
    ) -> bool:
        pass

    @abstractmethod
    async def get_by_url(self, url: str) -> Optional[LinkDomain]:
        pass
