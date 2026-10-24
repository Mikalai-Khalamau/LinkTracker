from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class User:
    id: int
    username: Optional[str] = None


class UserRepository:
    """Репозиторий для работы с пользователем."""

    def __init__(self):
        self._users: Dict[int, User] = {}

    def get_or_create(self, user_id: int, username: Optional[str] = None) -> User:
        """Получить пользователя по id или создать нового."""
        if user_id not in self._users:
            self._users[user_id] = User(id=user_id, username=username)
        return self._users[user_id]

    def get_user(self, user_id: int) -> Optional[User]:
        """Получить пользователя по id."""
        return self._users.get(user_id)
