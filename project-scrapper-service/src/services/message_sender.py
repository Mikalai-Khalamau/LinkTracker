"""Интерфейс для отправки уведомлений."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Protocol, runtime_checkable


@dataclass
class UpdateMessage:
    """Структурированное сообщение об обновлении."""

    update_type: str
    source_url: str
    title: str
    author: str
    created_at: datetime
    preview: str
    chat_ids: List[int]

    def __str__(self) -> str:
        return f"{self.update_type}: {self.title} by {self.author}"


@runtime_checkable
class MessageSenderProtocol(Protocol):
    """Протокол для отправки уведомлений."""

    async def send_message(self, message: UpdateMessage) -> bool:
        """Отправляет уведомление всем получателям."""
        ...
