from typing import Protocol
from uuid import UUID

from app.domain.identity.user import User


class UserStore(Protocol):
    def save(self, user: User) -> None:
        ...

    def get(self, user_id: UUID) -> User | None:
        ...

    def get_or_create(self, user_id: UUID, status) -> User:
        ...
